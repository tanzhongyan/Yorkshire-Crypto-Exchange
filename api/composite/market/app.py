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
COINGECKO_MARKET_CHART_URL = "https://api.coingecko.com/api/v3/coins/{coin}/market_chart"
COINGECKO_SIMPLE_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"
ORDERBOOK_GET_ALL_URL = "https://personal-qrtp80l4.outsystemscloud.com/OrderBook_API/rest/v1/GetAllOrders"
ORDERBOOK_GET_BY_TOKEN_URL = "https://personal-qrtp80l4.outsystemscloud.com/OrderBook_API/rest/v1/GetOrdersByToken?FromTokenId={FromTokenId}&ToTokenId={ToTokenId}"

# New Exchange Rate API URL
EXCHANGE_RATE_API_URL = "https://v6.exchangerate-api.com/v6/{api_key}/latest/USD"

# coingecko api
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")

# Fiat Exchange Rate API key
EXCHANGE_RATE_API_KEY = os.getenv("EXCHANGE_RATE_API_KEY")

# Define namespaces to group api calls together
# Namespaces are essentially folders that group all related API calls
market_ns = Namespace('market', description='Market related operations')
orderbook_ns = Namespace('orderbook', description='Orderbook related operations')

api.add_namespace(market_ns)
api.add_namespace(orderbook_ns)

##### API Models - flask restx API autodoc #####
market_params = market_ns.model('MarketParams', {
    'coin': fields.String(required=False, default='bitcoin', description='Cryptocurrency name for CoinGecko API'),
    'days': fields.String(required=False, default='1', description='Time period for CoinGecko API'),
})

# /market response
coin_gecko_model = market_ns.model('CoinGeckoData', {
    'prices': fields.Raw(description='Price data points [timestamp, price]'),
    'market_caps': fields.Raw(description='Market cap data points [timestamp, cap]'),
    'total_volumes': fields.Raw(description='Volume data points [timestamp, volume]')
})

market_response = market_ns.model('MarketResponse', {
    'coinGecko': fields.Nested(coin_gecko_model, description='Data from CoinGecko API')
})

# market/exchangerate response model
exchange_rate_response = market_ns.model('ExchangeRateResponse', {
    'rates': fields.Raw(description='Exchange rates for requested tokens against USDT')
})

# market/fiatrates API response model
exchange_rate_api_response = market_ns.model('ExchangeRateApiResponse', {
    'base_code': fields.String(description='Base currency code'),
    'conversion_rates': fields.Raw(description='Currency conversion rates'),
    'time_last_update_utc': fields.String(description='Last update time in UTC')
})

# orders model from outsystem orderbook
# same as json response from orderbook, we are only working with limit 
orderbook_model = orderbook_ns.model('OrderBookData', {
    'transactionId': fields.String(description='Unique identifier for the transaction'),
    'userId': fields.String(description='Unique identifier for the user'),
    'orderType': fields.String(description='Type of order (e.g., limit)', example='limit'),
    'fromTokenId': fields.String(description='Source token identifier'),
    'toTokenId': fields.String(description='Destination token identifier'),
    'fromAmount': fields.Float(description='Amount of source token'),
    'limitPrice': fields.Float(description='Limit price for the order'),
    'creation': fields.DateTime(description='Timestamp of order creation', example='2014-12-31T23:59:59.937Z')
})

# /recentorders output model
recent_orders_response = orderbook_ns.model('RecentOrderResponse', {
    'orders': fields.List(fields.Nested(orderbook_model), description='List of recent orders in the orderbook')
})

# /sortedorders output model (buy contains 5 most expensive usdt to crypto buy-ins, sell contains 5 cheapest crypto to usdt sell-outs)
sorted_orders_response = orderbook_ns.model('SortedOrdersResponse', {
    'buy': fields.List(fields.Nested(orderbook_model), description='List of 5 most expensive buy orders (USDT to token)'),
    'sell': fields.List(fields.Nested(orderbook_model), description='List of 5 cheapest sell orders (token to USDT)')
})

#### - HELPER FUNCTIONS - ####

