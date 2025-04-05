from flask import Flask, jsonify, request, Blueprint
from flask_cors import CORS
from flask_restx import Api, Resource, fields, Namespace
import requests


##### Configuration #####
# Define API version and root path
API_VERSION = 'v1'
API_ROOT = f'/api/{API_VERSION}'

app = Flask(__name__)
CORS(app)

# Flask swagger (flask_restx) api documentation
# Creates API documentation automatically
blueprint = Blueprint('api',__name__,url_prefix=API_ROOT)
api = Api(blueprint, version=API_VERSION, title='Order Management Service API', description='Order Management Service API for Yorkshire Crypto Exchange')

# Register Blueprint with Flask app
app.register_blueprint(blueprint)

# Environment variables for microservice
# Environment variables for microservice URLs
# NOTE: Do not use localhost here as localhost refer to this container itself
# CRYPTO_SERVICE_URL = "http://crypto-service:5002/api/v1/crypto"
# TRANSACTION_SERVICE_URL = "http://transaction-service:5005/api/v1/transaction"

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

# Input from FE for creating order, also needed for checking balance
create_order_model = order_ns.model(
    "CreateAccount",
    {
        # Admin details
        "userId": fields.String(required=True, description="User ID"),

        # Order details
        "fromTokenId": fields.String(required=True, description="Token ID of quote currency"),
        "fromAmount": fields.Float(required=True, description="Total amount of quote currency"),

        "toTokenId": fields.String(required=True, description="Token ID of base currency"),
        "toAmount": fields.Float(required=True, description="Total amount of base currency"),
        "limitPrice": fields.Float(required=True, description="Base price at which user is willing to execute"),

        # "usdtFee": fields.Float(required=True, description="Fee of transaction"),
        "orderType": fields.String(required=True, description="Type of Order (Limit/Market)")
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
# Output to FE upon fulfillment of order (partial/full)
# order_update_response = order_ns.model(
#     "OrderUpdateResponse",
#     {
#         "message": fields.String(description="Order update message"),
#         "transactionId": fields.String(attribute='transaction_id', description="Tranaction ID for updated order"),
#     },
# )

# Output to orderbook_service
order_publish_model = order_ns.model(
    "PublishOrder",
    {
        "message": fields.String(description="Order publishing message"),
        "transactionId": fields.String(attribute='transaction_id'),
        "userId": fields.String(attribute='user_id', description="User ID (wallet) associated with order"),
        "type": fields.String(attribute='type', description="Order type - buy or sell"),
        # "baseQuotePair": fields.String(attribute='type', description="Order pair, i.e. BTC/XRP"),
        "fromTokenId": fields.String(attribute='from_token_id', description="Token ID for crypto buying with (quote)"),
        "toTokenId": fields.String(attribute='to_token_id', description="Token ID for crypto being bought (base)"),
        "fromAmount": fields.Float(attribute='from_amount', description="Amount being bought with from(quote) Token (i.e Amount of XRP from BTC/XRP that you are willing to pay for the given price of BTC)"),
        "price": fields.Float(attribute='price', description="Price of to(base) Token (i.e BTC with limit price of 100,000 for BTC/XRP)"),
        "creation": fields.DateTime
    },
)

##### Individual helper functions  #####

# (F1) Check for balance (connects to crypto service)
def check_crypto_balance(user_id, token_id, required_from_amount):
    try:
        holding_response = requests.get(f"{CRYPTO_SERVICE_URL}/holdings/{user_id}/{token_id}")
        if holding_response.status_code != 200:
            return None, {
                "error": "Failed to retrieve holding balance",
                "details": holding_response.json() if holding_response.content else "No response content"
            }, holding_response.status_code, None
        
        response_dict = holding_response.json()
        is_sufficient = True
        short_of = None
        if response_dict["heldBalance"] < required_from_amount:
            is_sufficient = False
            short_of = required_from_amount - response_dict["heldBalance"]
        
        return is_sufficient, None, 200, short_of

    except requests.RequestException as e:
        return None, {"error": "Failed to connect to crypto service", "details": str(e)}, 500, None 

# (F2) Post order to transaction log (connects to transaction logs service)
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

# Create account service
@order_ns.route("/create_order")
class CheckBalance(Resource):
    @order_ns.expect(create_order_model) # expected input structure
    @order_ns.response(201, "Order created successfully", success_creation_response) # documents responses from this func
    @order_ns.response(400, "Order failed (insufficient balance)", insufficient_balance_response)
    @order_ns.response(500, "Internal Server Error", error_response)
    def post(self):
        """Checks balance, creates transaction log, and creates order for orderbook to swap"""
        data = request.json

        user_id = data.get("userId")
        from_token_id = data.get("fromTokenId")
        from_amount = data.get("fromAmount")
        to_token_id = data.get("toTokenId")
        to_amount = data.get("toAmount")
        limit_price = data.get("limitPrice")
        order_type = data.get("orderType") # limited to limit order rn
        order_fee = 0.05 * from_amount # usually just 0.05% for takers (taking base crypto out of pool)
        required_from_amount = order_fee + from_amount

        # (1) Check quote (from/paying) crypto balance of user (BTC/XRP -> XRP)
        crypto_sufficient, crypto_error, crypto_status_code, shortOf = check_crypto_balance(user_id, from_token_id, required_from_amount)

        if crypto_error:
            return crypto_error, crypto_status_code
        
        if crypto_sufficient == False:
            return {
                "error": "Insufficient balance to fulfil order",
                "shortOf": shortOf,
                    }, 400

        # (2) Create transaction log
        transaction_log_payload = {
            "userId": user_id,
            "status": "pending",
            "fromTokenId": from_token_id,
            "fromAmount": from_amount,
            "fromAmountActual": 0, #is this really needed
            "toTokenId": to_token_id,
            "toAmount": to_amount,
            "toAmountActual": 0, #is this really needed
            "limitPrice": limit_price,
            "usdtFee": order_fee, #not usdt
            "orderType": "order_type",
        }

        transaction_response, transaction_error, transaction_status_code = post_transaction_log(transaction_log_payload)

        if transaction_error:
            return transaction_error, transaction_status_code 
        
        # (3) publish to orderbook service and respond to user


        return {"message": "Order created successfully", 
                "transaction_id": transaction_response["transactionId"],
                "transaction_status": transaction_response["status"],
                }, 201

# Add name spaces into api
api.add_namespace(order_ns)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)	