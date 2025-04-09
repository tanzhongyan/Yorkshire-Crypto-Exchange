import requests
import logging
import amqp_lib
import pika
import json

# logger
# Configure logging at the application startup
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG during testing
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# RabbitMQ
rabbit_host = "rabbitmq"
rabbit_port = 5672
exchange_name = "order_topic"
exchange_type = "topic"
queue_name = "new_orders"
routing_key = "order.executed"

connection = None 
channel = None

# Environment variables for microservice
# Environment variables for microservice URLs
# NOTE: Do not use localhost here as localhost refer to this container itself
CRYPTO_SERVICE_URL = "http://crypto-service:5000/api/v1/crypto"
ORDERBOOK_SERVICE_URL = "https://personal-qrtp80l4.outsystemscloud.com/OrderBook_API/rest/v1/"

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


##### Individual helper functions  #####
    
def determine_side(incoming_order):
    '''
    this helper function is meant to check if the incoming order is on the buy or sell side.
    this will help determine sorting needed in counterparty orders and give incoming order the best price
            args:
                    consumed incoming order
            returns:
                    side of consumed incoming order
    '''
    
    # understanding orders coming in
        # fromTokenId
            # what they want to give 
        # toTokenId
            # what they want to recieve 
    from_token_id = incoming_order.get('fromTokenId')
    to_token_id = incoming_order.get('toTokenId')
    
    # order book terminology
        # base
            # what we define as the you are buying or selling directly
        # quote
            # what the price of the base asset is
            
        # example (base/quote)
            # ETH/USDT
                # this sets the direction of buying and selling for our algo
    pair_raw = from_token_id + '/' + to_token_id 
    
    # processing orders coming in for order book
        # 1. defined base/quote to resolve if buy or sell
            # e.g. ETH/USDT
            
        # 2. see what the fromTokenId is 
            # if fromTokenId == base, then side = sell
            # if fromTokenId == quote, then side = buy 
    # this is to enforce the tokens allowed in the orderbook. single point to change if needed
    PAIR_LOGIC= {
        
            'btc/usdt': 'sell', # Sell btc to get usdt
            'usdt/btc': 'buy',  # Buy btc with usdt
            
            'eth/usdt': 'sell', # Sell eth to get usdt
            'usdt/eth': 'buy',  # Buy eth with usdt
            
            'xrp/usdt': 'sell',  # Sell xrp to get usdt
            'usdt/xrp': 'buy',   # Buy xrp with usdt
            
            'bnb/usdt': 'sell',  # Sell bnb to get usdt
            'usdt/bnb': 'buy',   # Buy bnb with usdt
            
            'ada/usdt': 'sell',  # Sell ada to get usdt
            'usdt/ada': 'buy',   # Buy ada with usdt
            
            'sol/usdt': 'sell',  # Sell sol to get usdt
            'usdt/sol': 'buy',   # Buy sol with usdt
            
            'doge/usdt': 'sell',  # Sell doge to get usdt
            'usdt/doge': 'buy',   # Buy doge with usdt
            
            'dot/usdt': 'sell',  # Sell dot to get usdt
            'usdt/dot': 'buy',   # Buy dot with usdt
            
            'matic/usdt': 'sell',  # Sell matic to get usdt
            'usdt/matic': 'buy',   # Buy matic with usdt
            
            'ltc/usdt': 'sell',  # Sell ltc to get usdt
            'usdt/ltc': 'buy',   # Buy ltc with usdt
            
            'link/usdt': 'sell',  # Sell link to get usdt
            'usdt/link': 'buy',   # Buy link with usdt
            
            'avax/usdt': 'sell',  # Sell avax to get usdt
            'usdt/avax': 'buy',   # Buy avax with usdt

        }
    side = PAIR_LOGIC[pair_raw]
    return side

def get_counterparty_orders(incoming_order, incoming_side):
    '''
    this helper function is meant to retrive the counterparty orders needed to fulfill consumed incoming order
            args:
                    consumed incoming order and its side
            returns:
                    call success status, liquidity, list of counterparty orders, message for errors
    '''
    
    counterparty_orders_success = False
    from_token_id = incoming_order.get('fromTokenId')
    to_token_id = incoming_order.get('toTokenId')
    
    try:
        # retrive the opposite side of the incoming_order AKA counterparty orders. NOTE: swap the from and to token ids for get query
        print(f"Retrieving Counterparty Order details for fromTokenId: {to_token_id} and toTokenId: {from_token_id}")
        counterparty_orders_response = requests.get(f"{ORDERBOOK_SERVICE_URL}/GetOrdersByToken?fromTokenId={to_token_id}&toTokenId={from_token_id}")
        
        # load data
        counterparty_orders_details = counterparty_orders_response.json()
        
        # get the standard response fields that is always recieved
        result = counterparty_orders_details.get('result', {})
        liquidity = result.get('success', False)
        counterparty_orders_error_message = result.get('errorMessage')
        counterparty_orders_success = True
        
        # determine if any counterparty orders returned (sucsessful call still)
        if liquidity:
            counterparty_orders = counterparty_orders_details.get('orders', [])
            
            # sort according to matching order book logic/algo.
            if incoming_side == 'buy':
                # Sort the sell orders by ascending price (lowest price first). Favor incoming buy order to get lowest price
                counterparty_orders.sort(key=lambda x: x['limitPrice'])
            elif incoming_side == 'sell':
                # Sort the buy orders by descending price (highest price first). Favor incoming sell order to get highest price
                counterparty_orders.sort(key=lambda x: x['limitPrice'], reverse=True)
            return counterparty_orders_success, liquidity, counterparty_orders, counterparty_orders_error_message
        
        else:
            counterparty_orders = []
            return counterparty_orders_success, liquidity, counterparty_orders, counterparty_orders_error_message
    
    # error handle bad request and terminate
    except requests.RequestException as e:
        counterparty_orders = []
        counterparty_orders_error_message = 'Failed to add order in Yokshire Crypto Exchange order book. Report error to exchange admins (Subject: failed getting counterparty orders).'
        liquidity = False
        return counterparty_orders_success, liquidity, counterparty_orders, counterparty_orders_error_message

