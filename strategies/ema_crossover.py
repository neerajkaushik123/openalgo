from openalgo import api
import requests
import pandas as pd
import numpy as np
import time
import threading
from datetime import datetime, timedelta
import traceback
import sys
import logging
import warnings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
# Get API key from openalgo portal
api_key = '92fbae88ad9c469aa53b96c4f1e0b2db3341c06bc6c80303092687fc78741abe'

# Set the strategy details and trading parameters
strategy = "EMA Crossover Python"
symbols = ["BHEL", "SBIN", "RELIANCE"]  # List of OpenAlgo Symbols
exchange = "NSE"
product = "MIS"
quantity = 1

# Global dictionary to track positions for each symbol
symbol_positions = {symbol: 0 for symbol in symbols}

# Global dictionary to track the last order timestamp for each symbol
last_order_time = {symbol: None for symbol in symbols}
order_interval_seconds = 60 * 5  # 5 minutes between orders

# EMA periods
fast_period = 5
slow_period = 10

# Set the API Key
client = api(api_key=api_key, host='https://804c-83-92-100-2.ngrok-free.app')

def calculate_ema_signals(df):
    """
    Calculate EMA crossover signals.
    """
    close = df['close']
    
    # Calculate EMAs
    ema_fast = close.ewm(span=fast_period, adjust=False).mean()
    ema_slow = close.ewm(span=slow_period, adjust=False).mean()
    
    # Create crossover signals
    crossover = pd.Series(False, index=df.index)
    crossunder = pd.Series(False, index=df.index)
    
    # Previous values of EMAs
    prev_fast = ema_fast.shift(1)
    prev_slow = ema_slow.shift(1)
    
    # Current values of EMAs
    curr_fast = ema_fast
    curr_slow = ema_slow
    
    # Generate crossover signals
    crossover = (prev_fast < prev_slow) & (curr_fast > curr_slow)
    crossunder = (prev_fast > prev_slow) & (curr_fast < curr_slow)
    
    return pd.DataFrame({
        'EMA_Fast': ema_fast,
        'EMA_Slow': ema_slow,
        'Crossover': crossover,
        'Crossunder': crossunder
    }, index=df.index)

def ema_strategy(symbol):
    """
    EMA crossover trading strategy for a single symbol.
    """
    while True:
        try:
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

            df = client.history(
                symbol=symbol,
                exchange=exchange,
                interval="1h",
                start_date=start_date,
                end_date=end_date
            )

            if df.empty:
                print(f"{symbol} - DataFrame is empty. Retrying...")
                time.sleep(15)
                continue

            if 'close' not in df.columns:
                raise KeyError("Missing 'close' column in DataFrame")

            df['close'] = df['close'].round(2)
            signals = calculate_ema_signals(df)
            crossover = signals['Crossover'].iloc[-2]
            crossunder = signals['Crossunder'].iloc[-2]

            if crossover and symbol_positions[symbol] <= 0 and (last_order_time[symbol] is None or (datetime.now() - last_order_time[symbol]).total_seconds() > order_interval_seconds):
                symbol_positions[symbol] = quantity
                response = client.placesmartorder(
                    strategy=strategy,
                    symbol=symbol,
                    action="BUY",
                    exchange=exchange,
                    price_type="MARKET",
                    product=product,
                    quantity=quantity,
                    position_size=symbol_positions[symbol]
                )
                print(f"{symbol} - Buy Order Response:", response)
                last_order_time[symbol] = datetime.now()
                requests.post(f"http://804c-83-92-100-2.ngrok-free.app/strategy/webhook/YOUR_WEBHOOK_ID", json={"symbol": symbol, "action": "BUY"})

            elif crossunder and symbol_positions[symbol] > 0 and (last_order_time[symbol] is None or (datetime.now() - last_order_time[symbol]).total_seconds() > order_interval_seconds):
                symbol_positions[symbol] = 0
                response = client.placesmartorder(
                    strategy=strategy,
                    symbol=symbol,
                    action="SELL",
                    exchange=exchange,
                    price_type="MARKET",
                    product=product,
                    quantity=quantity,
                    position_size=symbol_positions[symbol]
                )
                print(f"{symbol} - Sell Order Response:", response)
                last_order_time[symbol] = datetime.now()
                requests.post(f"http://804c-83-92-100-2.ngrok-free.app/strategy/webhook/f8f9ba1e-3144-4797-a140-bcfd5cd9ba3d", json={"symbol": symbol, "action": "SELL"})

            print(f"\n{symbol} Strategy Status: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print("-" * 50)
            print(f"Position: {symbol_positions[symbol]}")
            print(f"LTP: {df['close'].iloc[-1]}")
            print(f"Fast EMA ({fast_period}): {signals['EMA_Fast'].iloc[-2]:.2f}")
            print(f"Slow EMA ({slow_period}): {signals['EMA_Slow'].iloc[-2]:.2f}")
            print(f"Buy Signal: {crossover}")
            print(f"Sell Signal: {crossunder}")
            print("-" * 50)

        except Exception as e:
            logger.error(f"{symbol} - Error in strategy: {str(e)}")
            time.sleep(15)
            logger.error("Stack trace:", exc_info=True)
            print(traceback.format_exc())
            continue

        time.sleep(15)

if __name__ == "__main__":
    print(f"Starting {fast_period}/{slow_period} EMA Crossover Strategy for multiple symbols...")
    threads = []
    for sym in symbols:
        t = threading.Thread(target=ema_strategy, args=(sym,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()
