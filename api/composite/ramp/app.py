from flask import Flask, jsonify, request, Blueprint
from flask_cors import CORS
from flask_restx import Api, Resource, fields, Namespace
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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

# Flask swagger (flask_restx) api documentation
# Creates API documentation automatically
blueprint = Blueprint('api',__name__,url_prefix=API_ROOT)
api = Api(blueprint, version=API_VERSION, title='Ramp Service API', description='Ramp Service API for Yorkshire Crypto Exchange')

# Register Blueprint with Flask app
app.register_blueprint(blueprint)

# Environment variables for microservice
# Environment variables for microservice URLs
# NOTE: Do not use localhost here as localhost refer to this container itself
FIAT_SERVICE_URL = "http://fiat-service:5000/api/v1/fiat"
CRYPTO_SERVICE_URL = "http://crypto-service:5000/api/v1/crypto"
TRANSACTION_SERVICE_URL = "http://transaction-service:5000/api/v1/transaction"
EXCHANGE_RATE_API_KEY = os.getenv("EXCHANGE_RATE_API_KEY")

# Define namespaces to group api calls together
# Namespaces are essentially folders that group all related API calls
ramp_ns = Namespace('ramp', description='Ramp related operations')
api.add_namespace(ramp_ns)


#### API Models - flask restx API autodoc #####
swap_request_model = ramp_ns.model('SwapRequest', {
    'userId': fields.String(attribute="user_id", required=True, description="User's ID",
                example="a7c396e2-8370-4975-820e-c5ee8e3875c0"),
    'amount': fields.Float(required=True, description="Amount to swap (interpreted based on direction)",
                example=1000.0),
    'fiatCurrency': fields.String(attribute="fiat_currency", required=True, description="Currency code of fiat",
                example="sgd"),
    'tokenId': fields.String(attribute="token_id", required=True, description="Crypto token ID to swap to/from",
                example="usdt"),
    'direction': fields.String(required=True, description="Direction of swap: 'fiattocrypto' or 'cryptotofiat'",
                example="fiattocrypto")
})

ramp_response_model = ramp_ns.model('RampResponse', {
    'message': fields.String(description="Response message",
                example="Swap operation completed successfully"),
    'transactionDetails': fields.Raw(attribute="transaction_details", description="Details of the transaction",
                example={
                    "transactionId": "a1b2c3d4-e5f6-4a5b-9c8d-1e2f3a4b5c6d",
                    "userId": "a7c396e2-8370-4975-820e-c5ee8e3875c0",
                    "fromAmount": 1000.0,
                    "toAmount": 0.015,
                    "direction": "fiattocrypto",
                    "limitPrice": 65000.0,
                    "status": "completed",
                    "tokenId": "usdt",
                    "currencyCode": "sgd",
                    "creation": "2025-04-08T04:30:00",
                    "confirmation": "2025-04-08T04:32:15"
                })
})

error_model = ramp_ns.model('ErrorResponse', {
    'error': fields.String(description="Error type",
                example="insufficient_funds"),
    'message': fields.String(description="Error message",
                example="User has insufficient funds to complete this transaction"),
    'serviceResponse': fields.Raw(attribute="service_response", description="Original service response that caused the error",
                example={
                    "status": "error",
                    "code": 4001,
                    "details": "Available balance (500.00 USD) is less than requested amount (1000.00 USD)"
                })
})

##### Helper Functions #####
def check_fiat_account(user_id, currency_code):
    """
    Check if a user has a fiat account for the specified currency.
    
    Args:
        user_id (str): The user ID
        currency_code (str): The currency code
        
    Returns:
        dict: Account details if exists, None if not found, or error details
    """
    try:
        response = requests.get(f"{FIAT_SERVICE_URL}/account/{user_id}/{currency_code}")
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            return {
                'error': 'Failed to check fiat account', 
                'message': response.text,
                'serviceResponse': {
                    'statusCode': response.status_code,
                    'text': response.text
                }
            }
    except requests.exceptions.RequestException as e:
        return {'error': 'Network error', 'message': str(e)}

