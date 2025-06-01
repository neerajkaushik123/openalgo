import importlib
import logging
import traceback
from typing import Tuple, Dict, Any, Optional, List, Union
from database.auth_db import get_auth_token_broker
from collections import defaultdict
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def format_decimal(value):
    """Format numeric value to 2 decimal places"""
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    return value

def format_holdings_data(holdings_data):
    """Format all numeric values in holdings data to 2 decimal places"""
    if isinstance(holdings_data, list):
        return [
            {
                key: format_decimal(value) if key in ['pnl', 'pnlpercent'] else value
                for key, value in item.items()
            }
            for item in holdings_data
        ]
    return holdings_data

def format_statistics(stats):
    """Format all numeric values in statistics to 2 decimal places"""
    if isinstance(stats, dict):
        return {
            key: format_decimal(value)
            for key, value in stats.items()
        }
    return stats

def import_broker_module(broker_name: str) -> Optional[Dict[str, Any]]:
    """
    Dynamically import the broker-specific holdings modules.
    
    Args:
        broker_name: Name of the broker
        
    Returns:
        Dictionary of broker functions or None if import fails
    """
    try:
        # Import API module
        api_module = importlib.import_module(f'broker.{broker_name}.api.order_api')
        # Import mapping module
        mapping_module = importlib.import_module(f'broker.{broker_name}.mapping.order_data')
        return {
            'get_holdings': getattr(api_module, 'get_holdings'),
            'map_portfolio_data': getattr(mapping_module, 'map_portfolio_data'),
            'calculate_portfolio_statistics': getattr(mapping_module, 'calculate_portfolio_statistics'),
            'transform_holdings_data': getattr(mapping_module, 'transform_holdings_data')
        }
    except (ImportError, AttributeError) as error:
        logger.error(f"Error importing broker modules: {error}")
        return None

