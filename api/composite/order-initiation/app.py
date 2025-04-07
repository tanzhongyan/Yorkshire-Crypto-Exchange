from flask import Flask, jsonify, request, Blueprint
from flask_cors import CORS
from flask_restx import Api, Resource, fields, Namespace
import requests
import amqp_lib
import pika
import json
# import threading

##### Configuration #####
# Define API version and root path
API_VERSION = 'v1'
API_ROOT = f'/api/{API_VERSION}'

app = Flask(__name__)
CORS(app)

# RabbitMQ
rabbit_host = "rabbitmq"
rabbit_port = 5672
exchange_name = "order_topic"
exchange_type = "topic"
# queue_name = "order_management_service.orders_placed"

connection = None 
channel = None

# Flask swagger (flask_restx) api documentation
# Creates API documentation automatically
blueprint = Blueprint('api',__name__,url_prefix=API_ROOT)
api = Api(blueprint, version=API_VERSION, title='Order Initiation Service API', description='Order Initiation Service API for Yorkshire Crypto Exchange')

# Register Blueprint with Flask app
app.register_blueprint(blueprint)

# Environment variables for microservice
# Environment variables for microservice URLs
# NOTE: Do not use localhost here as localhost refer to this container itself
CRYPTO_SERVICE_URL = "http://crypto-service:5000/api/v1/crypto"
TRANSACTION_SERVICE_URL = "http://transaction-service:5000/api/v1/transaction"

# Define namespaces to group api calls together
# Namespaces are essentially folders that group all related API calls
order_ns = Namespace('order', description='Order related operations')
# balance_ns = Namespace('balance', description='Balance related operations')
# transaction_ns = Namespace('transaction', description='Transaction related operations')

##### API Models - flask restx API autodoc #####
# To use flask restx, you will have to define API models with their input types
# For all API models, add a comment to the top to signify its importance
# E.g. Input/Output One/Many user account

# Input from FE for creating order, also needed for checking balance [old]
# create_order_model = order_ns.model(
#     "CreateOrder",
#     {
#         # Admin details
#         "userId": fields.String(required=True, description="User ID"),

#         # Order details
#         "fromTokenId": fields.String(required=True, description="Token ID of quote currency"),
#         "fromAmount": fields.Float(required=True, description="Total amount of quote currency"),

#         "toTokenId": fields.String(required=True, description="Token ID of base currency"),
#         "toAmount": fields.Float(required=True, description="Total amount of base currency"),
#         "limitPrice": fields.Float(required=True, description="Base price at which user is willing to execute"),

#         # "usdtFee": fields.Float(required=True, description="Fee of transaction"),
#         "orderType": fields.String(required=True, description="Type of Order (Limit/Market)")
#     },
# )

# Input from FE for creating order, also needed for checking balance [new]
create_order_model = order_ns.model(
    "CreateOrder",
    {
        "userId": fields.String(required=True, description="User ID"),
        "orderType": fields.String(required=True, description="Type of Order (Limit/Market)"),
        "side": fields.String(required=True, description="Type of Order (Buy/Sell)"),

        "baseTokenId": fields.String(required=True, description="Token ID of base currency"),
        "quoteTokenId": fields.String(required=True, description="Token ID of quote currency"),
        "limitPrice": fields.Float(required=True, description="Price at which user is willing to buy base asset"),

        "quantity": fields.Float(required=True, description="Total amount of base currency to be bought/sold"),
        "orderCost": fields.Float(required=True, description="Total amount of quote to pay with, computed frontend")
    },
)

# Output to FE upon successful creation of order in transaction log
success_creation_response = order_ns.model(
    "SuccessfulTransactionResponse",
    {
        "message": fields.String(description="Order creation success message"),
        "transactionId": fields.String(attribute='transaction_id', 
        description="Created Transaction ID"),
        "transactionStatus": fields.String,
    },
)

# Output to FE upon insufficient balance for order detected
insufficient_balance_response = order_ns.model(
    "InsufficientBalanceErrorResponse",
    {
        "error": fields.String(description="Error message"),
        "shortOf": fields.Float(description="Amount shortage")
    },
)