def update_fiat_balance(user_id, currency_code, amount_changed):
    """
    Update the balance of a user's fiat account.
    
    Args:
        user_id (str): The user ID
        currency_code (str): The currency code
        amount_changed (float): Amount to add (positive) or subtract (negative)
        
    Returns:
        dict: Updated account details or error details
    """
    try:
        payload = {"amountChanged": amount_changed}
        response = requests.put(f"{FIAT_SERVICE_URL}/account/{user_id}/{currency_code}", json=payload)
        if response.status_code == 200:
            return response.json()
        else:
            return {
                'error': 'Failed to update fiat balance', 
                'message': response.text,
                'serviceResponse': {
                    'statusCode': response.status_code,
                    'text': response.text,
                    'requestPayload': payload
                }
            }
    except requests.exceptions.RequestException as e:
        return {'error': 'Network error', 'message': str(e)}


def check_crypto_wallet(user_id):
    """
    Check if a user has a crypto wallet.
    
    Args:
        user_id (str): The user ID
        
    Returns:
        dict: Wallet details if exists, None if not found, or error details
    """
    try:
        response = requests.get(f"{CRYPTO_SERVICE_URL}/wallet/{user_id}")
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            return {
                'error': 'Failed to check crypto wallet', 
                'message': response.text,
                'serviceResponse': {
                    'statusCode': response.status_code,
                    'text': response.text
                }
            }
    except requests.exceptions.RequestException as e:
        return {'error': 'Network error', 'message': str(e)}


def create_crypto_wallet(user_id):
    """
    Create a new crypto wallet for a user.
    
    Args:
        user_id (str): The user ID
        
    Returns:
        dict: Created wallet details or error details
    """
    try:
        payload = {"userId": user_id}
        response = requests.post(f"{CRYPTO_SERVICE_URL}/wallet", json=payload)
        if response.status_code == 201:
            return response.json()
        else:
            return {
                'error': 'Failed to create crypto wallet', 
                'message': response.text,
                'serviceResponse': {
                    'statusCode': response.status_code,
                    'text': response.text,
                    'requestPayload': payload
                }
            }
    except requests.exceptions.RequestException as e:
        return {'error': 'Network error', 'message': str(e)}


def check_token_exists(token_id):
    """
    Check if a token exists in the system.
    
    Args:
        token_id (str): The token ID
        
    Returns:
        dict: Token details if exists, None if not found, or error details
    """
    try:
        response = requests.get(f"{CRYPTO_SERVICE_URL}/token/{token_id}")
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            return {
                'error': 'Failed to check token existence', 
                'message': response.text,
                'serviceResponse': {
                    'statusCode': response.status_code,
                    'text': response.text
                }
            }
    except requests.exceptions.RequestException as e:
        return {'error': 'Network error', 'message': str(e)}


def create_token(token_id, token_name=None):
    """
    Create a new token in the system.
    
    Args:
        token_id (str): The token ID
        token_name (str, optional): The token name, defaults to token_id if not provided
        
    Returns:
        dict: Created token details or error details
    """
    if not token_name:
        token_name = token_id
        
    try:
        payload = {
            "tokenId": token_id,
            "tokenName": token_name
        }
        response = requests.post(f"{CRYPTO_SERVICE_URL}/token", json=payload)
        if response.status_code == 201:
            return response.json()
        else:
            return {
                'error': 'Failed to create token', 
                'message': response.text,
                'serviceResponse': {
                    'statusCode': response.status_code,
                    'text': response.text,
                    'requestPayload': payload
                }
            }
    except requests.exceptions.RequestException as e:
        return {'error': 'Network error', 'message': str(e)}

