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
CORS(app)

# Flask swagger (flask_restx) api documentation
# Creates API documentation automatically
blueprint = Blueprint('api',__name__,url_prefix=API_ROOT)
api = Api(blueprint, version=API_VERSION, title='Market Service API', description='Market Service API for Yorkshire Crypto Exchange')

# Register Blueprint with Flask app
app.register_blueprint(blueprint)

# 2 ways to supply API key to root URL for coingecko
# header using curl 
# query string params

# Environment variables for microservice
# Environment variables for microservice URLs
# NOTE: Do not use localhost here as localhost refer to this container itself
COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/{coin}/market_chart"
# ORDERBOOK_URL = "https://personal-qrtp80l4.outsystemscloud.com/OrderBook_API/rest/v1/GetOrders?CryptoPair={CryptoPair}&Side={Side}"

# coingecko api
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")

# Define namespaces to group api calls together
# Namespaces are essentially folders that group all related API calls
market_ns = Namespace('market', description='Market related operations')


##### API Models - flask restx API autodoc #####
market_params = market_ns.model('MarketParams', {
    'coin': fields.String(required=False, default='bitcoin', description='Cryptocurrency name for CoinGecko API'),
    'days': fields.String(required=False, default='1', description='Time period for CoinGecko API'),
    # 'crypto_pair': fields.String(required=False, default='BTC-USD', description='Trading pair for OrderBook API'),
    # 'side': fields.String(required=False, description='Order side for OrderBook API (buy/sell)')
})

coin_gecko_model = market_ns.model('CoinGeckoData', {
    'prices': fields.Raw(description='Price data points [timestamp, price]'),
    'market_caps': fields.Raw(description='Market cap data points [timestamp, cap]'),
    'total_volumes': fields.Raw(description='Volume data points [timestamp, volume]')
})


market_response = market_ns.model('MarketDetailResponse', {
    'coinGecko': fields.Nested(coin_gecko_model, description='Data from CoinGecko API')
})

error_response = market_ns.model('ErrorResponse', {
    'errors': fields.Raw(description='Error details from various services')
})

# helper function
# get market chart data from coingecko
# historical price, volume
def get_coingecko_data(coin="bitcoin", days="30"):
    """
    Get market chart data from CoinGecko API
    
    Args:
        coin (str): Cryptocurrency name (default: bitcoin)
        days (str): Time period for data (default: 30)
        
    Returns:
        tuple: (data_dict, error_message)
    """
    try:
        # Format URL with parameters
        formatted_url = COINGECKO_URL.format(coin=coin)
        
        # Add query parameters
        params = {
            'vs_currency': 'usd',
            'days': days,
        }
        
        # Add authorization header if API key is provided
        headers = {}
        if COINGECKO_API_KEY:
            headers = {"x-cg-demo-api-key": COINGECKO_API_KEY}
        
        # Make the request
        response = requests.get(formatted_url, params=params, headers=headers)
        
        # Validate response
        if response.status_code == 200:
            return response.json(), None
        else:
            error_msg = f"Failed to fetch data from CoinGecko (Status: {response.status_code})"
            return None, error_msg
            
    except Exception as e:
        return None, f"Error fetching CoinGecko data: {str(e)}"


# helper function for outsystem order book
# must get 5 highest buy price & 5 lowest sell price for the crypto-usdt pair
# commented out till shahul updates order book

# def get_orderbook_data(crypto_pair="BTC-USD", side=None):
#     """
#     Get order book data from OrderBook API
    
#     Args:
#         crypto_pair (str): Trading pair (default: BTC-USD)
#         side (str): Order side (buy/sell), optional
        
#     Returns:
#         tuple: (data_dict, error_message)
#     """
#     try:
#         # Format URL with parameters
#         formatted_url = ORDERBOOK_URL.format(CryptoPair=crypto_pair, Side=side if side else "")
        
#         # Make the request
#         response = requests.get(formatted_url)
        
#         # Validate response
#         if response.status_code == 200:
#             return response.json(), None
#         else:
#             error_msg = f"Failed to fetch data from OrderBook (Status: {response.status_code})"
#             return None, error_msg
            
#     except Exception as e:
#         return None, f"Error fetching OrderBook data: {str(e)}"


##### API actions - flask restx API autodoc #####
@market_ns.route('')
class MarketDetailResource(Resource):
    @market_ns.doc(
        params={
            'coin': {'description': 'Cryptocurrency name for CoinGecko API', 'default': 'bitcoin'},
            'days': {'description': 'Time period for CoinGecko API', 'default': '30'},
            # 'crypto_pair': {'description': 'Trading pair for OrderBook API', 'default': 'BTC-USD'},
            # 'side': {'description': 'Order side for OrderBook API (buy/sell)'}
        },
        responses={
            200: 'Success',
            500: 'Server Error'
        }
    )
    @market_ns.marshal_with(market_response, code=200)
    @market_ns.marshal_with(error_response, code=500)
    def get(self):
        """
        Retrieve combined market data from CoinGecko and OrderBook
        
        This endpoint fetches and combines market data from multiple sources:
        - Historical price and volume data from CoinGecko
        - Order book data from the OrderBook service (currently disabled)
        """
        # Get parameters from request
        coin = request.args.get("coin", "bitcoin")
        days = request.args.get("days", "30")
        # crypto_pair = request.args.get("crypto_pair", "BTC-USD")
        # side = request.args.get("side")
        
        # Store errors
        errors = {}
        
        # Get CoinGecko data
        data_coin_gecko, error_coin_gecko = get_coingecko_data(coin, days)
        if error_coin_gecko:
            errors["coin_gecko"] = error_coin_gecko
        
        # Get OrderBook data (commented out till shahul updates orderbook)
        # data_order_book, error_order_book = get_orderbook_data(crypto_pair, side)
        # if error_order_book:
        #     errors["order_book"] = error_order_book
        
        # Return if any errors
        if errors:
            return {"errors": errors}, 500
        
        # Merge responses if no errors
        combined_market = {
            "coinGecko": data_coin_gecko
        }

        
        return combined_market

api.add_namespace(market_ns)


if __name__ == "__main__":
    if not COINGECKO_API_KEY:
        print("Warning: No CoinGecko API key found. Set COINGECKO_API_KEY environment variable.")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
