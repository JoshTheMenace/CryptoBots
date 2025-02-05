#!/usr/bin/env python3
"""
Trade with Winner Neural Network Bot

This script loads a pre-trained NEAT neural network (the winner) from a pickle file and uses it
to make trading decisions every minute via your trading API.

The neural network receives 5 normalized inputs:
    1. Normalized Price = current close / initial close
    2. Price Change = (current close - previous close) / previous close
    3. Normalized Volume = current volume / initial volume
    4. Normalized Trades = current trades / initial trades
    5. Position Flag = 1.0 if currently in a long position, 0.0 otherwise

The network outputs a decision:
    0 = Hold, 1 = Buy, 2 = Sell

Trading Logic:
    - If the decision is Buy and no position is open, send a buy order.
    - If the decision is Sell and a position is open, send a sell order.
    - Otherwise, do nothing.
    
Usage:
    python trade_with_winner.py <config_file> <winner_pickle_file>
"""

import sys
import time
import datetime
import requests
import pickle
import neat
import numpy as np

BOT_ID = "-OI0A-_UOfKmWX4FNW-h"         # Unique bot identifier
USER_ID = "6xDYg9OrqaRlkLecm4CFG2G1rq93"  # Your user id

# ------------------------------
# CONFIGURATION
# ------------------------------
# Adjust these API endpoints as needed.
TRADE_API_URL = f"https://crypto-bots-mu.vercel.app/api/bots/{BOT_ID}/trades"  # Replace <BOT_ID> with your bot's id.
MARKET_DATA_API_URL = "https://crypto-bots-mu.vercel.app/api/market-data"

# TRADE_API_URL = f"http://localhost:3000/api/bots/{BOT_ID}/trades"
# MARKET_DATA_API_URL = "http://localhost:3000/api/market-data"

# Trading parameters.
SYMBOL = "BTC"         # Trading symbol.
ORDER_TYPE = "market"  # Order type.
TRADE_AMOUNT = 0.01    # Trade amount.

# Evaluation interval (in seconds).
EVALUATION_INTERVAL = 60

# Global state.
in_position = False    # False means no open position; True means a long position is held.
entry_price = None     # Price at which the current position was entered.
baseline_close = None  # Set on first market data fetch.
baseline_volume = None
baseline_trades = None
previous_close = None  # For computing price change.

# ------------------------------
# FUNCTIONS
# ------------------------------
def fetch_market_data():
    """
    Fetches current market data from the market data API.
    Expects a JSON response like: {'BTC': 101729.81, 'ETH': 3232.82}.
    
    Returns a dictionary with keys "close", "volume", and "trades".
    Since volume and trades are not provided by this API, they are defaulted to 1.0.
    """
    try:
        response = requests.get(MARKET_DATA_API_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        price = data.get(SYMBOL)
        if price is None:
            print(f"[{datetime.datetime.now().isoformat()}] ⚠️ {SYMBOL} not found in market data.")
            return None
        # Default volume and trades to 1.0 since they are not provided.
        return {"close": float(price), "volume": 1.0, "trades": 1.0}
    except Exception as e:
        print(f"[{datetime.datetime.now().isoformat()}] ❌ Error fetching market data: {e}")
        return None

def send_trade_order(side, amount, price):
    """
    Sends a trade order to your trade API.
    The payload includes: side, amount, price, symbol, and orderType.
    """
    payload = {
        "side": side,
        "amount": amount,
        "price": price,
        "symbol": SYMBOL,
        "orderType": ORDER_TYPE,
        "userId": USER_ID
        # Add additional fields such as userId if required by your API.
    }
    try:
        response = requests.post(TRADE_API_URL, json=payload, timeout=5)
        response.raise_for_status()
        result = response.json()
        print(f"[{datetime.datetime.now().isoformat()}] ✅ Trade executed: {side} {amount} {SYMBOL} at ${price:.2f}")
        print("API Response:", result)
        return True
    except Exception as e:
        print(f"[{datetime.datetime.now().isoformat()}] ❌ Error sending trade order: {e}")
        return False

def main():
    global in_position, entry_price, baseline_close, baseline_volume, baseline_trades, previous_close

    if len(sys.argv) < 3:
        print("Usage: python trade_with_winner.py <config_file> <winner_pickle_file>")
        sys.exit(1)

    config_path = sys.argv[1]
    winner_path = sys.argv[2]

    # Load NEAT configuration.
    config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                         neat.DefaultSpeciesSet, neat.DefaultStagnation,
                         config_path)

    # Load the winner genome.
    with open(winner_path, "rb") as f:
        winner = pickle.load(f)

    # Create the neural network from the winner genome.
    net = neat.nn.FeedForwardNetwork.create(winner, config)

    print("🚀 Loaded winner network. Starting trading loop...")

    while True:
        market_data = fetch_market_data()
        if market_data is None:
            print(f"[{datetime.datetime.now().isoformat()}] ⚠️ Market data fetch failed. Skipping this interval.")
            time.sleep(EVALUATION_INTERVAL)
            continue

        current_close = market_data["close"]
        current_volume = market_data["volume"]
        current_trades = market_data["trades"]

        # Initialize baseline values on the first successful fetch.
        if baseline_close is None:
            baseline_close = current_close
            baseline_volume = current_volume if current_volume != 0 else 1.0
            baseline_trades = current_trades if current_trades != 0 else 1.0
            previous_close = current_close

        # Compute normalized inputs.
        norm_price = current_close / baseline_close
        price_change = (current_close - previous_close) / previous_close if previous_close != 0 else 0
        norm_volume = current_volume / baseline_volume if baseline_volume != 0 else 1.0
        norm_trades = current_trades / baseline_trades if baseline_trades != 0 else 1.0
        position_flag = 1.0 if in_position else 0.0

        inputs = [norm_price, price_change, norm_volume, norm_trades, position_flag]
        outputs = net.activate(inputs)
        decision = np.argmax(outputs)  # 0 = Hold, 1 = Buy, 2 = Sell

        now_str = datetime.datetime.now().isoformat()
        print(f"[{now_str}] Inputs: {inputs}")
        print(f"[{now_str}] Network outputs: {outputs} => Decision: {decision}")

        if decision == 1:  # Buy signal.
            if not in_position:
                if send_trade_order("buy", TRADE_AMOUNT, current_close):
                    in_position = True
                    entry_price = current_close
                    print(f"[{now_str}] Executed BUY at ${current_close:.2f}")
                else:
                    print(f"[{now_str}] BUY order failed.")
            else:
                print(f"[{now_str}] Already in position. BUY signal ignored.")
        elif decision == 2:  # Sell signal.
            if in_position:
                if send_trade_order("sell", TRADE_AMOUNT, current_close):
                    in_position = False
                    profit = current_close - entry_price
                    print(f"[{now_str}] Executed SELL at ${current_close:.2f}. Profit: ${profit:.2f}")
                    entry_price = None
                else:
                    print(f"[{now_str}] SELL order failed.")
            else:
                print(f"[{now_str}] Not in position. SELL signal ignored.")
        else:
            print(f"[{now_str}] Hold decision. No action taken.")

        previous_close = current_close
        time.sleep(EVALUATION_INTERVAL)

if __name__ == '__main__':
    main()