def check_crypto_holding(user_id, token_id):
    """
    Check if a user has a crypto holding for the specified token.
    
    Args:
        user_id (str): The user ID
        token_id (str): The token ID
        
    Returns:
        dict: Holding details if exists, None if not found, or error details
    """
    try:
        response = requests.get(f"{CRYPTO_SERVICE_URL}/holdings/{user_id}/{token_id}")
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            return {
                'error': 'Failed to check crypto holding', 
                'message': response.text,
                'serviceResponse': {
                    'statusCode': response.status_code,
                    'text': response.text
                }
            }
    except requests.exceptions.RequestException as e:
        return {'error': 'Network error', 'message': str(e)}


def deposit_crypto(user_id, token_id, amount):
    """
    Deposit crypto into a user's holding.
    Increases both actual and available balance.
    
    Args:
        user_id (str): The user ID
        token_id (str): The token ID
        amount (float): Amount to deposit
        
    Returns:
        dict: Response from the API or error details
    """
    try:
        payload = {
            "userId": user_id,
            "tokenId": token_id,
            "amountChanged": amount
        }
        response = requests.post(f"{CRYPTO_SERVICE_URL}/holdings/deposit", json=payload)
        if response.status_code == 200:
            return {'message': 'Crypto deposit successful'}
        else:
            return {
                'error': 'Failed to deposit crypto', 
                'message': response.text,
                'serviceResponse': {
                    'statusCode': response.status_code,
                    'text': response.text,
                    'requestPayload': payload
                }
            }
    except requests.exceptions.RequestException as e:
        return {'error': 'Network error', 'message': str(e)}


def withdraw_crypto(user_id, token_id, amount):
    """
    Withdraw crypto from a user's holding.
    Reduces both actual and available balance.
    
    Args:
        user_id (str): The user ID
        token_id (str): The token ID
        amount (float): Amount to withdraw
        
    Returns:
        dict: Response from the API or error details
    """
    try:
        payload = {
            "userId": user_id,
            "tokenId": token_id,
            "amountChanged": amount
        }
        response = requests.post(f"{CRYPTO_SERVICE_URL}/holdings/withdraw", json=payload)
        if response.status_code == 200:
            return {'message': 'Crypto withdrawal successful'}
        else:
            return {
                'error': 'Failed to withdraw crypto', 
                'message': response.text,
                'serviceResponse': {
                    'statusCode': response.status_code,
                    'text': response.text,
                    'requestPayload': payload
                }
            }
    except requests.exceptions.RequestException as e:
        return {'error': 'Network error', 'message': str(e)}


def create_crypto_holding(user_id, token_id, amount):
    """
    Create a new crypto holding for a user.
    
    Args:
        user_id (str): The user ID
        token_id (str): The token ID
        amount (float): Initial balance
        
    Returns:
        dict: Created holding details or error details
    """
    try:
        payload = {
            "userId": user_id,
            "tokenId": token_id,
            "actualBalance": amount,
            "availableBalance": amount  # Set both balances to the same amount
        }
        response = requests.post(f"{CRYPTO_SERVICE_URL}/holdings", json=payload)
        if response.status_code == 201:
            return response.json()
        else:
            return {
                'error': 'Failed to create crypto holding', 
                'message': response.text,
                'serviceResponse': {
                    'statusCode': response.status_code,
                    'text': response.text,
                    'requestPayload': payload
                }
            }
    except requests.exceptions.RequestException as e:
        return {'error': 'Network error', 'message': str(e)}