# Output to FE given upon failure in general
error_response = order_ns.model(
    "ErrorResponse",
    {
        "error": fields.String(description="Error message"),
        "details": fields.String(description="Error details"),
    },
)

##### AMQP Connection Functions  #####

def connectAMQP():
    # Use global variables to reduce number of reconnection to RabbitMQ
    global connection
    global channel

    print("  Connecting to AMQP broker...")
    try:
        connection, channel = amqp_lib.connect(
                hostname=rabbit_host,
                port=rabbit_port,
                exchange_name=exchange_name,
                exchange_type=exchange_type,
        )
    except Exception as exception:
        print(f"  Unable to connect to RabbitMQ.\n     {exception=}\n")
        exit(1) # terminate

def callback(channel, method, properties, body):
    try:
        error = json.loads(body)
        print(f"Error message (JSON): {error}")
    except Exception as e:
        print(f"Unable to parse JSON: {e=}")
        print(f"Error message: {body}")
    print()

##### Individual helper functions  #####

# (F1) Check for balance (connects to crypto service)
def check_crypto_balance(user_id, token_id, required_from_amount):
    try:
        checked_and_updated = True
        error_message = None
        status_code = 200
        short_of = None

        # (F1.1) check for balance
        holding_response = requests.get(f"{CRYPTO_SERVICE_URL}/holdings/{user_id}/{token_id}")
         # (F1.1.1r) return early if cannot connect: None, error, status_code, short_of
        if holding_response.status_code != 200:
            return None, {
                "error": "Failed to retrieve holding balance",
                "details": holding_response.json() if holding_response.content else "No response content"
            }, holding_response.status_code, None
        
        response_dict = holding_response.json()
        # (F1.1.2r) return early if bank balance is insufficient: False, no error, status_code, short_of
        if response_dict["availableBalance"] < required_from_amount:
            checked_and_updated = False
            short_of = required_from_amount - response_dict["availableBalance"]
            return checked_and_updated, None, status_code, short_of
        
        # (F1.2) update holding
        update_success, update_error_message, update_status_code = update_available_balance(user_id, token_id, required_from_amount)

        # (F1.2.1) update return values - if failed, propagate update errors for returning:
        # False, update_error, status_code, (short_of)
        if update_success == False:
            checked_and_updated = False
            error_message = update_error_message
            status_code = update_status_code

        return checked_and_updated, error_message, status_code, short_of
    
    except requests.RequestException as e:
        return None, {"error": "Failed to connect to crypto service for checking", "details": str(e)}, 500, None 

# (F2) Post reserve balance to crypto (connects to crypto service)
def update_available_balance(user_id, token_id, required_from_amount):
    try:
        body_for_update = {
            "userId": user_id,
            "tokenId": token_id,
            "amountChanged": required_from_amount
        }
        json_message = json.dumps(body_for_update)

        update_response = requests.post(f"{CRYPTO_SERVICE_URL}/holdings/reserve", json=json_message)

        if update_response.status_code != 200:
            # (r1) return if unable to connect
            return False, {
                "error": "Failed to update holding balance",
                "details": update_response.json() if update_response.content else "No response content"
            }, update_response.status_code
            
        # (r2) return if successfully updated
        return True, None, 200
    except requests.RequestException as e:
        # (r3) return if error connecting, exception
        return False, {"error": "Failed to connect to crypto service for reserving balance", "details": str(e)}, 500 

# (F3) Post order to transaction log (connects to transaction logs service)
def post_transaction_log(transaction_log_payload):
    try:
        transaction_response = requests.post(f"{TRANSACTION_SERVICE_URL}/crypto/", json=transaction_log_payload)
        if transaction_response.status_code != 201:
            return None, {
                "error": "Failed to create transaction log",
                "details": transaction_response.json() if transaction_response.content else "No response content"
            }, transaction_response.status_code
        
        return transaction_response.json(), None, None
    except requests.RequestException as e:
        return None, {"error": "Failed to connect to transaction service", "details": str(e)}, 500   

##### API actions - flask restx API autodoc #####
# To use flask restx, you will also have to seperate the CRUD actions from the DB table classes