def analyze_holdings(holdings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze holdings data to provide detailed portfolio insights.
    
    Args:
        holdings: List of holdings data
        
    Returns:
        Dictionary containing portfolio analysis metrics
    """
    try:
        if not holdings:
            return {
                'status': 'error',
                'message': 'No holdings data available for analysis'
            }
            
        # Initialize analysis containers
        total_investment = 0
        total_current_value = 0
        total_pnl = 0
        exchange_exposure = defaultdict(float)
        product_exposure = defaultdict(float)
        pnl_distribution = []
        value_categories = {
            'high_value': 0,  # > 100,000
            'mid_value': 0,   # 10,000 - 100,000
            'low_value': 0    # < 10,000
        }
        risk_metrics = {
            'max_drawdown': 0,
            'volatility': 0,
            'sharpe_ratio': 0
        }
        
        # Calculate basic metrics
        for holding in holdings:
            if holding.get('quantity', 0) == 0:
                continue
            # Investment metrics
            investment = float(holding.get('averageprice', 0)) * float(holding.get('quantity', 0))
            current_value = float(holding.get('ltp', 0)) * float(holding.get('quantity', 0))
            pnl = float(holding.get('pnl', 0))
            
            total_investment += investment
            total_current_value += current_value
            total_pnl += pnl
            pnl_distribution.append(pnl)
            
            # Exchange exposure
            exchange = holding.get('exchange', 'Unknown')
            exchange_exposure[exchange] += current_value
            
            # Product type exposure
            # product = holding.get('product', 'Unknown')
            # product_exposure[product] += current_value
            
            # Value-based categorization
            if current_value > 100000:
                value_categories['high_value'] += 1
            elif current_value > 10000:
                value_categories['mid_value'] += 1
            else:
                value_categories['low_value'] += 1
        
        # Calculate portfolio metrics
        portfolio_value = total_current_value
        portfolio_pnl_percent = (total_pnl / total_investment * 100) if total_investment > 0 else 0
        
        # Calculate exchange weights
        # exchange_weights = {
        #     exchange: (value / portfolio_value * 100)
        #     for exchange, value in exchange_exposure.items()
        # }
        
        # Calculate product weights
        # product_weights = {
        #     product: (value / portfolio_value * 100)
        #     for product, value in product_exposure.items()
        # }
        
        # Calculate risk metrics
        if pnl_distribution:
            pnl_array = np.array(pnl_distribution)
            risk_metrics.update({
                'max_drawdown': float(np.min(pnl_array)),
                'volatility': float(np.std(pnl_array)),
                'sharpe_ratio': float(np.mean(pnl_array) / np.std(pnl_array)) if np.std(pnl_array) != 0 else 0
            })
        
        # Prepare analysis results
        analysis = {
            'portfolio_summary': {
                'total_investment': round(total_investment, 2),
                'current_value': round(portfolio_value, 2),
                'total_pnl': round(total_pnl, 2),
                'pnl_percentage': round(portfolio_pnl_percent, 2),
                'number_of_holdings': len(holdings)
            },
            # 'exchange_exposure': {
            #     exchange: round(weight, 2)
            #     for exchange, weight in exchange_weights.items()
            # },
            # 'product_exposure': {
            #     product: round(weight, 2)
            #     for product, weight in product_weights.items()
            # },
            'value_distribution': {
                'high_value': value_categories['high_value'],
                'mid_value': value_categories['mid_value'],
                'low_value': value_categories['low_value']
            },
            'risk_metrics': {
                'max_drawdown': round(risk_metrics['max_drawdown'], 2),
                'volatility': round(risk_metrics['volatility'], 2),
                'sharpe_ratio': round(risk_metrics['sharpe_ratio'], 2)
            },
            'top_performers': sorted(
                holdings,
                key=lambda x: float(x.get('pnlpercent', 0)),
                reverse=True
            )[:3],
            'bottom_performers': sorted(
                holdings,
                key=lambda x: float(x.get('pnlpercent', 0))
            )[:3]
        }
        
        return {
            'status': 'success',
            'data': analysis
        }
        
    except Exception as e:
        logger.error(f"Error analyzing holdings: {e}")
        traceback.print_exc()
        return {
            'status': 'error',
            'message': f'Error analyzing holdings: {str(e)}'
        }

def get_holdings_with_auth(auth_token: str, broker: str) -> Tuple[bool, Dict[str, Any], int]:
    """
    Get holdings details using provided auth token.
    
    Args:
        auth_token: Authentication token for the broker API
        broker: Name of the broker
        
    Returns:
        Tuple containing:
        - Success status (bool)
        - Response data (dict)
        - HTTP status code (int)
    """
    broker_funcs = import_broker_module(broker)
    if broker_funcs is None:
        return False, {
            'status': 'error',
            'message': 'Broker-specific module not found'
        }, 404

    try:
        # Get holdings using broker functions
        holdings = broker_funcs['get_holdings'](auth_token)
        
        if 'status' in holdings and holdings['status'] == 'error':
            return False, {
                'status': 'error',
                'message': holdings.get('message', 'Error fetching holdings data')
            }, 500

        # Transform data using mapping functions
        holdings = broker_funcs['map_portfolio_data'](holdings)
        portfolio_stats = broker_funcs['calculate_portfolio_statistics'](holdings)
        holdings = broker_funcs['transform_holdings_data'](holdings)
        
        # Format numeric values to 2 decimal places
        formatted_holdings = format_holdings_data(holdings)
        formatted_stats = format_statistics(portfolio_stats)
        
        # Add holdings analysis
        # analysis = analyze_holdings(formatted_holdings)
        
        return True, {
            'status': 'success',
            'data': {
                'holdings': formatted_holdings,
                'statistics': formatted_stats,
                # 'analysis': analysis.get('data', {}) if analysis['status'] == 'success' else {}
            }
        }, 200
    except Exception as e:
        logger.error(f"Error processing holdings data: {e}")
        traceback.print_exc()
        return False, {
            'status': 'error',
            'message': str(e)
        }, 500

def get_holdings(
    api_key: Optional[str] = None, 
    auth_token: Optional[str] = None, 
    broker: Optional[str] = None
) -> Tuple[bool, Dict[str, Any], int]:
    """
    Get holdings details.
    Supports both API-based authentication and direct internal calls.
    
    Args:
        api_key: OpenAlgo API key (for API-based calls)
        auth_token: Direct broker authentication token (for internal calls)
        broker: Direct broker name (for internal calls)
        
    Returns:
        Tuple containing:
        - Success status (bool)
        - Response data (dict)
        - HTTP status code (int)
    """
    # Case 1: API-based authentication
    if api_key and not (auth_token and broker):
        AUTH_TOKEN, broker_name = get_auth_token_broker(api_key)
        if AUTH_TOKEN is None:
            return False, {
                'status': 'error',
                'message': 'Invalid openalgo apikey'
            }, 403
        return get_holdings_with_auth(AUTH_TOKEN, broker_name)
    
    # Case 2: Direct internal call with auth_token and broker
    elif auth_token and broker:
        return get_holdings_with_auth(auth_token, broker)
    
    # Case 3: Invalid parameters
    else:
        return False, {
            'status': 'error',
            'message': 'Either api_key or both auth_token and broker must be provided'
        }, 400
