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
order_ns = Namespace('order', description='Order related operations')

# Input from FE for creating order
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

##### AMQP Connection Functions #####

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

##### Individual helper functions #####

# Check for balance (connects to crypto service)
def check_crypto_balance(user_id, token_id, required_amount):
    try:
        checked_and_updated = True
        error_message = None
        status_code = 200
        short_of = None

        # Check for balance
        holding_response = requests.get(f"{CRYPTO_SERVICE_URL}/holdings/{user_id}/{token_id}")
        if holding_response.status_code != 200:
            return None, {
                "error": "Failed to retrieve holding balance",
                "details": holding_response.json() if holding_response.content else "No response content"
            }, holding_response.status_code, None
        
        response_dict = holding_response.json()
        # Return early if balance is insufficient
        if response_dict["availableBalance"] < required_amount:
            checked_and_updated = False
            short_of = required_amount - response_dict["availableBalance"]
            return checked_and_updated, None, status_code, short_of
        
        # Update holding (reserve the tokens)
        update_success, update_error_message, update_status_code = update_available_balance(user_id, token_id, required_amount)

        if update_success == False:
            checked_and_updated = False
            error_message = update_error_message
            status_code = update_status_code

        return checked_and_updated, error_message, status_code, short_of
    
    except requests.RequestException as e:
        return None, {"error": "Failed to connect to crypto service for checking", "details": str(e)}, 500, None 

# Reserve balance (connects to crypto service)
def update_available_balance(user_id, token_id, required_amount):
    try:
        body_for_update = {
            "userId": user_id,
            "tokenId": token_id,
            "amountChanged": required_amount
        }

        update_response = requests.post(f"{CRYPTO_SERVICE_URL}/holdings/reserve", json=body_for_update)

        if update_response.status_code != 200:
            return False, {
                "error": "Failed to update holding balance",
                "details": update_response.json() if update_response.content else "No response content"
            }, update_response.status_code
            
        return True, None, 200
    except requests.RequestException as e:
        return False, {"error": "Failed to connect to crypto service for reserving balance", "details": str(e)}, 500 

# Check if wallet exists and create holding if needed
def check_or_create_wallet_holding(user_id, token_id):
    try:
        # Check if wallet exists
        wallet_response = requests.get(f"{CRYPTO_SERVICE_URL}/wallet/{user_id}")
        
        # If wallet doesn't exist, create it
        if wallet_response.status_code != 200:
            wallet_creation = requests.post(f"{CRYPTO_SERVICE_URL}/wallet", json={"userId": user_id})
            if wallet_creation.status_code != 201:
                return False, {
                    "error": "Failed to create wallet",
                    "details": wallet_creation.json() if wallet_creation.content else "No response content"
                }, wallet_creation.status_code
        
        # Check if holding exists
        holding_response = requests.get(f"{CRYPTO_SERVICE_URL}/holdings/{user_id}/{token_id}")
        
        # If holding doesn't exist, create it
        if holding_response.status_code != 200:
            holding_creation = requests.post(f"{CRYPTO_SERVICE_URL}/holdings", json={
                "userId": user_id,
                "tokenId": token_id,
                "actualBalance": 0,
                "availableBalance": 0
            })
            if holding_creation.status_code != 201:
                return False, {
                    "error": "Failed to create holding",
                    "details": holding_creation.json() if holding_creation.content else "No response content"
                }, holding_creation.status_code
        
        return True, None, 200
    except requests.RequestException as e:
        return False, {"error": "Failed to connect to crypto service for wallet/holding operations", "details": str(e)}, 500

# Post order to transaction log
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

##### API actions #####
@order_ns.route("/create_order")
class CheckBalance(Resource):
    @order_ns.expect(create_order_model)
    @order_ns.response(201, "Order created successfully", success_creation_response)
    @order_ns.response(400, "Order failed (insufficient balance)", insufficient_balance_response)
    @order_ns.response(500, "Internal Server Error", error_response)
    def post(self):
        """Checks balance, creates transaction log, and creates order for orderbook to swap"""
        if connection is None or not amqp_lib.is_connection_open(connection):
            connectAMQP()
        
        data = request.json

        # Process input data
        user_id = data.get("userId")
        side = data.get("side").lower()
        order_type = data.get("orderType").lower()
        
        # Ensure all cryptocurrency tokens are lowercase
        base_token_id = data.get("baseTokenId").lower()
        quote_token_id = data.get("quoteTokenId").lower()
        limit_price = data.get("limitPrice")
        quantity = data.get("quantity")
        order_cost = data.get("orderCost")

        # Determine from/to tokens based on side
        if side == "buy":
            from_token_id = quote_token_id
            from_amount = order_cost
            to_token_id = base_token_id
            to_amount = quantity
        elif side =="sell":  # sell
            from_token_id = base_token_id
            from_amount = quantity
            to_token_id = quote_token_id
            to_amount = order_cost
        else:
            return {
                "error": "Invalid side value. Must be 'buy' or 'sell'."
            }, 400

        # 1. Check if from side has sufficient balance
        crypto_sufficient, crypto_error, crypto_status_code, shortOf = check_crypto_balance(user_id, from_token_id, from_amount)

        if crypto_error:
            return crypto_error, crypto_status_code
        
        if crypto_sufficient == False:
            return {
                "error": "Insufficient balance to fulfil order",
                "shortOf": shortOf,
            }, 400

        # 2. Check if to side has a wallet and holding, create if needed
        wallet_created, wallet_error, wallet_status_code = check_or_create_wallet_holding(user_id, to_token_id)
        
        if wallet_error:
            return wallet_error, wallet_status_code

        # 3. Create transaction log
        transaction_log_payload = {
            "userId": user_id,
            "status": "pending",
            "fromTokenId": from_token_id,
            "fromAmount": from_amount,
            "fromAmountActual": 0,  # will be updated as order gets fulfilled
            "toTokenId": to_token_id,
            "toAmount": to_amount,
            "toAmountActual": 0,  # will be updated as order gets fulfilled
            "limitPrice": limit_price,
            "orderType": order_type,
        }

        transaction_response, transaction_error, transaction_status_code = post_transaction_log(transaction_log_payload)

        if transaction_error:
            return transaction_error, transaction_status_code 
        
        transaction_id = transaction_response["transactionId"]
        creation = transaction_response["creation"]
        
        # 4. Publish to orderbook service
        message_to_publish = {
            "transactionId": transaction_id,
            "userId": user_id,
            "orderType": order_type, 
            "fromTokenId": from_token_id,
            "toTokenId": to_token_id,
            "fromAmount": from_amount,
            "limitPrice": limit_price,
            "creation": creation
        }

        json_message = json.dumps(message_to_publish)

        channel.basic_publish(
            exchange=exchange_name,
            routing_key="order.new",
            body=json_message,
            properties=pika.BasicProperties(delivery_mode=2),
        )

        return {
            "message": "Order created successfully", 
            "transaction_id": transaction_response["transactionId"],
            "transaction_status": transaction_response["status"],
        }, 201

# Add namespace to api
api.add_namespace(order_ns)

if __name__ == '__main__':
    connectAMQP()
    app.run(host='0.0.0.0', port=5000, debug=True)