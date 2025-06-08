"""
OpenAlgo WebSocket Feed Example
"""

from openalgo import api
import time

# Initialize feed client with explicit parameters
client = api(
    api_key="92fbae88ad9c469aa53b96c4f1e0b2db3341c06bc6c80303092687fc78741abe",  # Replace with your API key
    host="http://127.0.0.1:5000",  # Replace with your API host
    ws_url="ws://127.0.0.1:8765"  # Explicit WebSocket URL (can be different from REST API host)
)

# MCX instruments for testing
instruments_list = [
    {"exchange": "MCX", "symbol": "GOLD05AUG25FUT"},
    {"exchange": "MCX", "symbol": "CRUDEOIL19AUG25FUT"},
    {"exchange": "NSEINDEX", "symbol": "NIFTY50"}
]

def on_data_received(data):
    print("LTP Update:")
    print(data)

# Connect and subscribe
client.connect()
client.subscribe_ltp(instruments_list, on_data_received=on_data_received)

# Poll LTP data a few times
for i in range(100):
    print(f"\nPoll {i+1}:")
    print(client.get_ltp())
    time.sleep(0.5)

# Cleanup
client.unsubscribe_ltp(instruments_list)
client.disconnect()
