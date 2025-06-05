import os
import hashlib
import json
import logging
from utils.httpx_client import get_httpx_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def authenticate_broker(request_token):
    try:
        # Fetching the necessary credentials from environment variables
        BROKER_API_KEY = os.getenv('BROKER_API_KEY')
        BROKER_API_SECRET = os.getenv('BROKER_API_SECRET')
        
        if not BROKER_API_KEY or not BROKER_API_SECRET:
            logger.error("API credentials not found in environment variables")
            return None, "API credentials not configured"
        
        # Zerodha's endpoint for session token exchange
        url = 'https://api.kite.trade/session/token'
        
        # Log the request token for debugging
        logger.info(f"Request token received: {request_token}")
        
        # Generating the checksum as a SHA-256 hash of concatenated api_key, request_token, and api_secret
        checksum_input = f"{BROKER_API_KEY}{request_token}{BROKER_API_SECRET}"
        checksum = hashlib.sha256(checksum_input.encode()).hexdigest()
        
        # The payload for the POST request
        data = {
            'api_key': BROKER_API_KEY,
            'request_token': request_token,
            'checksum': checksum
        }
        
        # Log the request details (excluding sensitive data)
        logger.info(f"Making authentication request to {url}")
        logger.debug(f"Request payload (excluding sensitive data): {{'request_token': '{request_token}'}}")
        
        # Get the shared httpx client with connection pooling
        client = get_httpx_client()
        
        # Setting the headers as specified by Zerodha's documentation
        headers = {
            'X-Kite-Version': '3',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        try:
            # Performing the POST request using the shared client
            response = client.post(
                url,
                headers=headers,
                data=data,  # Send as form data
                timeout=30.0  # Add timeout
            )
            
            # Log response status
            logger.info(f"Response status code: {response.status_code}")
            
            # Try to parse response as JSON
            try:
                response_data = response.json()
                logger.debug(f"Response data: {json.dumps(response_data, indent=2)}")
            except json.JSONDecodeError:
                logger.error(f"Failed to parse response as JSON: {response.text}")
                return None, "Invalid response from server"
            
            # Check for error in response
            if response_data.get('status') == 'error':
                error_message = response_data.get('message', 'Unknown error')
                logger.error(f"API error: {error_message}")
                return None, f"API error: {error_message}"
            
            # Check for access token
            if 'data' in response_data and 'access_token' in response_data['data']:
                logger.info("Successfully obtained access token")
                return response_data['data']['access_token'], None
            else:
                logger.error("No access token in response")
                return None, "Authentication succeeded but no access token was returned"
                
        except Exception as e:
            # Handle HTTP errors and timeouts
            error_message = str(e)
            try:
                if hasattr(e, 'response') and e.response is not None:
                    error_detail = e.response.json()
                    error_message = error_detail.get('message', str(e))
                    logger.error(f"API error response: {error_detail}")
            except:
                logger.error(f"Error parsing error response: {error_message}")
            
            return None, f"API error: {error_message}"
    except Exception as e:
        # Exception handling
        logger.error(f"Authentication error: {str(e)}", exc_info=True)
        return None, f"An exception occurred: {str(e)}"
