import requests
import json
import logging
from typing import Dict, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)

class WebhookError(Exception):
    """Custom exception for webhook errors"""
    pass

def send_webhook_data(webhook_url: str, data: Dict) -> Dict:
    """
    Send data to a webhook URL
    
    Args:
        webhook_url (str): The complete webhook URL
        data (Dict): The data to send in the webhook
        
    Returns:
        Dict: Response from the webhook
        
    Raises:
        WebhookError: If the request fails or returns non-200 status
    """
    try:
        # Add timestamp to the data
        data['timestamp'] = datetime.now().isoformat()
        
        # Make the POST request
        response = requests.post(
            webhook_url,
            json=data,
            timeout=5  # 5 seconds timeout
        )
        
        # Check response status
        if response.status_code != 200:
            raise WebhookError(
                f"Request failed with status {response.status_code}: "
                f"{response.text}"
            )
        
        return response.json()
        
    except requests.exceptions.Timeout:
        raise WebhookError("Request timed out")
    except requests.exceptions.ConnectionError:
        raise WebhookError("Connection failed")
    except json.JSONDecodeError:
        raise WebhookError("Invalid JSON response")
    except Exception as e:
        raise WebhookError(f"Unexpected error: {str(e)}")

def send_strategy_webhook(host_url: str, webhook_id: str, symbol: str, action: str, position_size: Optional[int] = None) -> Dict:
    """
    Send a strategy signal via webhook
    
    Args:
        host_url (str): Base URL of the OpenAlgo server
        webhook_id (str): Strategy's webhook ID
        symbol (str): Trading symbol
        action (str): "BUY" or "SELL"
        position_size (int, optional): Required for BOTH mode
        
    Returns:
        Dict: Response from the webhook
    """
    # Construct webhook URL
    webhook_url = f"{host_url}/strategy/webhook/{webhook_id}"
    
    # Prepare message
    post_message = {
        "symbol": symbol,
        "action": action.upper()
    }
    
    # Add position_size for BOTH mode
    if position_size is not None:
        post_message["position_size"] = str(position_size)
    
    return send_webhook_data(webhook_url, post_message)

def send_chartink_webhook(host_url: str, webhook_id: str, stocks: str, scan_name: str, trigger_prices: str = None) -> Dict:
    """
    Send a Chartink signal via webhook
    
    Args:
        host_url (str): Base URL of the OpenAlgo server
        webhook_id (str): Chartink strategy's webhook ID
        stocks (str): Comma-separated list of stock symbols
        scan_name (str): Name of the scan (e.g., "BUY", "SELL")
        trigger_prices (str, optional): Comma-separated list of trigger prices
        
    Returns:
        Dict: Response from the webhook
    """
    # Construct webhook URL
    webhook_url = f"{host_url}/chartink/webhook/{webhook_id}"
    
    # Prepare message
    post_message = {
        "stocks": stocks,
        "scan_name": scan_name.upper(),
        "scan_url": "custom-scan",
        "alert_name": "Custom Alert"
    }
    
    # Add trigger prices if provided
    if trigger_prices:
        post_message["trigger_prices"] = trigger_prices
    
    return send_webhook_data(webhook_url, post_message)

# Example usage
if __name__ == "__main__":
    # Example host URL
    host = "http://127.0.0.1:5000"
    
    # Example webhook IDs
    strategy_webhook_id = "your-strategy-webhook-id"
    chartink_webhook_id = "your-chartink-webhook-id"
    
    try:
        # Example 1: Send strategy webhook
        result = send_strategy_webhook(
            host,
            strategy_webhook_id,
            "RELIANCE",
            "BUY",
            1
        )
        print(f"Strategy webhook sent successfully: {result}")
        
        # Example 2: Send Chartink webhook
        result = send_chartink_webhook(
            host,
            chartink_webhook_id,
            "RELIANCE",
            "BUY",
            "2500.50"
        )
        print(f"Chartink webhook sent successfully: {result}")
        
    except WebhookError as e:
        print(f"Webhook error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}") 