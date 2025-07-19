from openalgo import api
import pandas as pd
import ta  # For technical indicators
from datetime import datetime

_api_key = '92fbae88ad9c469aa53b96c4f1e0b2db3341c06bc6c80303092687fc78741abe'
# Initialize the API client
client = api(api_key=_api_key, host='http://127.0.0.1:5000')

def apply_scanner(df):
    df.set_index('timestamp', inplace=True)
    if df is None:
        return None
    df['ema20'] = ta.trend.ema_indicator(df['close'], window=20)
    df['ema50'] = ta.trend.ema_indicator(df['close'], window=50)
    df['rsi'] = ta.momentum.rsi(df['close'], window=14)
    df['macd'] = ta.trend.macd_diff(df['close'])
    
    last = df.iloc[-1]
    return df
    # return (
    #     last['ema20'] > last['ema50']
    # )

def get_historical_data(symbol, exchange, interval, start_date, end_date):
    # Fetch historical data for BHEL
    # df = get_historical_data(symbol, exchange, interval, start_date, end_date)
    df = client.history(
        symbol=symbol,
        exchange=exchange,
        interval=interval,
        start_date=start_date,
        end_date=end_date
    )
    if df is not None:
        df = apply_scanner(df)
    else:
        df = None
        
    return df


# ==== 🏦 LOAD NSE SYMBOLS ====
# instruments_df = pd.read_csv("https://smartapisocket.angelone.in/smartapi/instruments.csv")
# download json from https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json
# parse json and get the tradingsymbol and exchange
import json

import requests
# url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
# response = requests.get(url)
# instruments_df = pd.DataFrame(columns=['symbol', 'exchange'])

# with open('OpenAPIScripMaster.json', 'wb') as f:
#     f.write(response.content)

# with open('https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json', 'r') as file:
#     data = json.load(file)
#     # Convert the list of dicts to a DataFrame
#     instruments_df = pd.DataFrame(data)
    
# instruments_df = pd.DataFrame(columns=['symbol', 'exchange'])
# instruments_df = client.instruments(exchange="NSE", tradingsymbol="BHEL")

holdings = client.holdings()

# holdings is a list of json objects in a data object

holdings_df = pd.DataFrame(holdings["data"]["holdings"])
# print(holdings_df)


scan_results = []

for index, row in holdings_df.iterrows():
    symbol = row['symbol']
    exchange = row['exchange']
    interval = "D"
    start_date = "2025-01-01"
    end_date = "2025-07-11" #datetime.now().strftime("%Y-%m-%d")
    print(symbol, exchange, interval, start_date, end_date)
    df = get_historical_data(symbol, exchange, interval, start_date, end_date)
    if df is True:
        scan_results.append(row)
    else:
        print(f"No data found or did not pass scanner for {symbol} {exchange} {interval} {start_date} {end_date}")


# Display the fetched data
if scan_results:
    results_df = pd.DataFrame(scan_results)
    print(results_df.head())
else:
    print("No symbols passed the scanner.")



# print(type(df))
# print(df.shape)
# print(df.index)

# print(df.head())
# print(df.columns)