def create_fiat_to_crypto_transaction(user_id, from_amount, to_amount, direction, token_id, currency_code, limit_price):
    """
    Create a fiat to crypto transaction record.
    
    Args:
        user_id (str): The user ID
        from_amount (float): Amount being swapped from (in source currency)
        to_amount (float): Amount being swapped to (in target currency)
        direction (str): 'fiattocrypto' or 'cryptotofiat'
        token_id (str): The crypto token ID
        currency_code (str): The fiat currency code
        limit_price (float): Exchange rate between currencies
        
    Returns:
        dict: Created transaction details or error details
    """
    try:
        payload = {
            "userId": user_id,
            "fromAmount": from_amount,
            "toAmount": to_amount,
            "direction": direction,
            "limitPrice": limit_price,
            "status": "pending",
            "tokenId": token_id,
            "currencyCode": currency_code
        }
        response = requests.post(f"{TRANSACTION_SERVICE_URL}/fiattocrypto/", json=payload)
        if response.status_code == 201:
            return response.json()
        else:
            return {
                'error': 'Failed to create transaction record', 
                'message': response.text,
                'serviceResponse': {
                    'statusCode': response.status_code,
                    'text': response.text,
                    'requestPayload': payload
                }
            }
    except requests.exceptions.RequestException as e:
        return {'error': 'Network error', 'message': str(e)}

def update_transaction_status(transaction_id, status, to_amount=None):
    """
    Update the status of a fiat to crypto transaction.
    
    Args:
        transaction_id (str): The transaction ID
        status (str): The new status
        to_amount (float, optional): Updated to_amount if available
        
    Returns:
        dict: Updated transaction details or error details
    """
    try:
        # First get the current transaction to preserve all fields
        get_response = requests.get(f"{TRANSACTION_SERVICE_URL}/fiattocrypto/{transaction_id}")
        if get_response.status_code != 200:
            return {
                'error': 'Failed to retrieve transaction', 
                'message': get_response.text,
                'serviceResponse': {
                    'statusCode': get_response.status_code,
                    'text': get_response.text
                }
            }
        
        transaction = get_response.json()
        
        # Update fields
        transaction['status'] = status
        if to_amount is not None:
            transaction['toAmount'] = to_amount
        
        # Send the update request
        response = requests.put(f"{TRANSACTION_SERVICE_URL}/fiattocrypto/{transaction_id}", json=transaction)
        if response.status_code == 200:
            return response.json()
        else:
            return {
                'error': 'Failed to update transaction status', 
                'message': response.text,
                'serviceResponse': {
                    'statusCode': response.status_code,
                    'text': response.text,
                    'requestPayload': transaction
                }
            }
    except requests.exceptions.RequestException as e:
        return {'error': 'Network error', 'message': str(e)}


def create_fiat_account(user_id, currency_code, initial_balance=0):
    """
    Create a new fiat account for a user.
    
    Args:
        user_id (str): The user ID
        currency_code (str): The currency code
        initial_balance (float, optional): Initial balance for the account
        
    Returns:
        dict: Created account details or error details
    """
    try:
        payload = {
            "userId": user_id,
            "currencyCode": currency_code,
            "balance": initial_balance
        }
        response = requests.post(f"{FIAT_SERVICE_URL}/account/", json=payload)
        if response.status_code == 201:
            return response.json()
        else:
            return {
                'error': 'Failed to create fiat account', 
                'message': response.text,
                'serviceResponse': {
                    'statusCode': response.status_code,
                    'text': response.text,
                    'requestPayload': payload
                }
            }
    except requests.exceptions.RequestException as e:
        return {'error': 'Network error', 'message': str(e)}

def get_exchange_rate(from_currency, to_currency, amount):
    """
    Retrieve the exchange rate and calculate the conversion.
    
    Args:
        from_currency (str): Source currency code
        to_currency (str): Target currency code
        amount (float): Amount to convert
        
    Returns:
        dict: Conversion details or error details
    """
    if not EXCHANGE_RATE_API_KEY:
        return {'error': 'Missing API key', 'message': 'Exchange rate API key is not configured'}
    
    url = f"https://v6.exchangerate-api.com/v6/{EXCHANGE_RATE_API_KEY}/pair/{from_currency}/{to_currency}/{amount}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data['result'] == 'success':
                converted_amount = data['conversion_result']
                return {
                    'rate': data['conversion_rate'],
                    'convertedAmount': converted_amount
                }
            else:
                return {
                    'error': 'Failed to fetch exchange rate', 
                    'message': data.get('error-type', 'Unknown error'),
                    'serviceResponse': data
                }
        else:
            return {
                'error': 'Failed to fetch exchange rate', 
                'message': 'Bad response from API',
                'serviceResponse': {
                    'statusCode': response.status_code,
                    'text': response.text
                }
            }
    except requests.exceptions.RequestException as e:
        return {'error': 'Network error', 'message': str(e)}

