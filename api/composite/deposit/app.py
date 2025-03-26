from flask import Flask, request, jsonify, Blueprint, redirect
from flask_cors import CORS
from flask_restx import Api, Resource, fields, Namespace
import stripe
import requests
import uuid
import logging
import os
from dotenv import load_dotenv
from datetime import datetime


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
TRANSACTION_SERVICE_URL = "http://transaction-service:5000/v1/api/transaction"

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
            "type": "deposit",
            "status": "pending"
        }
        logger.info(f"Sending transaction data to transaction service: {transaction_payload}")

        try:
            response = requests.post(f"{TRANSACTION_SERVICE_URL}/fiat", json=transaction_payload)
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
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            logger.error("Invalid payload")
            return {"error": "Invalid payload"}, 400
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid signature")
            return {"error": "Invalid signature"}, 400

        if event.get("type") == "checkout.session.completed":
            session = event["data"]["object"]
            transaction_id = session.get("client_reference_id")

            if transaction_id:
                update_payload = {"status": "completed"}
                try:
                    response = requests.put(f"{TRANSACTION_SERVICE_URL}/fiat/{transaction_id}", json=update_payload)
                    response.raise_for_status()
                    logger.info(f"Transaction {transaction_id} updated successfully.")
                except requests.RequestException as e:
                    logger.error(f"Failed to update transaction {transaction_id}: {e}")
                    return {"error": "Failed to update transaction"}, 500

        return {"message": "Webhook received"}, 200

# Add namespace to API
api.add_namespace(deposit_ns)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)