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
API_ROOT = f'/{API_VERSION}/api'

app = Flask(__name__)
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    methods=["GET","POST","PUT","DELETE","OPTIONS"],
    allow_headers=["Content-Type","Authorization","X-Requested-With"]
)

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
TRANSACTION_SERVICE_URL = "http://transaction-service:5000/v1/api/transaction"
FIAT_SERVICE_URL = "http://fiat-service:5000/v1/api/fiat"

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
        "user_id": fields.String(required=True, description="User ID"),
        "amount": fields.Float(required=True, description="Amount to deposit"),
        "currency_code": fields.String(required=True, description="Currency code (default: USD)")
    }
)

# Output Model for a transaction
transaction_output_model = deposit_ns.model(
    "TransactionOutput", 
    {
        "transaction_id": fields.String(description="Transaction ID"),
        "checkout_url": fields.String(description="Stripe Checkout URL"),
        "amount": fields.Float(description="Amount deposited"),
    }
)

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
        if not data.get("user_id") or not data.get("amount") or not data.get("currency_code"):
            logger.error("Missing required fields in request")
            return {"error": "Missing required fields"}, 400

        # Create transaction in the transaction service
        transaction_payload = {
            "user_id": data.get('user_id'),
            "amount": data.get('amount'),
            "currency_code": data.get('currency_code'),
            "type": "deposit",
            "status": "pending"
        }
        logger.info(f"Sending transaction data to transaction service: {transaction_payload}")

        try:
            response = requests.post(f"{TRANSACTION_SERVICE_URL}/fiat/", json=transaction_payload)
            response.raise_for_status()
            transaction_data = response.json()
            transaction_id = transaction_data.get("transaction_id")
            if not transaction_id:
                raise ValueError("Transaction service did not return a transaction_id")
        except requests.RequestException as e:
            logger.error(f"Failed to store transaction: {e}")
            return {"error": "Failed to store transaction", "details": str(e)}, 500
        except ValueError as e:
            logger.error(str(e))
            return {"error": str(e)}, 500

        # Construct success and cancel URLs
        base_url = request.host_url.rstrip('/')
        success_url = f"{base_url}/v1/api/deposit/success/{transaction_id}"
        cancel_url = f"{base_url}/v1/api/deposit/cancel/{transaction_id}"

        try:
            # Create Stripe checkout session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': data.get('currency_code'),
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
            "transaction_id": transaction_id,
            "checkout_url": checkout_session.url,
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
                    user_id = transaction_details.get("user_id")
                    currency_code = transaction_details.get("currency_code")
                    
                    # Validate required fields
                    if not user_id or not currency_code:
                        logger.error(f"Missing user_id or currency_code: {transaction_details}")
                        return {"error": "Missing required transaction data"}, 400
                        
                    # 2) Update the Fiat Service (the user's wallet) first
                    # Convert Decimal to float for proper JSON serialization
                    try:
                        # First convert to string to maintain precision, then to float for JSON compatibility
                        deposit_amount = float(transaction_details.get("amount"))
                        
                        # Create payload according to API specification
                        fiat_payload = {"amount_changed": deposit_amount}
                        
                        # Set proper content-type header
                        headers = {"Content-Type": "application/json"}
                        
                        fiat_url = f"{FIAT_SERVICE_URL}/account/{user_id}/{currency_code}"
                        logger.info(f"Calling fiat service: PUT {fiat_url} with payload {fiat_payload}")
                        
                        fiat_response = requests.put(
                            fiat_url, 
                            json=fiat_payload,  # Use json parameter for proper serialization
                            headers=headers
                        )
                        
                        # Log detailed response for debugging
                        logger.info(f"Fiat service response: {fiat_response.status_code} - {fiat_response.text}")
                        
                        # Handle non-200 responses explicitly
                        if fiat_response.status_code != 200:
                            logger.error(f"Fiat service error: {fiat_response.status_code} - {fiat_response.text}")
                            return {"error": f"Failed to update balance: {fiat_response.text}"}, 500
                            
                        fiat_response.raise_for_status()  # Will raise an exception for 4XX/5XX responses
                        
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
                        trans_update_response.raise_for_status()
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