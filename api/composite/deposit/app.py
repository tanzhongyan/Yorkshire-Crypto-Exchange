from flask import Flask, request, jsonify, Blueprint, redirect
from flask_cors import CORS
from flask_restx import Api, Resource, fields, Namespace
import stripe
import requests
import logging
import os
from decimal import Decimal
from dotenv import load_dotenv


##### Configuration #####
# Define API version and root path
API_VERSION = 'v1'
API_ROOT = f'/api/{API_VERSION}'

app = Flask(__name__)

# Configure CORS with restricted origins for production security
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://crypto.tanzhongyan.com", "https://yorkshirecryptoexchange.com"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
        "max_age": 3600
    }
})

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

##### Stripe API Keys #####

# Load .env file
load_dotenv()

# Get keys from .env file
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

stripe.api_key = STRIPE_SECRET_KEY

# Flask swagger (flask_restx) api documentation
# Creates API documentation automatically
blueprint = Blueprint('api', __name__, url_prefix=API_ROOT)
api = Api(blueprint, version=API_VERSION, title='Deposit Microservice', description='Handles fiat deposits with Stripe')
app.register_blueprint(blueprint)

# Environment variables for microservice
# Environment variables for microservice URLs
# NOTE: Do not use localhost here as localhost refer to this container itself
TRANSACTION_SERVICE_URL = "http://transaction-service:5000/api/v1/transaction"
FIAT_SERVICE_URL = "http://fiat-service:5000/api/v1/fiat"
USER_SERVICE_URL = "http://user-service:5000/api/v1/user"

# Frontend URL for Stripe redirects - MUST be set via environment variable
FRONTEND_URL = os.getenv("WEBAPP_URL")
if not FRONTEND_URL:
    raise ValueError("WEBAPP_URL environment variable is required for Stripe redirects")

# Define namespaces to group api calls together
# Namespaces are essentially folders that group all related API calls
deposit_ns = Namespace('deposit', description='Deposit-related operations')

##### API Models - flask restx API autodoc #####
# To use flask restx, you will have to define API models with their input types
# For all API models, add a comment to the top to signify its importance
# E.g. Input/Output One/Many user account

# Input Model for creating a deposit transaction
transaction_input_model = deposit_ns.model(
    "TransactionInput", 
    {
        "userId": fields.String(attribute="user_id", required=True, description="User ID",
                   example="a7c396e2-8370-4975-820e-c5ee8e3875c0"),
        "amount": fields.Float(required=True, description="Amount to deposit",
                   example=1000.0),
        "currencyCode": fields.String(attribute="currency_code", required=True, description="Currency code (default: USD)",
                   example="usd")
    }
)

# Output Model for a transaction
transaction_output_model = deposit_ns.model(
    "TransactionOutput", 
    {
        "transactionId": fields.String(attribute="transaction_id", description="Transaction ID",
                        example="a7c396e2-8370-4975-820e-c5ee8e3875c0"),
        "checkoutUrl": fields.String(attribute="checkout_url", description="Stripe Checkout URL",
                        example="https://checkout.stripe.com/pay/cs_test_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"),
        "amount": fields.Float(description="Amount deposited",
                        example=1000.0),
    }
)

##### Helper Functions #####
def check_user_exists(user_id):
    """
    Check if a user exists in the system.
    
    Args:
        user_id (str): The user ID to check
        
    Returns:
        bool: True if user exists, False otherwise
        str: Error message if an exception occurred, None otherwise
    """
    try:
        response = requests.get(f"{USER_SERVICE_URL}/account/{user_id}")
        if response.status_code == 200:
            return True, None
        elif response.status_code == 404:
            return False, "User does not exist"
        else:
            logger.error(f"Failed to check if user exists: {response.status_code} - {response.text}")
            return False, f"Failed to verify user: {response.text}"
    except requests.RequestException as e:
        logger.error(f"Exception checking if user exists: {str(e)}")
        return False, f"Service unavailable: {str(e)}"

