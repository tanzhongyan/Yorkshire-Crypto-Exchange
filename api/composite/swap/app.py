from flask import Flask, jsonify, request, Blueprint
from flask_cors import CORS
from flask_restx import Api, Resource, fields, Namespace
import requests


##### Configuration #####
# Define API version and root path
API_VERSION = 'v1'
API_ROOT = f'/{API_VERSION}/api'

app = Flask(__name__)
CORS(app)

# Flask swagger (flask_restx) api documentation
# Creates API documentation automatically
blueprint = Blueprint('api',__name__,url_prefix=API_ROOT)
api = Api(blueprint, version=API_VERSION, title='Swap Service API', description='Swap Service API for Yorkshire Crypto Exchange')

# Register Blueprint with Flask app
app.register_blueprint(blueprint)

# Environment variables for microservice
# Environment variables for microservice URLs
# NOTE: Do not use localhost here as localhost refer to this container itself
USERS_SERVICE_URL = "http://user-service:5000/v1/api/user"
FIAT_SERVICE_URL = "http://fiat-service:5000/v1/api/fiat"
CRYPTO_SERVICE_URL = "http://crypto-service:5000/v1/api/crypto"
TRANSACTION_SERVICE_URL = "http://transaction-service:5000/v1/api/transaction"


# Define namespaces to group api calls together
# Namespaces are essentially folders that group all related API calls
swap_ns = Namespace('swap', description='Swap related operations')
api.add_namespace(swap_ns)


##### API Models - flask restx API autodoc #####
# To use flask restx, you will have to define API models with their input types
# For all API models, add a comment to the top to signify its importance
# E.g. Input/Output One/Many user account
swap_request_model = swap_ns.model('SwapRequest', {
    'user_id': fields.String(required=True, description="User's ID"),
    'fiat_amount': fields.Float(required=True, description="Amount of fiat to swap"),
    'fiat_currency': fields.String(required=True, description="Currency code of fiat")
})

swap_response_model = swap_ns.model('SwapResponse', {
    'message': fields.String(description="Response message"),
    'transaction_details': fields.Raw(description="Details of the transaction")
})



##### API actions - flask restx API autodoc #####
@swap_ns.route('/')
class SwapResource(Resource):
    @swap_ns.expect(swap_request_model)
    @swap_ns.marshal_with(swap_response_model, code=201)
    def post(self):
        """Initiate a swap transaction."""
        data = request.json
        user_id = data['user_id']
        fiat_amount = data['fiat_amount']
        fiat_currency = data['fiat_currency']

        # Step 1: Log the transaction with pending status
        transaction_log = create_pending_transaction(user_id, fiat_amount, fiat_currency)
        
        if 'error' in transaction_log:
            swap_ns.abort(400, transaction_log['message'])
        
        # Step 2: Fetch exchange rate and calculate conversion
        exchange_result = get_exchange_rate(fiat_currency, "USD", fiat_amount)
        if 'error' in exchange_result:
            # Update transaction log as failed and terminate
            update_transaction_status(transaction_log['transaction_id'], 'failed')
            swap_ns.abort(400, exchange_result['message'])
        
        # Step 3: 
       



        # Example successful swap response (simplify according to actual process):
        return jsonify({
            'message': 'Swap initiated successfully',
            'transaction_details': transaction_log
        })

def create_pending_transaction(user_id, amount, currency_code):
    """Function to create a transaction log with 'pending' status using the transaction API."""
    transaction_data = {
        "user_id": user_id,
        "amount": amount,
        "currency_code": currency_code,
        "type": "swap",  # Assuming 'swap' is a valid type for your use case
        "status": "pending"
    }
    try:
        response = requests.post(f"{TRANSACTION_SERVICE_URL}/fiat/", json=transaction_data)
        if response.status_code == 201:
            return response.json()  # Returns the created transaction details
        else:
            return {'error': 'Failed to create transaction log', 'message': response.text}
    except requests.exceptions.RequestException as e:
        return {'error': 'Network error', 'message': str(e)}

def get_exchange_rate(from_currency, to_currency, amount):
    """Retrieve the exchange rate and calculate the conversion."""
    api_key = "35cbaa1f18ca3a26bcd96cec"
    url = f"https://v6.exchangerate-api.com/v6/{api_key}/pair/{from_currency}/USD/{amount}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data['result'] == 'success':
                converted_amount = data['conversion_result']
                return {
                    'rate': data['conversion_rate'],
                    'converted_amount': converted_amount
                }
            else:
                return {'error': 'Failed to fetch exchange rate', 'message': data.get('error-type', 'Unknown error')}
        else:
            return {'error': 'Failed to fetch exchange rate', 'message': 'Bad response from API'}
    except requests.exceptions.RequestException as e:
        return {'error': 'Network error', 'message': str(e)}


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)	