def add_to_order_book(incoming_order):
    '''
    this helper function is meant to add partial fulfilled or non-fulfilled orders to orderbook for future processing
            args:
                    incoming order (latest version when this function is invoked)
            returns:
                    response success status, error message
    '''
    add_to_orderbook_success = False
    
    try:
        payload = incoming_order
        print(f"Adding order to order book for transaction_id: {incoming_order['transactionId']}")
        add_to_orderbook_response = requests.post(f"{ORDERBOOK_SERVICE_URL}/AddOrder", json=payload)
        add_to_orderbook_details = add_to_orderbook_response.json() 
        add_to_orderbook_success = add_to_orderbook_details.get('success')
        add_to_orderbook_error_message = add_to_orderbook_details.get('errorMessage')
        return add_to_orderbook_success , add_to_orderbook_error_message
        

    except requests.RequestException as e:
        add_to_orderbook_error_message = 'Failed to add order in Yokshire Crypto Exchange order book. Report error to exchange admins. (Subject: failed adding order to orderbook)'
        return add_to_orderbook_success , add_to_orderbook_error_message

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
                'service_response': {
                    'status_code': response.status_code,
                    'text': response.text
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
                'service_response': {
                    'status_code': response.status_code,
                    'text': response.text,
                    'request_payload': payload
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
                'service_response': {
                    'status_code': response.status_code,
                    'text': response.text,
                    'request_payload': payload
                }
            }
    except requests.exceptions.RequestException as e:
        return {'error': 'Network error', 'message': str(e)}
    
def release_crypto(user_id, token_id, amount):
    """
    release crypto so in available amount. This allows the user to use released amount again.
    
    Args:
        user_id (str): The user ID
        token_id (str): The token ID
        amount (float): Amount to release
        
    Returns:
        dict: Response from the API or error details
    """
    try:
        payload = {
            "userId": user_id,
            "tokenId": token_id,
            "amountChanged": amount
        }
        response = requests.post(f"{CRYPTO_SERVICE_URL}/holdings/release", json=payload)
        if response.status_code == 200:
            return {'message': 'Crypto release successful'}
        else:
            return {
                'error': 'Failed to release crypto', 
                'message': response.text,
                'service_response': {
                    'status_code': response.status_code,
                    'text': response.text,
                    'request_payload': payload
                }
            }
    except requests.exceptions.RequestException as e:
        return {'error': 'Network error', 'message': str(e)}

def update_to_crypto(user_id, to_token_id, amount_changed):
    '''
    this helper function is meant to deposit crypto holdings within a person's wallet (by depositing or creating a holding)
            args:
                    user_id, to_token_id, amount_changed
            returns:
                    Response from the API or error details
    '''
    
        # Check if user already has a holding for the token
    crypto_holding = check_crypto_holding(user_id, to_token_id)
    
    # Add to amount actual to user's crypto holding
    if crypto_holding and 'error' not in crypto_holding:
        # User already has a holding, deposit to it
        deposit_result = deposit_crypto(user_id, to_token_id, amount_changed)
        return deposit_result
    else:
        # User doesn't have a holding, create one (will update amount while creating)
        holding_result = create_crypto_holding(user_id, to_token_id, amount_changed)
        return holding_result
        
def rollback_to_crypto(user_id, to_token_id, amount_changed):
    '''
    this helper function is meant to withdraw back crypto holdings within a person's wallet 
            args:
                    user_id, to_token_id, amount_changed
            returns:
                    Response from the API or error details
    '''
    try:
        payload = {
            "userId": user_id,
            "tokenId": to_token_id,
            "amountChanged": amount_changed
        }
        response = requests.post(f"{CRYPTO_SERVICE_URL}/holdings/withdraw", json=payload)
        if response.status_code == 200:
            return {'message': 'Crypto withdrawn and rollbacked successful'}
        else:
            return {
                'error': 'Failed to withdraw and rollback crypto', 
                'message': response.text,
                'service_response': {
                    'status_code': response.status_code,
                    'text': response.text,
                    'request_payload': payload
                }
            }
    except requests.exceptions.RequestException as e:
        return {'error': 'Network error', 'message': str(e)}
    

def update_from_crypto(user_id, from_token_id, amount_changed):
    """
    Deposit crypto into a user's holding.
    Increases both actual and available balance.
    
    Args:
        user_id (str): The user ID
        from_token_id (str): The token ID
        amount_changed (float): Amount to deposit
        
    Returns:
        dict: Response from the API or error details
    """
    try:
        payload = {
            "userId": user_id,
            "tokenId": from_token_id,
            "amountChanged": amount_changed
        }
        response = requests.post(f"{CRYPTO_SERVICE_URL}/holdings/execute", json=payload)
        if response.status_code == 200:
            return {'message': 'Crypto deducted successfully'}
        else:
            return {
                'error': 'Failed to deduct crypto', 
                'message': response.text,
                'service_response': {
                    'status_code': response.status_code,
                    'text': response.text,
                    'request_payload': payload
                }
            }
    except requests.exceptions.RequestException as e:
        return {'error': 'Network error', 'message': str(e)}

def rollback_from_crypto(user_id, from_token_id, amount_changed):
    '''
    this helper function is meant to withdraw back crypto holdings within a person's wallet 
            args:
                    user_id, from_token_id, amount_changed
            returns:
                    Response from the API or error details
    '''
    try:
        payload = {
            "userId": user_id,
            "tokenId": from_token_id,
            "amountChanged": amount_changed
        }
        response = requests.post(f"{CRYPTO_SERVICE_URL}/holdings/withdraw", json=payload)
        if response.status_code == 200:
            return {'message': 'Crypto added back and rollbacked successful'}
        else:
            return {
                'error': 'Failed to add back and rollback crypto', 
                'message': response.text,
                'service_response': {
                    'status_code': response.status_code,
                    'text': response.text,
                    'request_payload': payload
                }
            }
    except requests.exceptions.RequestException as e:
        return {'error': 'Network error', 'message': str(e)}
    
def update_order_in_orderbook(transaction_id, from_amount_left):
    '''
    this helper function is meant to update partial fulfilled orders in orderbook for future processing
            args:
                    transaction_id, from_amount_left
            returns:
    '''
    
    try:
        payload = {"fromAmount": float(from_amount_left)}
        print(f"Adding updating order in order book for transaction_id: {transaction_id} and from_amount: {from_amount_left}")
        update_amount_response = requests.patch(f"{ORDERBOOK_SERVICE_URL}/UpdateOrderQuantity/{transaction_id}/", json=payload)
        update_amount_response = update_amount_response.json() 
        return update_amount_response
        

    except requests.RequestException as e:
        return {
            'success' : False,
            'errorMessage' : f'Failed to updated fromAmount for transaction_id: {transaction_id} and from_amount: {from_amount_left}'
        }

def delete_order_in_orderbook(transaction_id):
    '''
    this helper function is meant to update partial fulfilled orders in orderbook for future processing
            args:
                    transaction_id
            returns:
                    response from API
    '''
    
    try:
        print(f"Adding deleting order in order book for transaction_id: {transaction_id}")
        delete_response = requests.delete(f"{ORDERBOOK_SERVICE_URL}/DeleteOrder/{transaction_id}/")
        delete_response = delete_response.json() 
        return delete_response
        

    except requests.RequestException as e:
        return {
            'success' : False,
            'errorMessage' : f'Failed to updated fromAmount for transaction_id: {transaction_id}'
        }


def match_incoming_buy(incoming_order, counterparty_orders):
    
    # initialise and used to determined if not fulfilled after running algo
    fulfilled_incoming_req = False
    fail_incoming_req = True
    
    # intialise for readability
    buy = incoming_order.copy()
    buy['fromAmount'] = float(str(buy['fromAmount']))
    if buy['orderType'] == 'limit':
        buy['limitPrice'] = float(str(buy['limitPrice']))
    
    sell_orders = []
    for sell in counterparty_orders:
        sell_copy = sell.copy()
        sell_copy['fromAmount'] = float(str(sell['fromAmount']))
        sell_copy['limitPrice'] = float(str(sell['limitPrice']))
        sell_orders.append(sell_copy)
    
    # to keep track and use for updating crypto
    base_crypto_id = buy.get('toTokenId')
    quote_crypto_id = buy.get('fromTokenId')

    # gp through all sell orders and see if can fulfill incoming buy order
    for sell in sell_orders:
        
        can_match = False
        # limit price fulfillment check. The sell price should be lower or equal to limit price for buy tolerance.
        if buy.get('orderType') == 'limit' and sell.get('limitPrice') <= buy.get('limitPrice') and sell.get('userId') != buy.get('userId'):
            # favour buyer in this case since requester
            price_executed = min(buy.get('limitPrice'), sell.get('limitPrice'))
            can_match = True
            
        # if market will always execute for whatever best price
        elif buy.get('orderType') == 'market':
            price_executed = sell.get('limitPrice')
            can_match = True
        
        logger.error(f"matching is {can_match}-----------------------------------------------------------------------------")
        if can_match:
            # bring to common quote crypto Id to compare and see which can be maximally fulfilled. Recall terminology used in determine_side function for quote (can refer to comments).
            # to answer
                    # enough token for exact match?
                    # enough token for total sell but leftover buy?
                    # enough token for total buy but leftover sell?
            sell_qty = sell.get('fromAmount') * price_executed # converted to quote crypto id
            buy_qty = buy.get('fromAmount') # in quote crypto id
            qty_executed_in_quote_currency = min(sell_qty,buy_qty)
            
            # determine in terms of base and quote, what is being traded/swapped
            base_qty_traded = qty_executed_in_quote_currency / price_executed
            quote_qty_traded = qty_executed_in_quote_currency
            
            # crypto to be updated here first since we dont want to update order without making sure wallet updated
            # step 1: minus from buy order userId 
            updated_all_services = False
            execute_buy_result = update_from_crypto(buy['userId'], buy['fromTokenId'], float(quote_qty_traded))
            
            # if step 1 fail: nothing to rollback, updated_all_services is False. stops here and exits this nested if 
            if 'error' in execute_buy_result:
                logger.error(f"error in step 1-----------------------------------------------------------------------------")
            # if step 1 success: 
                # step 2:minus from sell order userId 
            if 'error' not in execute_buy_result:
                execute_sell_result = update_from_crypto(sell['userId'], sell['fromTokenId'], float(base_qty_traded))
                
                # if step 2 fail: rollback step1, updated_all_services is False. stops here and exits this nested if 
                if 'error' in execute_sell_result:
                    logger.error(f"error in step 2-----------------------------------------------------------------------------")
                    rollback_execute_buy_result = rollback_from_crypto(buy['userId'], buy['fromTokenId'], float(quote_qty_traded))
                # if step 2 success: 
                    # step 3:add to buy order userId 
                else:
                    deposit_buy_result = update_to_crypto(buy['userId'], buy['toTokenId'], float(base_qty_traded))
                    
                    # if step 3 fail: rollback step1 and step2, updated_all_services is False. stops here and exits this nested if 
                    if 'error' in deposit_buy_result:
                        logger.error(f"error in step 3-----------------------------------------------------------------------------")
                        rollback_execute_buy_result = rollback_from_crypto(buy['userId'], buy['fromTokenId'], float(quote_qty_traded))
                        rollback_execute_sell_result = rollback_from_crypto(sell['userId'], sell['fromTokenId'], float(base_qty_traded))
                    # if step 3 success: 
                        # step 4:add to sell order userId 
                    else:
                        deposit_sell_result = update_to_crypto(sell['userId'], sell['toTokenId'], float(quote_qty_traded))

                        # if step 4 fail: rollback step1, step2 and step3, updated_all_services is False. stops here and exits this nested if
                        if 'error' in deposit_sell_result:
                            logger.error(f"error in step 4-----------------------------------------------------------------------------")
                            rollback_execute_buy_result = rollback_from_crypto(buy['userId'], buy['fromTokenId'], float(quote_qty_traded))
                            rollback_execute_sell_result = rollback_from_crypto(sell['userId'], sell['fromTokenId'], float(base_qty_traded))
                            rollback_deposit_buy_result = rollback_to_crypto(buy['userId'], buy['toTokenId'], float(base_qty_traded))
                        # if step 4 success: 
                            # step 5:send message and update orderbook (more details below), updated_all_services is now True
                        else:
                            
                            # amount added
                            buy_from_amount_actual = quote_qty_traded
                            sell_from_amount_actual = base_qty_traded
                            
                            # amount minus
                            buy_to_amount_actual = base_qty_traded
                            sell_to_amount_actual = quote_qty_traded
                            
                            # check amount left (used to determine status)
                            buy_from_amount_left = buy.get('fromAmount') - quote_qty_traded
                            sell_from_amount_left = sell.get('fromAmount') - base_qty_traded
                            
                            ZERO_THRESHOLD = float('0.000001')
                            # find status of orders
                            # adding of incoming buy order to order book to be done last after full iteration
                            buy['fromAmount'] = buy_from_amount_left
                            if buy_from_amount_left > ZERO_THRESHOLD:
                                buy_status = 'partially filled'
                            else:
                                buy_status = 'completed'
                                fulfilled_incoming_req = True
                                
                            if sell_from_amount_left > ZERO_THRESHOLD:
                                sell_status = 'partially filled'
                                update_book_response = update_order_in_orderbook(sell.get('transactionId'), sell_from_amount_left)
                            else:
                                sell_status = 'completed'
                                update_book_response = delete_order_in_orderbook(sell.get('transactionId'))
                                
                                
                            if not update_book_response.get('success'):
                                # rollback step 1,2,3,4, updated_all_services is False. stops here and exits this nested if
                                logger.error(f"error in step 5 aka update orderbook-----------------------------------------------------------------------------")
                                rollback_execute_buy_result = rollback_from_crypto(buy['userId'], buy['fromTokenId'], quote_qty_traded)
                                rollback_execute_sell_result = rollback_from_crypto(sell['userId'], sell['fromTokenId'], base_qty_traded)
                                rollback_deposit_buy_result = rollback_to_crypto(buy['userId'], buy['toTokenId'], base_qty_traded)
                                rollback_deposit_sell_result = rollback_to_crypto(sell['userId'], sell['toTokenId'], quote_qty_traded)
                                
                            else:
                                # all services updated properly
                                fail_incoming_req = False
                                updated_all_services = True 
                                
                                # description of execution
                                buy_description = f"{buy_from_amount_actual}{buy.get('fromTokenId')} was swapped for {buy_to_amount_actual}{buy.get('toTokenId')}"
                                sell_description = f"{sell_from_amount_actual}{sell.get('fromTokenId')} was swapped for {sell_to_amount_actual}{sell.get('toTokenId')}"

                                message_to_publish_buy = {
                                                'transactionId' : buy.get('transactionId'), 
                                                'userId' : buy.get('userId'),
                                                'status' : buy_status, 
                                                'fromAmountActual' : buy_from_amount_actual, 
                                                'toAmountActual' : buy_to_amount_actual, 
                                                'details' : buy_description
                                            }            
                                
                                message_to_publish_sell = {
                                                    'transactionId' : sell.get('transactionId'), 
                                                    'userId' : sell.get('userId'),
                                                    'status' : sell_status, 
                                                    'fromAmountActual' : sell_from_amount_actual, 
                                                    'toAmountActual' : sell_to_amount_actual, 
                                                    'details' : sell_description
                                                }            
                                if connection is None or not amqp_lib.is_connection_open(connection):
                                    connectAMQP()
                                    
                                
                    
                                json_message = json.dumps(message_to_publish_buy)
                                channel.basic_publish(
                                    exchange=exchange_name,
                                    routing_key=routing_key,
                                    body=json_message,
                                    properties=pika.BasicProperties(delivery_mode=2),
                                    )
                                
                                json_message2 = json.dumps(message_to_publish_sell)
                                channel.basic_publish(
                                    exchange=exchange_name,
                                    routing_key=routing_key,
                                    body=json_message2,
                                    properties=pika.BasicProperties(delivery_mode=2),
                                    )
                                # if incoming order fulfilled and services updated and message published for executions, then break out of loop to check for orders
                                if fulfilled_incoming_req:
                                    break
            # if any of the steps 1,2,3,4 had failed, it will get caught here
            if not updated_all_services:
                # if any error, would have rollbacked and ignore that match first.
                # this is to simplify any error and let timeout take care of these bad orders
                # skip to next iter of sell_order
                continue
            
    # here is out of loop already. search is finished
    if not fulfilled_incoming_req and incoming_order.get('orderType') == 'limit':
        # if incoming order not fully updated, then add to order book for further processing
        add_to_orderbook_success , add_to_orderbook_error_message = add_to_order_book(buy) 
        description = add_to_orderbook_error_message
        # Note if failed to add at this point, check if 'Fail' or 'partially filled'. 
        # if 'partially filled', would have published message that can help update front end alrdy so its fine
        # if 'fail', need to publish message that can help update front end
        if not add_to_orderbook_success and fail_incoming_req:
            # current description will be add order to orderbook fail or duplicate order exist
            logger.error(f"Releasing crypto-----------------------------------------------------------------------------")
            release_result = release_crypto(incoming_order.get('userId'), incoming_order.get('fromTokenId'), incoming_order.get('fromAmount'))
            if 'error' in release_result:
                logger.error(f"failed to release crypto-----------------------------------------------------------------------------")
                description = description +  f"Failed to release {incoming_order.get('fromAmount')} {incoming_order.get('fromTokenId')}. Contact admins."
            message_to_publish =  {
                                                'transactionId' : incoming_order.get('transactionId'), 
                                                'userId' : incoming_order.get('userId'),
                                                'status' : 'cancelled', 
                                                'fromAmountActual' : 0, 
                                                'toAmountActual' : 0, 
                                                'details' : description
                                            }
            if connection is None or not amqp_lib.is_connection_open(connection):
                connectAMQP()
            json_message = json.dumps(message_to_publish)
            channel.basic_publish(
                exchange=exchange_name,
                routing_key=routing_key,
                body=json_message,
                properties=pika.BasicProperties(delivery_mode=2),
                )
    # failed market
    elif not fulfilled_incoming_req and incoming_order.get('orderType') == 'market' and fail_incoming_req:
        description = "Failed to process order in Yokshire Crypto Exchange order book. Market currently has no matching orders. Please try again Later"
        logger.error(f"Releasing crypto-----------------------------------------------------------------------------")
        release_result = release_crypto(incoming_order.get('userId'), incoming_order.get('fromTokenId'), incoming_order.get('fromAmount'))
        if 'error' in release_result:
            logger.error(f"failed to release crypto-----------------------------------------------------------------------------")
            description = description +  f"Failed to release {incoming_order.get('fromAmount')} {incoming_order.get('fromTokenId')}. Contact admins."
        message_to_publish =  {
                                                'transactionId' : incoming_order.get('transactionId'), 
                                                'userId' : incoming_order.get('userId'),
                                                'status' : 'cancelled', 
                                                'fromAmountActual' : 0, 
                                                'toAmountActual' : 0, 
                                                'details' : description
                                            }
        if connection is None or not amqp_lib.is_connection_open(connection):
            connectAMQP()
            
        json_message = json.dumps(message_to_publish)
        channel.basic_publish(
            exchange=exchange_name,
            routing_key=routing_key,
            body=json_message,
            properties=pika.BasicProperties(delivery_mode=2),
            )
    
    # partial market
    elif not fulfilled_incoming_req and incoming_order.get('orderType') == 'market' and not fail_incoming_req:
        logger.error(f"Releasing crypto-----------------------------------------------------------------------------")
        release_result = release_crypto(incoming_order.get('userId'), incoming_order.get('fromTokenId'), buy.get('fromAmount')) #not amount to release is only hte amount left over
        # only update again if release fail so that notification sent to user. status is still partially filled
        if 'error' in release_result:
            logger.error(f"failed to release crypto-----------------------------------------------------------------------------")
            description = f"Failed to release {incoming_order.get('fromAmount')} {buy.get('fromAmount')}. Contact admins."
            message_to_publish =  {
                                                    'transactionId' : incoming_order.get('transactionId'), 
                                                    'userId' : incoming_order.get('userId'),
                                                    'status' : 'partially filled', 
                                                    'fromAmountActual' : 0, 
                                                    'toAmountActual' : 0, 
                                                    'details' : description
                                                }
            if connection is None or not amqp_lib.is_connection_open(connection):
                connectAMQP()

            json_message = json.dumps(message_to_publish)
            channel.basic_publish(
                exchange=exchange_name,
                routing_key=routing_key,
                body=json_message,
                properties=pika.BasicProperties(delivery_mode=2),
                )

def match_incoming_sell(incoming_order, counterparty_orders):
    
    # initialise and used to determined if not fulfilled after running algo
    fulfilled_incoming_req = False
    fail_incoming_req = True
    
    # intialise for readability
    sell = incoming_order.copy()
    sell['fromAmount'] = float(str(sell['fromAmount']))
    if sell['orderType'] == 'limit':
        sell['limitPrice'] = float(str(sell['limitPrice']))
    
    buy_orders = []
    for buy in counterparty_orders:
        buy_copy = buy.copy()
        buy_copy['fromAmount'] = float(str(buy['fromAmount']))
        buy_copy['limitPrice'] = float(str(buy['limitPrice']))
        buy_orders.append(buy_copy)
    
    # to keep track and use for updating crypto
    base_crypto_id = sell.get('fromTokenId')
    quote_crypto_id = sell.get('toTokenId')

    # gp through all sell orders and see if can fulfill incoming buy order
    for buy in buy_orders:
        
        can_match = False
        # limit price fulfillment check. The buy price should be higher or equal to limit price for sell tolerance.
        if sell.get('orderType') == 'limit' and buy.get('limitPrice') >= sell.get('limitPrice') and sell.get('userId') != buy.get('userId'):
            
            # favour seller in this case since requester
            price_executed = max(buy.get('limitPrice'), sell.get('limitPrice'))
            can_match = True
            
        # if market will always execute for whatever best price
        elif sell.get('orderType') == 'market':
            price_executed = buy.get('limitPrice')
            can_match = True
        
        logger.error(f"matching is {can_match}-----------------------------------------------------------------------------")
        if can_match:
            # bring to common quote crypto Id to compare and see which can be maximally fulfilled. Recall terminology used in determine_side function for quote (can refer to comments).
            # to answer
                    # enough token for exact match?
                    # enough token for total sell but leftover buy?
                    # enough token for total buy but leftover sell?
            sell_qty = sell.get('fromAmount') * price_executed # converted to quote crypto id
            buy_qty = buy.get('fromAmount') # in quote crypto id
            qty_executed_in_quote_currency = min(sell_qty,buy_qty)
            
            # determine in terms of base and quote, what is being traded/swapped
            base_qty_traded = qty_executed_in_quote_currency / price_executed
            quote_qty_traded = qty_executed_in_quote_currency
            
            # crypto to be updated here first since we dont want to update order without making sure wallet updated
            # step 1: minus from buy order userId 
            updated_all_services = False
            execute_buy_result = update_from_crypto(buy['userId'], buy['fromTokenId'], float(quote_qty_traded))
            
            # if step 1 fail: nothing to rollback, updated_all_services is False. stops here and exits this nested if 
            if 'error' in execute_buy_result:
                logger.error(f"error in step 1-----------------------------------------------------------------------------")
            # if step 1 success: 
                # step 2:minus from sell order userId 
            if 'error' not in execute_buy_result:
                execute_sell_result = update_from_crypto(sell['userId'], sell['fromTokenId'], float(base_qty_traded))
                
                # if step 2 fail: rollback step1, updated_all_services is False. stops here and exits this nested if 
                if 'error' in execute_sell_result:
                    logger.error(f"error in step 2-----------------------------------------------------------------------------")
                    rollback_execute_buy_result = rollback_from_crypto(buy['userId'], buy['fromTokenId'], float(quote_qty_traded))
                # if step 2 success: 
                    # step 3:add to buy order userId 
                else:
                    deposit_buy_result = update_to_crypto(buy['userId'], buy['toTokenId'], float(base_qty_traded))
                    
                    # if step 3 fail: rollback step1 and step2, updated_all_services is False. stops here and exits this nested if 
                    if 'error' in deposit_buy_result:
                        logger.error(f"error in step 3-----------------------------------------------------------------------------")
                        rollback_execute_buy_result = rollback_from_crypto(buy['userId'], buy['fromTokenId'], float(quote_qty_traded))
                        rollback_execute_sell_result = rollback_from_crypto(sell['userId'], sell['fromTokenId'], float(base_qty_traded))
                    # if step 3 success: 
                        # step 4:add to sell order userId 
                    else:
                        deposit_sell_result = update_to_crypto(sell['userId'], sell['toTokenId'], float(quote_qty_traded))

                        # if step 4 fail: rollback step1, step2 and step3, updated_all_services is False. stops here and exits this nested if
                        if 'error' in deposit_sell_result:
                            logger.error(f"error in step 4-----------------------------------------------------------------------------")
                            rollback_execute_buy_result = rollback_from_crypto(buy['userId'], buy['fromTokenId'], float(quote_qty_traded))
                            rollback_execute_sell_result = rollback_from_crypto(sell['userId'], sell['fromTokenId'], float(base_qty_traded))
                            rollback_deposit_buy_result = rollback_to_crypto(buy['userId'], buy['toTokenId'], float(base_qty_traded))
                        # if step 4 success: 
                            # step 5:send message and update orderbook (more details below), updated_all_services is now True
                        else:
                            
                            # amount added
                            buy_from_amount_actual = quote_qty_traded
                            sell_from_amount_actual = base_qty_traded
                            
                            # amount minus
                            buy_to_amount_actual = base_qty_traded
                            sell_to_amount_actual = quote_qty_traded
                            
                            # check amount left (used to determine status)
                            buy_from_amount_left = buy.get('fromAmount') - quote_qty_traded
                            sell_from_amount_left = sell.get('fromAmount') - base_qty_traded
                            
                            ZERO_THRESHOLD = float('0.000001')
                            # find status of orders
                            # adding of incoming buy order to order book to be done last after full iteration
                            sell['fromAmount'] = sell_from_amount_left
                            incoming_order['fromAmount'] = sell_from_amount_left
                            
                            if sell_from_amount_left > ZERO_THRESHOLD:
                                sell_status = 'partially filled'
                            else:
                                sell_status = 'completed'
                                fulfilled_incoming_req = True
                                
                            if buy_from_amount_left > ZERO_THRESHOLD:
                                buy_status = 'partially filled'
                                update_book_response = update_order_in_orderbook(buy.get('transactionId'), buy_from_amount_left)
                                
                            else:
                                buy_status = 'completed'
                                update_book_response = delete_order_in_orderbook(buy.get('transactionId'))
                                
                            if not update_book_response.get('success'):
                                logger.error(f"error in step 5 aka update orderbook-----------------------------------------------------------------------------")
                                # rollback step 1,2,3,4, updated_all_services is False. stops here and exits this nested if
                                rollback_execute_buy_result = rollback_from_crypto(buy['userId'], buy['fromTokenId'], quote_qty_traded)
                                rollback_execute_sell_result = rollback_from_crypto(sell['userId'], sell['fromTokenId'], base_qty_traded)
                                rollback_deposit_buy_result = rollback_to_crypto(buy['userId'], buy['toTokenId'], base_qty_traded)
                                rollback_deposit_sell_result = rollback_to_crypto(sell['userId'], sell['toTokenId'], quote_qty_traded)
                                
                            else:
                                # all services updated properly
                                fail_incoming_req = False
                                updated_all_services = True 

                                buy_description = f"{buy_from_amount_actual}{buy.get('fromTokenId')} was swapped for {buy_to_amount_actual}{buy.get('toTokenId')}"
                                sell_description = f"{sell_from_amount_actual}{sell.get('fromTokenId')} was swapped for {sell_to_amount_actual}{sell.get('toTokenId')}"
                                message_to_publish_buy = {
                                                'transactionId' : buy.get('transactionId'), 
                                                'userId' : buy.get('userId'),
                                                'status' : buy_status, 
                                                'fromAmountActual' : buy_from_amount_actual, 
                                                'toAmountActual' : buy_to_amount_actual, 
                                                'details' : buy_description
                                            }            
                                
                                message_to_publish_sell = {
                                                    'transactionId' : sell.get('transactionId'), 
                                                    'userId' : sell.get('userId'),
                                                    'status' : sell_status, 
                                                    'fromAmountActual' : sell_from_amount_actual, 
                                                    'toAmountActual' : sell_to_amount_actual, 
                                                    'details' : sell_description
                                                }            
                                if connection is None or not amqp_lib.is_connection_open(connection):
                                    connectAMQP()
                    
                                json_message = json.dumps(message_to_publish_buy)
                                channel.basic_publish(
                                    exchange=exchange_name,
                                    routing_key=routing_key,
                                    body=json_message,
                                    properties=pika.BasicProperties(delivery_mode=2),
                                    )
                                
                                json_message2 = json.dumps(message_to_publish_sell)
                                channel.basic_publish(
                                    exchange=exchange_name,
                                    routing_key=routing_key,
                                    body=json_message2,
                                    properties=pika.BasicProperties(delivery_mode=2),
                                    )
                                # if incoming order fulfilled and services updated and message published for executions, then break out of loop to check for orders
                                if fulfilled_incoming_req:
                                    break
            # if any of the steps 1,2,3,4 had failed, it will get caught here
            if not updated_all_services:
                # if any error, would have rollbacked and ignore that match first.
                # this is to simplify any error and let timeout take care of these bad orders
                # skip to next iter of sell_order
                continue
    
    # here is out of loop already. search is finished
    if not fulfilled_incoming_req and incoming_order.get('orderType') == 'limit':
        # if incoming order not fully updated, then add to order book for further processing
        add_to_orderbook_success , add_to_orderbook_error_message = add_to_order_book(sell) 
        description = add_to_orderbook_error_message
        # Note if failed to add at this point, check if 'Fail' or 'partially filled'. 
        # if 'partially filled', would have published message that can help update front end alrdy so its fine
        # if 'fail', need to publish message that can help update front end
        if not add_to_orderbook_success and fail_incoming_req:
            # current description will be add order to orderbook fail or duplicate order exist
            logger.error(f"Releasing crypto-----------------------------------------------------------------------------")
            release_result = release_crypto(incoming_order.get('userId'), incoming_order.get('fromTokenId'), incoming_order.get('fromAmount'))
            if 'error' in release_result:
                logger.error(f"failed to release crypto-----------------------------------------------------------------------------")
                description = description +  f"Failed to release {incoming_order.get('fromAmount')} {incoming_order.get('fromTokenId')}. Contact admins."
            message_to_publish = {
                                                'transactionId' : incoming_order.get('transactionId'),
                                                'userId' : incoming_order.get('userId'), 
                                                'status' : 'cancelled', 
                                                'fromAmountActual' : 0, 
                                                'toAmountActual' : 0, 
                                                'details' : description
                                            }
            if connection is None or not amqp_lib.is_connection_open(connection):
                connectAMQP()
            
            json_message = json.dumps(message_to_publish)
            channel.basic_publish(
                exchange=exchange_name,
                routing_key=routing_key,
                body=json_message,
                properties=pika.BasicProperties(delivery_mode=2),
                )
            
    elif not fulfilled_incoming_req and incoming_order.get('orderType') == 'market' and fail_incoming_req:
        description = "Failed to process order in Yokshire Crypto Exchange order book. Market currently has no matching orders. Please try again Later"
        logger.error(f"Releasing crypto-----------------------------------------------------------------------------")
        release_result = release_crypto(incoming_order.get('userId'), incoming_order.get('fromTokenId'), incoming_order.get('fromAmount'))
        if 'error' in release_result:
            logger.error(f"failed to release crypto-----------------------------------------------------------------------------")
            description = description +  f"Failed to release {incoming_order.get('fromAmount')} {incoming_order.get('fromTokenId')}. Contact admins."
        message_to_publish =  {
                                                'transactionId' : incoming_order.get('transactionId'), 
                                                'userId' : incoming_order.get('userId'),
                                                'status' : 'cancelled', 
                                                'fromAmountActual' : 0, 
                                                'toAmountActual' : 0, 
                                                'details' : description
                                            }
        if connection is None or not amqp_lib.is_connection_open(connection):
            connectAMQP()

        json_message = json.dumps(message_to_publish)
        channel.basic_publish(
            exchange=exchange_name,
            routing_key=routing_key,
            body=json_message,
            properties=pika.BasicProperties(delivery_mode=2),
            )
        
        # partial market
    elif not fulfilled_incoming_req and incoming_order.get('orderType') == 'market' and not fail_incoming_req:
        logger.error(f"Releasing crypto-----------------------------------------------------------------------------")
        release_result = release_crypto(incoming_order.get('userId'), incoming_order.get('fromTokenId'), sell.get('fromAmount')) #not amount to release is only hte amount left over
        # only update again if release fail so that notification sent to user. status is still partially filled
        if 'error' in release_result:
            logger.error(f"failed to release crypto-----------------------------------------------------------------------------")
            description = f"Failed to release {incoming_order.get('fromAmount')} {sell.get('fromAmount')}. Contact admins."
            message_to_publish =  {
                                                    'transactionId' : incoming_order.get('transactionId'), 
                                                    'userId' : incoming_order.get('userId'),
                                                    'status' : 'partially filled', 
                                                    'fromAmountActual' : 0, 
                                                    'toAmountActual' : 0, 
                                                    'details' : description
                                                }
            if connection is None or not amqp_lib.is_connection_open(connection):
                connectAMQP()

            json_message = json.dumps(message_to_publish)
            channel.basic_publish(
                exchange=exchange_name,
                routing_key=routing_key,
                body=json_message,
                properties=pika.BasicProperties(delivery_mode=2),
                )



def callback(channel, method, properties, body):
    # required signature for the callback; no return
    try:
        incoming_order = json.loads(body)
        print(f"Order recieved (JSON): {incoming_order}")
        
        # determine side for matching algo sort
        incoming_side = determine_side(incoming_order)
        order_type = incoming_order.get('orderType')
        
        # get counterparty orders to fulfill incoming order
        counterparty_orders_success, liquidity, counterparty_orders, counterparty_orders_error_message = get_counterparty_orders(incoming_order, incoming_side)
        
        # in the case that no counterparty order able to be obtained
        if not counterparty_orders_success or not liquidity:
            
            # initialise for any error message to show in UI
            # current description will be retrive counterparty fail or not liquid
            description = counterparty_orders_error_message
            # if limit, try add to order book for future processing
            if order_type == 'limit':
                # current description will be retrive counterparty fail or not liquid
                logger.error(f"adding order to orderbook instead. not liquied/retrive counterparty fail-----------------------------------------------------------------------------")
                add_to_orderbook_success , add_to_orderbook_error_message = add_to_order_book(incoming_order) 
                # if successfully added, then will end here. description = ''. will not go beyond here
                # if fail, current description will be add order to orderbook fail or duplicate order exist
                description = add_to_orderbook_error_message
                if add_to_orderbook_success:
                    channel.basic_ack(delivery_tag=method.delivery_tag)
                # in the case that adding to orderbook failed 
                if not add_to_orderbook_success:
                    
                    # current description will be add order to orderbook fail or duplicate order exist
                    logger.error(f"failed adding to order book instead. changing status to fail and ending-----------------------------------------------------------------------------")
                    logger.error(f"Releasing crypto-----------------------------------------------------------------------------")
                    release_result = release_crypto(incoming_order.get('userId'), incoming_order.get('fromTokenId'), incoming_order.get('fromAmount'))
                    if 'error' in release_result:
                        logger.error(f"failed to release crypto-----------------------------------------------------------------------------")
                        description = description +  f"Failed to release {incoming_order.get('fromAmount')} {incoming_order.get('fromTokenId')}. Contact admins."
                    message_to_publish = {
                                                        'transactionId' : incoming_order.get('transactionId'),
                                                        'userId' : incoming_order.get('userId'),  
                                                        'status' : 'cancelled', 
                                                        'fromAmountActual' : 0, 
                                                        'toAmountActual' : 0, 
                                                        'details' : description
                                                    }
                    
                    if connection is None or not amqp_lib.is_connection_open(connection):
                        connectAMQP()
                    
                    json_message = json.dumps(message_to_publish)
                    channel.basic_publish(
                        exchange=exchange_name,
                        routing_key=routing_key,
                        body=json_message,
                        properties=pika.BasicProperties(delivery_mode=2),
                        )
                    channel.basic_ack(delivery_tag=method.delivery_tag)
                    
            else:
                # current description will be retrive counterparty fail or not liquid (for market order)
                logger.error(f"incoming market order but marke not liquid. changing status to fail and ending-----------------------------------------------------------------------------")
                logger.error(f"Releasing crypto-----------------------------------------------------------------------------")
                release_result = release_crypto(incoming_order.get('userId'), incoming_order.get('fromTokenId'), incoming_order.get('fromAmount'))
                if 'error' in release_result:
                    logger.error(f"failed to release crypto-----------------------------------------------------------------------------")
                    description = description +  f"Failed to release {incoming_order.get('fromAmount')} {incoming_order.get('fromTokenId')}. Contact admins."
                message_to_publish = {
                                                        'transactionId' : incoming_order.get('transactionId'),
                                                        'userId' : incoming_order.get('userId'), 
                                                        'status' : 'cancelled', 
                                                        'fromAmountActual' : 0, 
                                                        'toAmountActual' : 0, 
                                                        'details' : description
                                                    }
                    # for publishing
                if connection is None or not amqp_lib.is_connection_open(connection):
                    connectAMQP()
                    
                json_message = json.dumps(message_to_publish)

                channel.basic_publish(
                    exchange=exchange_name,
                    routing_key=routing_key,
                    body=json_message,
                    properties=pika.BasicProperties(delivery_mode=2),
                    )
                channel.basic_ack(delivery_tag=method.delivery_tag)
                
        
        # counterparty order was able to be obtained. now ready for processsing.
        else:
            if incoming_side == 'buy':
                logger.error(f"starting matching of incoming buy-----------------------------------------------------------------------------")
                match_incoming_buy(incoming_order, counterparty_orders)
                channel.basic_ack(delivery_tag=method.delivery_tag)
            elif incoming_side == 'sell':
                logger.error(f"starting matching of incoming sell-----------------------------------------------------------------------------")
                match_incoming_sell(incoming_order, counterparty_orders)
                channel.basic_ack(delivery_tag=method.delivery_tag)
            
    except Exception as e:
        logger.error(f"Unable to parse JSON: {e=}")
        logger.error(f"Error message: {body}")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

if __name__ == '__main__':
    print('Match composite service - amqp consumer and publisher...')
    connectAMQP()

    try:
        amqp_lib.start_consuming(
            rabbit_host, rabbit_port, exchange_name, exchange_type, queue_name, callback
        )
    except Exception as exception:
        print(f"  Unable to connect to RabbitMQ.\n     {exception=}\n")
    