def check_fiat_account_exists(user_id, currency_code):
    """
    Check if a fiat account exists for the user with the specified currency code.
    
    Args:
        user_id (str): The user ID
        currency_code (str): The currency code
        
    Returns:
        bool: True if account exists, False otherwise
        dict or None: Account details if exists, None otherwise
        str: Error message if an exception occurred, None otherwise
    """
    try:
        response = requests.get(f"{FIAT_SERVICE_URL}/account/{user_id}/{currency_code}")
        if response.status_code == 200:
            return True, response.json(), None
        elif response.status_code == 404:
            return False, None, None
        else:
            logger.error(f"Failed to check if fiat account exists: {response.status_code} - {response.text}")
            return False, None, f"Failed to verify fiat account: {response.text}"
    except requests.RequestException as e:
        logger.error(f"Exception checking if fiat account exists: {str(e)}")
        return False, None, f"Service unavailable: {str(e)}"

def create_fiat_account(user_id, currency_code):
    """
    Create a new fiat account for the user with the specified currency code.
    
    Args:
        user_id (str): The user ID
        currency_code (str): The currency code
        
    Returns:
        bool: True if account was created successfully, False otherwise
        dict or None: Account details if created, None otherwise
        str: Error message if an exception occurred, None otherwise
    """
    try:
        payload = {
            "userId": user_id,
            "balance": 0,
            "currencyCode": currency_code
        }
        response = requests.post(f"{FIAT_SERVICE_URL}/account/", json=payload)
        if response.status_code == 201:
            return True, response.json(), None
        else:
            logger.error(f"Failed to create fiat account: {response.status_code} - {response.text}")
            return False, None, f"Failed to create fiat account: {response.text}"
    except requests.RequestException as e:
        logger.error(f"Exception creating fiat account: {str(e)}")
        return False, None, f"Service unavailable: {str(e)}"

##### API actions - flask restx API autodoc #####
# To use flask restx, you will also have to seperate the CRUD actions from the DB table classes
@deposit_ns.route("/fiat/")
class CreateDeposit(Resource):
    @deposit_ns.expect(transaction_input_model)
    @deposit_ns.response(201, "Deposit transaction initiated", transaction_output_model)
    @deposit_ns.response(400, "Bad Request")
    @deposit_ns.response(500, "Internal Server Error")
    def post(self):
        """Initiate a deposit transaction and return JSON for Swagger to display"""
        data = request.json

        # Validate required fields
        if not data.get("userId") or not data.get("amount") or not data.get("currencyCode"):
            logger.error("Missing required fields in request")
            return {"error": "Missing required fields"}, 400
   
        # Check if amount is valid
        if data.get("amount") <= 0:
            logger.error("Amount must be greater than zero")
            return {"error": "Validation Error", "message": "Amount must be greater than zero"}, 400
        
        user_id = data.get('userId')
        currency_code = data.get('currencyCode').lower()
        
        # Check if user exists
        user_exists, error_message = check_user_exists(user_id)
        if not user_exists:
            logger.error(f"User {user_id} does not exist: {error_message}")
            return {"error": "User Not Found", "message": error_message}, 404
        
        # Check if fiat account exists, create if it doesn't
        account_exists, account_details, error_message = check_fiat_account_exists(user_id, currency_code)
        
        if error_message:
            logger.error(f"Error checking fiat account: {error_message}")
            return {"error": "Service Unavailable", "message": error_message}, 500
        
        if not account_exists:
            logger.info(f"Fiat account for user {user_id} with currency {currency_code} does not exist. Creating new account.")
            account_created, account_details, error_message = create_fiat_account(user_id, currency_code)
            
            if not account_created:
                logger.error(f"Failed to create fiat account: {error_message}")
                return {"error": "Failed to Create Account", "message": error_message}, 500
        
        # Create transaction in the transaction service
        transaction_payload = {
            "userId": data.get('userId'),
            "amount": data.get('amount'),
            "currencyCode": data.get('currencyCode').lower(),
            "type": "deposit",
            "status": "pending"
        }
        logger.info(f"Sending transaction data to transaction service: {transaction_payload}")

        try:
            response = requests.post(f"{TRANSACTION_SERVICE_URL}/fiat/", json=transaction_payload)
            response.raise_for_status()
            transaction_data = response.json()
            transaction_id = transaction_data.get("transactionId")
            if not transaction_id:
                raise ValueError("Transaction service did not return a transactionId")
        except requests.RequestException as e:
            logger.error(f"Failed to store transaction: {e}")
            return {"error": "Failed to store transaction", "details": str(e)}, 500
        except ValueError as e:
            logger.error(str(e))
            return {"error": str(e)}, 500

        # Construct success and cancel URLs
        success_url = f"{FRONTEND_URL}/dashboard/deposit?status=success"
        cancel_url = f"{FRONTEND_URL}/dashboard/deposit?status=cancel"

        try:
            # Create Stripe checkout session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': data.get('currencyCode').lower(),
                        'product_data': {
                            'name': 'Fiat Deposit',
                        },
                        'unit_amount': int(data.get('amount') * 100),
                    },
                    'quantity': 1,
                }],
                mode='payment',
                client_reference_id=transaction_id,
                success_url=success_url,
                cancel_url=cancel_url,
            )
            logger.info(f"Stripe checkout session created: {checkout_session.url}")
        except Exception as e:
            logger.error(f"Failed to create Stripe checkout session: {e}")
            return {"error": "Failed to create Stripe checkout session", "details": str(e)}, 500

        # Return JSON so Swagger or any client gets a response
        return {
            "transactionId": transaction_id,
            "checkoutUrl": checkout_session.url,
            "amount": data.get('amount')
        }, 201

