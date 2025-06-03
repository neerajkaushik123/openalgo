import pandas as pd

from datetime import datetime, timedelta
from NiftyOptionCreditSpread import NiftyOptionCreditSpread
from openalgo import api
import time

api_key = '92fbae88ad9c469aa53b96c4f1e0b2db3341c06bc6c80303092687fc78741abe'
client = api(api_key=api_key, host='http://127.0.0.1:5000')


def get_nifty_data():
    """Fetch NIFTY data from Yahoo Finance"""
    # Get data for the last 30 days with 1-hour intervals
    # end_date = datetime.now()
    # start_date = end_date - timedelta(days=30)
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    df = client.history(
                    symbol="FINNIFTY", #NIFTY
                    exchange="NSE_INDEX",
                    interval="30m",
                    start_date=start_date,
                    end_date=end_date
                )
    print(df.head(5))
    # Fetch NIFTY data
    # nifty = yf.download("^NSEI", 
    #                    start=start_date,
    #                    end=end_date,
    #                    interval="1h")
    
    return df

def main():
    # Create strategy instance
    strategy = NiftyOptionCreditSpread()
    
    # Print strategy information
    info = strategy.get_strategy_info()
    print("\nStrategy Information:")
    print(info['description'])
    
    while True:
        try:
            # Get NIFTY data
            print("\nFetching NIFTY data...")
            data = get_nifty_data()
            print(data)
            # Execute strategy
            print("\nExecuting strategy...")
            result = strategy.execute_strategy(data)
            
            if result:
                print("\nStrategy Results:")
                print(f"Signal: {'LONG' if result['signal'] == 1 else 'SHORT'}")
                print(f"Spot Price: {result['spot_price']:.2f}")
                print(f"Expiry Date: {result['expiry_date'].strftime('%Y-%m-%d')}")
                print("\nOption Strikes:")
                print(f"Type: {result['option_strikes']['type'].upper()}")
                print(f"Buy Strike: {result['option_strikes']['buy_strike']}")
                print(f"Sell Strike: {result['option_strikes']['sell_strike']}")
                print(f"\nTimestamp: {result['timestamp']}")
            else:
                print("\nNo trading signal generated at this time.")
        except Exception as e:
            print(f"Error in strategy: {str(e)}")
            time.sleep(15)
            continue

        time.sleep(30)


if __name__ == "__main__":
    main() 