# helper function to convert symbol to coingecko ID
def symbol_to_coingecko_id(symbol):
    """
    Convert common cryptocurrency symbols to CoinGecko IDs
    
    Args:
        symbol (str): Cryptocurrency symbol (e.g., BTC, ETH)
        
    Returns:
        str: CoinGecko ID for the symbol
    """
    symbol_map = {
        'BTC': 'bitcoin',
        'ETH': 'ethereum',
        'XRP': 'ripple',
        'USDT': 'tether',
        'BNB': 'binancecoin',
        'ADA': 'cardano',
        'SOL': 'solana',
        'DOGE': 'dogecoin',
        'DOT': 'polkadot',
        'MATIC': 'matic-network',
        'LTC': 'litecoin',
        'LINK': 'chainlink',
        'AVAX': 'avalanche-2',
    }
    
    return symbol_map.get(symbol.upper(), symbol.lower())

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
        formatted_url = COINGECKO_MARKET_CHART_URL.format(coin=coin)
        
        # http get by query params
        params = {
            'vs_currency': 'usd',
            'days': days,
        }
        
        headers = {}
        if COINGECKO_API_KEY:
            headers = {"x-cg-demo-api-key": COINGECKO_API_KEY}
        
        response = requests.get(formatted_url, params=params, headers=headers)
        
        if response.status_code == 200:
            return response.json(), None
        else:
            error_msg = f"Failed to fetch data from CoinGecko (Status: {response.status_code})"
            return None, error_msg
            
    except Exception as e:
        return None, f"Error fetching CoinGecko data: {str(e)}"

# helper function to get exchange rates
def get_exchange_rates(tokens):
    """
    Get exchange rates for specified tokens against USDT
    
    Args:
        tokens (list): List of cryptocurrency tokens (e.g., BTC, ETH, XRP)
        
    Returns:
        tuple: (rates_dict, error_message)
    """
    try:
        # convert token symbols to coingecko IDs
        token_ids = [symbol_to_coingecko_id(token) for token in tokens]
        
        # get by query params
        params = {
            'ids': ','.join(token_ids),
            'vs_currencies': 'usd'  # use USD as a proxy for USDT
        }
        
        headers = {}
        if COINGECKO_API_KEY:
            headers = {"x-cg-demo-api-key": COINGECKO_API_KEY}
        
        response = requests.get(COINGECKO_SIMPLE_PRICE_URL, params=params, headers=headers)
        
        # validation
        if response.status_code == 200:
            data = response.json()
            
            # convert to our desired output format
            rates = {}
            for token in tokens:
                token_id = symbol_to_coingecko_id(token)
                if token_id in data and 'usd' in data[token_id]:
                    rates[token] = data[token_id]['usd']
                else:
                    rates[token] = None
            
            return rates, None
        else:
            error_msg = f"Failed to fetch exchange rates from CoinGecko (Status: {response.status_code})"
            return None, error_msg
            
    except Exception as e:
        return None, f"Error fetching exchange rates: {str(e)}"


# helper function to get exchange rates from Exchange Rate API
def get_exchange_rate_api_data(base_currency="USD"):
    """
    Get exchange rates from Exchange Rate API
    
    Args:
        base_currency (str): Base currency code (default: USD)
        
    Returns:
        tuple: (data_dict, error_message)
    """
    try:
        if not EXCHANGE_RATE_API_KEY:
            return None, "Exchange Rate API key not provided"
        
        # Format URL with API key
        formatted_url = EXCHANGE_RATE_API_URL.format(api_key=EXCHANGE_RATE_API_KEY)
        
        # Make the request
        response = requests.get(formatted_url)
        
        # Validate response
        if response.status_code == 200:
            return response.json(), None
        else:
            error_msg = f"Failed to fetch data from Exchange Rate API (Status: {response.status_code})"
            return None, error_msg
            
    except Exception as e:
        return None, f"Error fetching Exchange Rate API data: {str(e)}"


