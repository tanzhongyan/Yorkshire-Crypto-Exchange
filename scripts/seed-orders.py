#!/usr/bin/env python3
"""
Seed script to create sell orders for all cryptocurrency pairs.
This script will:
1. Wait for services to be ready
2. Get current market prices from CoinGecko
3. Create sell orders for the test user for all supported crypto pairs
"""

import requests
import time
import sys
import os
from datetime import datetime

# Configuration - Direct service URLs (bypassing Kong for internal calls)
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user-service:5000")
INITIATE_SERVICE_URL = os.getenv("INITIATE_SERVICE_URL", "http://initiate-service:5000")
MARKET_SERVICE_URL = os.getenv("MARKET_SERVICE_URL", "http://market-service:5000")
TEST_USER_IDENTIFIER = "test"
TEST_USER_PASSWORD = "test12345"

# Supported crypto pairs (base/quote)
CRYPTO_PAIRS = [
    ("btc", "usdt"),
    ("eth", "usdt"),
    ("xrp", "usdt"),
    ("bnb", "usdt"),
    ("ada", "usdt"),
    ("sol", "usdt"),
    ("doge", "usdt"),
    ("dot", "usdt"),
    ("matic", "usdt"),
    ("ltc", "usdt"),
]

# Amount to seed for each crypto (base quantity per order) - MASSIVE amounts for showcase!
SEED_AMOUNTS = {
    "btc": 5000.0,        # 5000 BTC per order (~$435M per order!)
    "eth": 50000.0,       # 50k ETH per order (~$145M per order!)
    "xrp": 25000000.0,    # 25M XRP per order (~$46M per order!)
    "bnb": 25000.0,       # 25k BNB per order (~$21M per order!)
    "ada": 50000000.0,    # 50M ADA per order (~$18M per order!)
    "sol": 250000.0,      # 250k SOL per order (~$30M per order!)
    "doge": 250000000.0,  # 250M DOGE per order (~$32M per order!)
    "dot": 2500000.0,     # 2.5M DOT per order (~$4.3M per order!)
    "matic": 50000000.0,  # 50M MATIC per order (~$5.5M per order!)
    "ltc": 50000.0,       # 50k LTC per order (~$3.8M per order!)
}

# Price intervals for creating multiple orders at different price points
# Each crypto will have orders at: base_price, base_price + interval, base_price + 2*interval, etc.
PRICE_INTERVALS = {
    "btc": 1000.0,    # $1000 intervals for BTC
    "eth": 100.0,     # $100 intervals for ETH
    "xrp": 0.10,      # $0.10 intervals for XRP
    "bnb": 50.0,      # $50 intervals for BNB
    "ada": 0.05,      # $0.05 intervals for ADA
    "sol": 10.0,      # $10 intervals for SOL
    "doge": 0.01,     # $0.01 intervals for DOGE
    "dot": 0.50,      # $0.50 intervals for DOT
    "matic": 0.05,    # $0.05 intervals for MATIC
    "ltc": 10.0,      # $10 intervals for LTC
}

# Number of price levels to create orders at (above market price)
NUM_PRICE_LEVELS = 10

def wait_for_services(max_retries=30, delay=2):
    """Wait for backend services to be ready (direct calls, no Kong)."""
    print("Waiting for services to be ready...")
    
    # Initial delay to let services warm up after Docker starts them
    print("  Initial warmup period (15 seconds)...")
    time.sleep(15)
    
    services_to_check = [
        ("user-service", f"{USER_SERVICE_URL}/api/v1/user/account"),
        ("initiate-service", f"{INITIATE_SERVICE_URL}/api/v1/initiate"),
    ]
    
    for i in range(max_retries):
        all_ready = True
        for service_name, url in services_to_check:
            try:
                response = requests.get(url, timeout=2)
                # Any response (even 404 for missing resource) means service is up
                if response.status_code < 500:
                    continue
                all_ready = False
            except requests.exceptions.RequestException:
                all_ready = False
        
        if all_ready:
            print("✓ All services are ready!")
            return True
        
        if i < max_retries - 1:
            print(f"  Waiting... ({i+1}/{max_retries})")
            time.sleep(delay)
    
    print("✗ Services failed to start in time")
    return False