# Create order service
@order_ns.route("/create_order")
class CheckBalance(Resource):
    @order_ns.expect(create_order_model) # expected input structure
    @order_ns.response(201, "Order created successfully", success_creation_response) # documents responses from this func
    @order_ns.response(400, "Order failed (insufficient balance)", insufficient_balance_response)
    @order_ns.response(500, "Internal Server Error", error_response)
    def post(self):
        """Checks balance, creates transaction log, and creates order for orderbook to swap"""
        if connection is None or not amqp_lib.is_connection_open(connection):
            connectAMQP()
        
        data = request.json

        # --- to remove ----
        # user_id = data.get("userId")
        # from_token_id = data.get("fromTokenId")
        # from_token_id = data.get("fromTokenId")
        # from_amount = data.get("fromAmount")
        # to_token_id = data.get("toTokenId")
        # to_amount = data.get("toAmount")
        # limit_price = data.get("limitPrice")
        # order_type = "Limit"
        # order_fee = 0.05 * from_amount
        # required_from_amount = order_fee + from_amount

        user_id = data.get("userId")
        side = data.get("side")

        from_token_id = data.get("quoteTokenId")
        from_amount = data.get("orderCost") # (!) total cost to be calculated on frontend (if "sell", just qty. if "buy", qty * lim price)

        to_token_id = data.get("baseTokenId")
        to_amount = data.get("quantity") # quantity of toToken(baseToken) to get

        limit_price = data.get("limitPrice")
        order_type = "Limit"

        if side == "sell":
            # (!) if you are selling ETH/USDT, ETH (base) will be used to pay for USDT (quote)
            from_token_id = data.get("baseTokenId") 
            to_token_id = data.get("quoteTokenId")

        # (1) Check quote crypto balance of user
        crypto_sufficient_updated, crypto_error, crypto_status_code, shortOf = check_crypto_balance(user_id, from_token_id, from_amount)

        if crypto_error:
            return crypto_error, crypto_status_code
        
        if crypto_sufficient_updated == False:
            return {
                "error": "Insufficient balance to fulfil order",
                "shortOf": shortOf,
                    }, 400

        # (2) Create transaction log
        transaction_log_payload = {
            "userId": user_id,
            "status": "pending",
            "fromTokenId": from_token_id, # cost, (determine above)
            "fromAmount": from_amount,
            "fromAmountActual": 0, # will be increased as order gets fulfilled (if partial)
            "toTokenId": to_token_id,
            "toAmount": to_amount, # total to be excuted
            "toAmountActual": 0, # will be increased as order gets fulfilled (if partial)
            "limitPrice": limit_price, # (!) will be market price for market orders
            "usdtFee": 0,
            "orderType": order_type,
        }

        transaction_response, transaction_error, transaction_status_code = post_transaction_log(transaction_log_payload)

        if transaction_error:
            return transaction_error, transaction_status_code 
        
        transaction_id = transaction_response["transactionId"]
        creation = transaction_response["creation"]
        
        # (3) publish to orderbook service and respond to user
        message_to_publish = {
            "transactionId": transaction_id,
            "userId": user_id,
            "orderType": order_type, 
            "fromTokenId": from_token_id,
            "toTokenId": to_token_id,
            "fromAmount": from_amount, # orderCost
            "limitPrice": limit_price, # 3) limit price or None
            "creation": creation
        }

        json_message = json.dumps(message_to_publish)

        channel.basic_publish(
                exchange=exchange_name,
                routing_key="order.new",
                body=json_message,
                properties=pika.BasicProperties(delivery_mode=2),
                )

        return {"message": "Order created successfully", 
                "transaction_id": transaction_response["transactionId"],
                "transaction_status": transaction_response["status"],
                }, 201

# Add name spaces into api
api.add_namespace(order_ns)

if __name__ == '__main__':
    connectAMQP()
    # consumer_thread = threading.Thread(
    #     target=lambda: amqp_lib.start_consuming(
    #         rabbit_host, rabbit_port, exchange_name, exchange_type, queue_name, callback
    #     ),
    #     daemon=True
    # )
    # consumer_thread.start()
    app.run(host='0.0.0.0', port=5000, debug=True)	