@deposit_ns.route("/webhook")
class StripeWebhook(Resource):
    def post(self):
        """Stripe Webhook to process payment events"""
        payload = request.data  # Get raw payload
        sig_header = request.headers.get("Stripe-Signature")

        try:
            # Validate Stripe payload and signature
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            logger.error("Invalid payload")
            return {"error": "Invalid payload"}, 400
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid signature")
            return {"error": "Invalid signature"}, 400

        # Only handle 'checkout.session.completed' events
        if event.get("type") == "checkout.session.completed":
            session = event["data"]["object"]
            transaction_id = session.get("client_reference_id")

            if transaction_id:
                try:
                    # 1) Retrieve the transaction details first
                    logger.info(f"Retrieving transaction details for ID: {transaction_id}")
                    trans_resp = requests.get(f"{TRANSACTION_SERVICE_URL}/fiat/{transaction_id}")
                    trans_resp.raise_for_status()
                    transaction_details = trans_resp.json()
                    user_id = transaction_details.get("userId")
                    currency_code = transaction_details.get("currencyCode").lower()
                    
                    # Validate required fields
                    if not user_id or not currency_code:
                        logger.error(f"Missing userId or currencyCode: {transaction_details}")
                        return {"error": "Missing required transaction data"}, 400
                    
                    # Check if user still exists
                    user_exists, error_message = check_user_exists(user_id)
                    if not user_exists:
                        logger.error(f"User {user_id} no longer exists: {error_message}")
                        # Update transaction to failed state
                        update_payload = {"status": "failed"}
                        requests.put(
                            f"{TRANSACTION_SERVICE_URL}/fiat/{transaction_id}",
                            json=update_payload
                        )
                        return {"error": "User Not Found", "message": error_message}, 404
                        
                    # Check if fiat account exists, create if not
                    account_exists, account_details, error_message = check_fiat_account_exists(user_id, currency_code)

                    if error_message:
                        logger.error(f"Error checking fiat account: {error_message}")
                        # Update transaction to failed state
                        update_payload = {"status": "failed"}
                        requests.put(
                            f"{TRANSACTION_SERVICE_URL}/fiat/{transaction_id}",
                            json=update_payload
                        )
                        return {"error": "Service Unavailable", "message": error_message}, 500

                    if not account_exists:
                        logger.info(f"Fiat account for user {user_id} with currency {currency_code} does not exist. Creating new account.")
                        account_created, account_details, error_message = create_fiat_account(user_id, currency_code)
                        
                        if not account_created:
                            logger.error(f"Failed to create fiat account: {error_message}")
                            # Update transaction to failed state
                            update_payload = {"status": "failed"}
                            requests.put(
                                f"{TRANSACTION_SERVICE_URL}/fiat/{transaction_id}",
                                json=update_payload
                            )
                            return {"error": "Failed to Create Account", "message": error_message}, 500

                    # 2) Update the Fiat Service (the user's wallet) first
                    # Convert Decimal to float for proper JSON serialization
                    try:
                        # First convert to string to maintain precision, then to float for JSON compatibility
                        amount = transaction_details.get("amount")
                        if not isinstance(amount, (int, float)):
                            logger.error(f"Invalid amount: {amount}")
                            return {"error": "Invalid amount"}, 400
                            
                        deposit_amount = float(amount)
                        
                        # Create payload according to API specification
                        fiat_payload = {"amountChanged": deposit_amount}
                        
                        # Set proper content-type header
                        headers = {"Content-Type": "application/json"}
                        
                        fiat_url = f"{FIAT_SERVICE_URL}/account/{user_id}/{currency_code}"
                        logger.info(f"Calling fiat service: PUT {fiat_url} with payload {fiat_payload}")
                        
                        fiat_response = requests.put(
                            fiat_url, 
                            json=fiat_payload,
                            headers=headers
                        )
                        
                        # Log detailed response for debugging
                        logger.info(f"Fiat service response: {fiat_response.status_code} - {fiat_response.text}")
                        
                        # Handle non-200 responses explicitly
                        if fiat_response.status_code != 200:
                            logger.error(f"Fiat service error: {fiat_response.status_code} - {fiat_response.text}")
                            return {"error": f"Failed to update balance: {fiat_response.text}"}, 500
                        
                        # Remove redundant raise_for_status()
                        
                        logger.info(
                            f"[Fiat Service] Wallet updated for user={user_id}, "
                            f"currency={currency_code} by {deposit_amount}."
                        )

                        # 3) After successfully updating the wallet, mark transaction as completed
                        update_payload = {"status": "completed"}
                        trans_update_response = requests.put(
                            f"{TRANSACTION_SERVICE_URL}/fiat/{transaction_id}",
                            json=update_payload,
                            headers=headers
                        )
                        
                        # Handle non-200 responses explicitly for transaction update
                        if trans_update_response.status_code != 200:
                            logger.error(f"Transaction service error: {trans_update_response.status_code} - {trans_update_response.text}")
                            return {"error": f"Failed to update transaction status: {trans_update_response.text}"}, 500
                            
                        # Remove redundant raise_for_status()
                        
                        logger.info(
                            f"[Transaction Service] Transaction {transaction_id} status set to 'completed'."
                        )
                    except (ValueError, TypeError) as e:
                        logger.error(f"Error converting amount: {e}")
                        return {"error": f"Amount conversion error: {str(e)}"}, 400


                except requests.RequestException as e:
                    logger.error(f"Failed during webhook handling for transaction {transaction_id}: {e}")
                    if hasattr(e, 'response') and e.response:
                        logger.error(f"Response details: {e.response.status_code} - {e.response.text}")
                    return {"error": f"Request failed: {str(e)}"}, 500
                
                except ValueError as e:
                    logger.error(f"Invalid transaction data for {transaction_id}: {e}")
                    return {"error": str(e)}, 400
                
                except Exception as e:
                    logger.error(f"Unexpected error: {str(e)}", exc_info=True)
                    return {"error": f"Unexpected error: {str(e)}"}, 500

                return {"message": "Payment processed successfully"}, 200

        return {"message": "Webhook received"}, 200


# Add namespace to API
api.add_namespace(deposit_ns)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)