# helper function for outsystem order book 5 most recent orders timestamped on order creation
def get_ten_recent_orders():
    """
    Get 10 most recent orders from OrderBook API
    
    Returns:
        tuple: (data_list, error_message)
    """
    try:
        # make request to OrderBook API in outsystems 
        response = requests.get(ORDERBOOK_GET_ALL_URL)
        
        # validation
        if response.status_code == 200:
            data = response.json()
            
            # check if orders exist in the response
            if 'orders' in data and isinstance(data['orders'], list):

                # filter such that only limit orders will be sorted 
                limit_orders = [order for order in data['orders'] if order.get('orderType') == 'limit']
                # sort orders by creation date (newest first)
                sorted_orders = sorted(
                    limit_orders, 
                    key=lambda x: x.get('creation', ''), 
                    reverse=True
                )
                
                # get 10 most recent by creation timestamp
                recent_orders = sorted_orders[:10]
                
                return recent_orders, None
            else:
                return [], None  # return empty list if no orders field
        else:
            return None, "Failed to fetch data from OrderBook API"
            
    except Exception as e:
        return None, f"Error fetching OrderBook data: {str(e)}"
    
# helper function to get sorted orders for a input token
def get_sorted_orders(token):
    """
    Get 5 most expensive buy orders and 5 cheapest sell orders for a specific token
    
    Args:
        token (str): Token identifier (e.g., BTC, ETH)
        
    Returns:
        tuple: (data_dict, error_message)
    """
    try:
        # get buy orders (USDT to input token)
        buy_url = ORDERBOOK_GET_BY_TOKEN_URL.format(FromTokenId='usdt', ToTokenId=token)
        buy_response = requests.get(buy_url)
        
        # get sell orders (input token to USDT)
        sell_url = ORDERBOOK_GET_BY_TOKEN_URL.format(FromTokenId=token, ToTokenId='usdt')
        sell_response = requests.get(sell_url)
        
        # success request?
        if buy_response.status_code == 200 and sell_response.status_code == 200:
            buy_data = buy_response.json()
            sell_data = sell_response.json()
            
            # sorting buy orders - get 5 most expensive (highest limit price)
            buy_orders = []
            if 'orders' in buy_data and isinstance(buy_data['orders'], list):
                # filter buy orders and sort by limit price (highest first)
                filtered_buy_orders = [order for order in buy_data['orders'] if order.get('orderType') == 'limit']
                sorted_buy_orders = sorted(filtered_buy_orders, key=lambda x: x.get('limitPrice', 0), reverse=True)
                buy_orders = sorted_buy_orders[:5]
            
            # sorting sell orders - get 5 cheapest (lowest limit price)
            sell_orders = []
            if 'orders' in sell_data and isinstance(sell_data['orders'], list):
                # filter sell orders and sort by limit price (lowest first)
                filtered_sell_orders = [order for order in sell_data['orders'] if order.get('orderType') == 'limit']
                sorted_sell_orders = sorted(filtered_sell_orders, key=lambda x: x.get('limitPrice', 0))
                sell_orders = sorted_sell_orders[:5]
            
            return {"buy": buy_orders, "sell": sell_orders}, None
        else:
            error_msg = f"Failed to fetch data from OrderBook API (Buy Status: {buy_response.status_code}, Sell Status: {sell_response.status_code})"
            return None, error_msg
            
    except Exception as e:
        return None, f"Error fetching sorted orders: {str(e)}"

##### API actions - flask restx API autodoc #####

# api endpoint for market/
@market_ns.route('')
class MarketResource(Resource):
    @market_ns.doc(
        params={
            'coin': {'description': 'Cryptocurrency name for CoinGecko API', 'default': 'bitcoin'},
            'days': {'description': 'Time period for CoinGecko API', 'default': '30'},
        },
        responses={
            200: 'Success',
            500: 'Server Error'
        }
    )
    @market_ns.marshal_with(market_response, code=200)

    def get(self):
        """
        Retrieve combined market data from CoinGecko and OrderBook
        
        This endpoint fetches and combines market data from multiple sources:
        - Historical price and volume data from CoinGecko
        - Order book data from the OrderBook service (currently disabled)
        """
        coin = request.args.get("coin", "bitcoin")
        days = request.args.get("days", "30")
        
        errors = {}
        
        data_coin_gecko, error_coin_gecko = get_coingecko_data(coin, days)
        if error_coin_gecko:
            errors["coin_gecko"] = error_coin_gecko

    
        if errors:
            return {"errors": errors}, 500

        combined_market = {
            "coinGecko": data_coin_gecko
        }
        
        return combined_market