def login_test_user():
    """Login as test user and get JWT token and user ID."""
    print(f"Logging in as test user ({TEST_USER_IDENTIFIER})...")
    try:
        response = requests.post(
            f"{USER_SERVICE_URL}/api/v1/user/authenticate/login",
            json={
                "identifier": TEST_USER_IDENTIFIER,
                "password": TEST_USER_PASSWORD
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("token")
            user_id = data.get("userId")
            print("✓ Login successful!")
            return token, user_id
        else:
            print(f"✗ Login failed: {response.status_code} - {response.text}")
            return None, None
    except Exception as e:
        print(f"✗ Login error: {e}")
        return None, None

def get_current_prices():
    """Get current market prices from CoinGecko API."""
    print("Fetching current cryptocurrency prices from CoinGecko...")
    try:
        # Get prices directly from CoinGecko (polygon-ecosystem-token is POL, formerly MATIC)
        coins = "bitcoin,ethereum,ripple,binancecoin,cardano,solana,dogecoin,polkadot,polygon-ecosystem-token,litecoin"
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coins}&vs_currencies=usd"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # Map CoinGecko IDs to our token IDs
            price_map = {
                "btc": data.get("bitcoin", {}).get("usd"),
                "eth": data.get("ethereum", {}).get("usd"),
                "xrp": data.get("ripple", {}).get("usd"),
                "bnb": data.get("binancecoin", {}).get("usd"),
                "ada": data.get("cardano", {}).get("usd"),
                "sol": data.get("solana", {}).get("usd"),
                "doge": data.get("dogecoin", {}).get("usd"),
                "dot": data.get("polkadot", {}).get("usd"),
                "matic": data.get("polygon-ecosystem-token", {}).get("usd"),
                "ltc": data.get("litecoin", {}).get("usd"),
            }
            print("✓ Retrieved current market prices from CoinGecko")
            return price_map
        else:
            print(f"⚠ Could not fetch live prices (status {response.status_code}), using fallback prices")
            return get_fallback_prices()
    except Exception as e:
        print(f"⚠ Error fetching prices: {e}, using fallback prices")
        return get_fallback_prices()

def get_fallback_prices():
    """Fallback prices if CoinGecko is unavailable."""
    return {
        "btc": 95000.0,
        "eth": 3500.0,
        "xrp": 2.5,
        "bnb": 650.0,
        "ada": 1.2,
        "sol": 180.0,
        "doge": 0.35,
        "dot": 8.5,
        "matic": 1.1,
        "ltc": 110.0,
    }

def create_sell_order(token, user_id, base_token, quote_token, price, quantity, order_cost):
    """Create a sell order for the test user."""
    try:
        payload = {
            "userId": user_id,
            "orderType": "limit",
            "side": "sell",
            "baseTokenId": base_token,
            "quoteTokenId": quote_token,
            "limitPrice": price,
            "quantity": quantity,
            "orderCost": order_cost
        }
        
        response = requests.post(
            f"{INITIATE_SERVICE_URL}/api/v1/order/create_order",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            print(f"  ✓ Created sell order: {quantity} {base_token.upper()} @ ${price:.2f}")
            return True
        else:
            print(f"  ✗ Failed to create order for {base_token}: {response.status_code}")
            if response.content:
                print(f"     {response.text}")
            return False
    except Exception as e:
        print(f"  ✗ Error creating order for {base_token}: {e}")
        return False

def seed_sell_orders():
    """Main function to seed sell orders."""
    print("\n" + "="*60)
    print("Yorkshire Crypto Exchange - Order Seeding Script")
    print("="*60 + "\n")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Wait for services
    if not wait_for_services():
        print("\n✗ Failed to connect to services. Exiting.")
        sys.exit(1)
    
    # Login
    token, user_id = login_test_user()
    if not token or not user_id:
        print("\n✗ Failed to login. Exiting.")
        sys.exit(1)
    
    # Get current prices
    prices = get_current_prices()
    
    # Calculate total orders
    total_orders = len(CRYPTO_PAIRS) * NUM_PRICE_LEVELS
    print(f"\nCreating {total_orders} sell orders ({NUM_PRICE_LEVELS} price levels × {len(CRYPTO_PAIRS)} pairs)...")
    print("-" * 60)
    
    success_count = 0
    
    for base_token, quote_token in CRYPTO_PAIRS:
        quantity = SEED_AMOUNTS.get(base_token, 1.0)
        interval = PRICE_INTERVALS.get(base_token, 100.0)
        
        # Get base price in USD
        base_price = prices.get(base_token)
        if base_price is None:
            print(f"\n⚠ Price not found for {base_token.upper()}, skipping...")
            continue
        
        print(f"\n{base_token.upper()}/USDT - Base price: ${base_price:,.2f}, Interval: ${interval:,.2f}")
        
        # Create orders at multiple price levels
        for level in range(NUM_PRICE_LEVELS):
            price = base_price + (interval * level)
            order_cost = price * quantity
            
            if create_sell_order(token, user_id, base_token, quote_token, price, quantity, order_cost):
                success_count += 1
            
            # Small delay to avoid overwhelming the system
            time.sleep(0.2)
    
    print(f"\n{'='*60}")
    print(f"Seeding Complete!")
    print(f"Successfully created {success_count}/{total_orders} sell orders")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    if success_count >= total_orders * 0.9:  # Allow 90% success rate
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    seed_sell_orders()
