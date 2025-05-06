import requests
from urllib.parse import quote
import json
import time

def make_request(url, params=None, headers=None, max_retries=3, retry_delay=1):
    """
    Makes an HTTP request with retry logic.
    
    Args:
        url (str): The URL to request
        params (dict, optional): Query parameters
        headers (dict, optional): Request headers
        max_retries (int): Maximum number of retry attempts
        retry_delay (int): Delay between retries in seconds
        
    Returns:
        dict: The JSON response or an error dictionary
    """
    if headers is None:
        headers = {
            'User-Agent': 'PropertySearchDashboard/1.0',
            'Accept': 'application/json'
        }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:  # Rate limit
                retry_after = int(response.headers.get('Retry-After', retry_delay * 2))
                time.sleep(retry_after)
                continue
            else:
                return {
                    'error': f"Request failed with status code: {response.status_code}",
                    'details': response.text if response.text else "No details available"
                }
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            return {'error': 'Request timed out'}
        except requests.exceptions.RequestException as e:
            return {'error': f"Request failed: {str(e)}"}
    
    return {'error': 'Maximum retry attempts reached'}

def get_json_data(url, params=None):
    """
    Fetches JSON data from a URL.
    
    Args:
        url (str): The URL to fetch from
        params (dict, optional): Query parameters
        
    Returns:
        dict: The JSON data or an error dictionary
    """
    try:
        response = make_request(url, params)
        return response
    except Exception as e:
        return {'error': f"Failed to fetch data: {str(e)}"}