# api endpoint for market/exchangerate
@market_ns.route('/exchangerate')
class ExchangeRateResource(Resource):
    @market_ns.doc(
        params={
            'tokens': {'description': 'Comma-separated list of cryptocurrency tokens (e.g., BTC,ETH,XRP)', 'default': 'BTC,ETH,XRP'}
        },
        responses={
            200: 'Success',
            500: 'Server Error'
        }
    )
    
    @market_ns.marshal_with(exchange_rate_response, code=200)

    def get(self):
        """
        Retrieve current exchange rates for specified tokens against USDT
        
        This endpoint fetches current exchange rates from CoinGecko API for the requested tokens.
        Returns a dictionary with token symbols as keys and their USDT rates as values.
        """
        # get tokens from query params (string of tokens separated by commas)
        tokens_param = request.args.get("tokens", "BTC,ETH,XRP")
        
        # parse tokens
        try:
            tokens = [token.strip() for token in tokens_param.split(',') if token.strip()]
            if not tokens:
                return {"error": "No valid tokens provided"}, 400
        except Exception as e:
            return {"error": f"Invalid token format: {str(e)}"}, 400
        
        rates, error = get_exchange_rates(tokens)
        
        if error:
            return {"error": error}, 500
        
        return {"rates": rates} # return rates dict

# api endpoint for market/fiatrates
@market_ns.route('/fiatrates')
class FiatRatesResource(Resource):
    @market_ns.doc(
        responses={
            200: 'Success',
            500: 'Server Error'
        }
    )
    
    @market_ns.marshal_with(exchange_rate_api_response, code=200)

    def get(self):
        """
        Retrieve current exchange rates for fiat currencies
        
        This endpoint fetches current exchange rates from Exchange Rate API.
        Returns the base currency and conversion rates for various fiat currencies.
        """
        data, error = get_exchange_rate_api_data()
        
        if error:
            return {"error": error}, 500
        
        return data
    
# api endpoint for /orderbook/recentorders
@orderbook_ns.route('/recentorders')
class RecentOrdersResource(Resource):
    @orderbook_ns.doc(
        responses={
            200: 'Success',
            500: 'Server Error'
        }
    )
    @orderbook_ns.marshal_with(recent_orders_response, code=200)
    def get(self):
        """
        Retrieve 10 most recent orders from the OrderBook
        
        This endpoint fetches the 10 most recent orders from the OrderBook service,
        sorted by creation timestamp (newest first).
        """
        recent_orders, error = get_ten_recent_orders()
        
        if error:
            return {"error": error}, 500
        
        return {"orders": recent_orders}

# api endpoint for /orderbook/sortedorders
@orderbook_ns.route('/sortedorders')
class SortedOrdersResource(Resource):
    @orderbook_ns.doc(
        params={
            'token': {'description': 'Token identifier (e.g., BTC, ETH)', 'default': 'BTC'}
        },
        responses={
            200: 'Success',
            500: 'Server Error'
        }
    )
    @orderbook_ns.marshal_with(sorted_orders_response, code=200)
    def get(self):
        """
        Retrieve 5 most expensive buy orders and 5 cheapest sell orders for a specific token
        
        This endpoint fetches:
        - 5 most expensive buy orders (USDT to token)
        - 5 cheapest sell orders (token to USDT)
        """
        # get token from query parameters
        token = request.args.get("token", "BTC").lower()
        
        sorted_orders, error = get_sorted_orders(token)
        
        if error:
            return {"error": error}, 500

        return sorted_orders

if __name__ == "__main__":
    if not COINGECKO_API_KEY:
        print("Warning: No CoinGecko API key found. Set COINGECKO_API_KEY environment variable.")
    
    if not EXCHANGE_RATE_API_KEY:
        print("Warning: No Exchange Rate API key found. Set EXCHANGE_RATE_API_KEY environment variable.")
    
    app.run(host='0.0.0.0', port=5000, debug=True)