##### API actions - flask restx API autodoc #####
@ramp_ns.route('/swap')
class SwapResource(Resource):
    @ramp_ns.expect(swap_request_model)
    @ramp_ns.response(201, 'Swap completed successfully', ramp_response_model)
    @ramp_ns.response(400, 'Bad request - invalid input data', error_model)
    @ramp_ns.response(404, 'Resource not found', error_model)
    @ramp_ns.response(500, 'Server error', error_model)
    def post(self):
        """
        Swap between fiat and crypto currencies.
        
        This endpoint facilitates swapping between fiat and crypto currencies.
        Direction can be either 'fiattocrypto' or 'cryptotofiat'.
        
        For 'fiattocrypto':
        - The amount is interpreted as fiat amount to swap
        - Fiat is deducted from the user's fiat account
        - Equivalent crypto is added to the user's crypto holding
        
        For 'cryptotofiat':
        - The amount is interpreted as crypto amount to swap
        - Crypto is deducted from the user's crypto holding
        - Equivalent fiat is added to the user's fiat account
        """
        data = request.json
        user_id = data['userId']
        amount = data['amount']
        fiat_currency = data['fiatCurrency']
        token_id = data['tokenId']
        direction = data['direction'].lower()
        
        # Validate direction
        if direction not in ['fiattocrypto', 'cryptotofiat']:
            return {'error': 'Invalid direction', 'message': "Direction must be 'fiattocrypto' or 'cryptotofiat'"}, 400
        
        # Validate amount
        if amount <= 0:
            return {'error': 'Invalid amount', 'message': "Amount must be greater than zero"}, 400
        
        # Direct to appropriate swap function based on direction
        if direction == 'fiattocrypto':
            return self.fiat_to_crypto_swap(user_id, amount, fiat_currency, token_id)
        else:
            return self.crypto_to_fiat_swap(user_id, amount, fiat_currency, token_id)
    
    def fiat_to_crypto_swap(self, user_id, fiat_amount, fiat_currency, token_id):
        """
        Handle swapping from fiat to crypto.
        
        Args:
            user_id (str): The user ID
            fiat_amount (float): Amount of fiat to swap
            fiat_currency (str): The fiat currency code
            token_id (str): The crypto token ID to swap to
            
        Returns:
            dict: Response with transaction details or error message
        """
        # Step 1: Check if user has fiat account
        fiat_account = check_fiat_account(user_id, fiat_currency)
        if not fiat_account:
            return {'error': 'Fiat account not found', 'message': f"No {fiat_currency} account found for user {user_id}"}, 404
        
        if 'error' in fiat_account:
            return fiat_account, 500
        
        # Step 2: Check if fiat account has sufficient balance
        if fiat_account['balance'] < fiat_amount:
            return {'error': 'Insufficient balance', 'message': f"Insufficient {fiat_currency} balance. Required: {fiat_amount}, Available: {fiat_account['balance']}"}, 400
        
        # Step 3: Check if user has a crypto wallet, create if not
        wallet = check_crypto_wallet(user_id)
        if not wallet:
            wallet_result = create_crypto_wallet(user_id)
            if 'error' in wallet_result:
                return wallet_result, 500
        
        # Step 4: Check if token exists in system, create if not
        token = check_token_exists(token_id)
        if not token:
            token_result = create_token(token_id)
            if 'error' in token_result:
                return token_result, 500
        
        # Step 5: Get exchange rate and calculate conversion
        exchange_result = get_exchange_rate(fiat_currency, 'USD', fiat_amount)
        
        if 'error' in exchange_result:
            return exchange_result, 500
        
        converted_amount = exchange_result['convertedAmount']
        
        # Calculate limit price - for fiat to crypto, it's 1/rate
        limit_price = 1 / exchange_result['rate']
        
        # Step 6: Create a pending transaction record with proper values
        transaction = create_fiat_to_crypto_transaction(
            user_id=user_id,
            from_amount=fiat_amount,
            to_amount=converted_amount,  # Set the expected crypto amount
            direction='fiattocrypto',
            token_id=token_id,
            currency_code=fiat_currency,
            limit_price=limit_price  # Set the exchange rate
        )
        
        if 'error' in transaction:
            return transaction, 500
        
        # Get transaction ID for future updates
        transaction_id = transaction['transactionId']
        
        # Step 7: Deduct fiat amount from user's account
        fiat_update = update_fiat_balance(user_id, fiat_currency, -fiat_amount)
        
        if 'error' in fiat_update:
            # Update transaction as failed
            update_transaction_status(transaction_id, 'failed')
            return fiat_update, 500
        
        # Step 8: Check if user already has a holding for the token
        crypto_holding = check_crypto_holding(user_id, token_id)
        
        # Step 9: Add converted amount to user's crypto holding
        if crypto_holding and 'error' not in crypto_holding:
            # User already has a holding, deposit to it
            deposit_result = deposit_crypto(user_id, token_id, converted_amount)
            
            if 'error' in deposit_result:
                # Rollback fiat deduction
                rollback = update_fiat_balance(user_id, fiat_currency, fiat_amount)
                # Update transaction as failed
                update_transaction_status(transaction_id, 'failed')
                return {
                    'error': deposit_result['error'],
                    'message': deposit_result['message'],
                    'rollbackResult': rollback,
                    'serviceResponse': deposit_result.get('serviceResponse', {})
                }, 500
        else:
            # User doesn't have a holding, create one
            holding_result = create_crypto_holding(user_id, token_id, converted_amount)
            
            if 'error' in holding_result:
                # Rollback fiat deduction
                rollback = update_fiat_balance(user_id, fiat_currency, fiat_amount)
                # Update transaction as failed
                update_transaction_status(transaction_id, 'failed')
                return {
                    'error': holding_result['error'],
                    'message': holding_result['message'],
                    'rollbackResult': rollback,
                    'serviceResponse': holding_result.get('serviceResponse', {})
                }, 500
        
        # Step 10: Update transaction with final details and mark as successful
        final_transaction = update_transaction_status(transaction_id, 'completed', converted_amount)
        
        if 'error' in final_transaction:
            # Log the error but don't fail the request since the swap itself was successful
            print(f"Warning: Failed to update transaction status: {final_transaction['message']}")
        
        # Return success response
        return {
            'message': 'Swap completed successfully',
            'transactionDetails': {
                'userId': user_id,
                'fromAmount': fiat_amount,
                'fromCurrency': fiat_currency,
                'toAmount': converted_amount,
                'toCurrency': token_id,
                'exchangeRate': exchange_result['rate'],
                'limitPrice': limit_price,
                'transactionId': transaction_id,
                'status': 'completed'
            }
        }, 201
    
    def crypto_to_fiat_swap(self, user_id, crypto_amount, fiat_currency, token_id):
        """
        Handle swapping from crypto to fiat.
        
        Args:
            user_id (str): The user ID
            crypto_amount (float): Amount of crypto to swap
            fiat_currency (str): The fiat currency code to swap to
            token_id (str): The crypto token ID to swap from
            
        Returns:
            dict: Response with transaction details or error message
        """
        # Step 1: Check if user has crypto holding
        crypto_holding = check_crypto_holding(user_id, token_id)
        if not crypto_holding:
            return {'error': 'Crypto holding not found', 'message': f"No {token_id} holding found for user {user_id}"}, 404
        
        if 'error' in crypto_holding:
            return crypto_holding, 500
        
        # Step 2: Check if crypto holding has sufficient available balance
        if crypto_holding['availableBalance'] < crypto_amount:
            return {'error': 'Insufficient balance', 'message': f"Insufficient {token_id} balance. Required: {crypto_amount}, Available: {crypto_holding['availableBalance']}"}, 400
        
        # Step 3: Get exchange rate from crypto to fiat
        # Assume crypto amount is in USD equivalent
        exchange_result = get_exchange_rate('USD', fiat_currency, crypto_amount)
        
        if 'error' in exchange_result:
            return exchange_result, 500
        
        # Get equivalent fiat amount
        fiat_amount = exchange_result['convertedAmount']
        
        # Calculate limit price - for crypto to fiat, it's the direct rate
        limit_price = exchange_result['rate']
        
        # Step 4: Create a pending transaction record with proper values
        transaction = create_fiat_to_crypto_transaction(
            user_id=user_id,
            from_amount=crypto_amount,
            to_amount=fiat_amount,  # Set the expected fiat amount
            direction='cryptotofiat',
            token_id=token_id,
            currency_code=fiat_currency,
            limit_price=limit_price  # Set the exchange rate
        )
        
        if 'error' in transaction:
            return transaction, 500
        
        # Get transaction ID for future updates
        transaction_id = transaction['transactionId']
        
        # Step 5: Withdraw crypto from user's holding
        withdraw_result = withdraw_crypto(user_id, token_id, crypto_amount)
        
        if 'error' in withdraw_result:
            # Update transaction as failed
            update_transaction_status(transaction_id, 'failed')
            return withdraw_result, 500
        
        # Step 6: Check if user has fiat account for the target currency
        fiat_account = check_fiat_account(user_id, fiat_currency)
        
        if not fiat_account and 'error' not in fiat_account:
            # Create new fiat account if it doesn't exist
            create_account_result = create_fiat_account(user_id, fiat_currency)
            
            if 'error' in create_account_result:
                # Rollback crypto withdrawal
                rollback = deposit_crypto(user_id, token_id, crypto_amount)
                # Update transaction as failed
                update_transaction_status(transaction_id, 'failed')
                return {
                    'error': create_account_result['error'],
                    'message': create_account_result['message'],
                    'rollbackResult': rollback,
                    'serviceResponse': create_account_result.get('serviceResponse', {})
                }, 500
        elif 'error' in fiat_account:
            # Rollback crypto withdrawal
            rollback = deposit_crypto(user_id, token_id, crypto_amount)
            # Update transaction as failed
            update_transaction_status(transaction_id, 'failed')
            return fiat_account, 500
        
        # Step 7: Add fiat amount to user's account
        fiat_update = update_fiat_balance(user_id, fiat_currency, fiat_amount)
        
        if 'error' in fiat_update:
            # Rollback crypto withdrawal
            rollback = deposit_crypto(user_id, token_id, crypto_amount)
            # Update transaction as failed
            update_transaction_status(transaction_id, 'failed')
            return {
                'error': fiat_update['error'],
                'message': fiat_update['message'],
                'rollbackResult': rollback,
                'serviceResponse': fiat_update.get('serviceResponse', {})
            }, 500
        
        # Step 8: Update transaction with final details and mark as successful
        final_transaction = update_transaction_status(transaction_id, 'completed')
        
        if 'error' in final_transaction:
            # Log the error but don't fail the request since the swap itself was successful
            print(f"Warning: Failed to update transaction status: {final_transaction['message']}")
        
        # Return success response
        return {
            'message': 'Swap completed successfully',
            'transactionDetails': {
                'userId': user_id,
                'fromAmount': crypto_amount,
                'fromCurrency': token_id,
                'toAmount': fiat_amount,
                'toCurrency': fiat_currency,
                'exchangeRate': exchange_result['rate'],
                'limitPrice': limit_price,
                'transactionId': transaction_id,
                'status': 'completed'
            }
        }, 201


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)