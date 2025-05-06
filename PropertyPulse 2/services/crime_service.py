from utils.data_fetcher import get_json_data, make_request
import datetime
import requests
import time

def get_crime_data_for_date(latitude, longitude, radius_km, date_str):
    """
    Fetches crime data for a specific month using lat/lng parameters.
    
    Args:
        latitude (float): Latitude coordinate
        longitude (float): Longitude coordinate
        radius_km (float): Radius in kilometers
        date_str (str): Date in format YYYY-MM
        
    Returns:
        list: List of crimes for the month
    """
    # Convert radius from km to miles (API uses miles)
    radius_miles = min(radius_km * 0.621371, 1.0)  # Max 1 mile radius for API
    
    # Make the API request with lat/lng
    url = "https://data.police.uk/api/crimes-street/all-crime"
    params = {
        "lat": latitude,
        "lng": longitude,
        "date": date_str
    }
    
    # API has a 1-mile maximum radius parameter
    if radius_miles <= 1.0:
        params["radius"] = radius_miles
    
    # Try to make the request - some months might not have data
    try:
        headers = {
            'User-Agent': 'PropertySearchDashboard/1.0',
            'Accept': 'application/json'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.json()
        else:
            return {
                'error': f"Request failed with status code: {response.status_code}",
                'details': response.text if response.text else "No details available"
            }
    except Exception as e:
        return {'error': f"Failed to fetch crime data: {str(e)}"}

def get_crime_data(latitude, longitude, radius=1, date=None):
    """
    Fetches crime data for a specific location from the Police UK API.
    If no date is provided, fetches data for the most recent available month.
    
    Args:
        latitude (float): Latitude coordinate
        longitude (float): Longitude coordinate
        radius (float): Search radius in kilometers (default 1 km)
        date (str): Optional date in format YYYY-MM (default is last month)
        
    Returns:
        list: Combined list of crime data dictionaries from the last 24 months
    """
    # If date provided, just get that month
    if date:
        return get_crime_data_for_date(latitude, longitude, radius, date)
    
    # Otherwise, get data for the last 24 months
    today = datetime.datetime.now()
    all_crimes = []
    
    # Get data for the last 12 months (API typically only has ~12 months of data)
    for i in range(12):
        # Calculate the month
        current_month = today.month - i
        current_year = today.year
        
        # Adjust for wrap-around to previous year(s)
        while current_month <= 0:
            current_month += 12
            current_year -= 1
        
        # Format date string
        date_str = f"{current_year}-{current_month:02d}"
        
        # Get crime data for this month
        month_crimes = get_crime_data_for_date(latitude, longitude, radius, date_str)
        
        # If we got a valid response, add to results
        if not isinstance(month_crimes, dict) or "error" not in month_crimes:
            all_crimes.extend(month_crimes)
        
        # Sleep briefly to avoid rate limiting
        time.sleep(0.2)
    
    return all_crimes

def get_crime_categories():
    """
    Fetches available crime categories from the Police UK API.
    
    Returns:
        list: List of crime categories
    """
    url = "https://data.police.uk/api/crime-categories"
    response_data = get_json_data(url)
    
    if "error" in response_data:
        return response_data
    
    return response_data

def get_last_year_monthly_data(latitude, longitude, radius=1):
    """
    Gets crime data for the last 12 months, organized by month.
    
    Args:
        latitude (float): Latitude coordinate
        longitude (float): Longitude coordinate
        radius (float): Search radius in kilometers
        
    Returns:
        dict: Monthly crime data for the last year
    """
    today = datetime.datetime.now()
    monthly_data = {}
    
    # Get data for the last 12 months
    for i in range(12):
        # Calculate the month
        current_month = today.month - i
        current_year = today.year
        
        # Adjust for wrap-around to previous year(s)
        while current_month <= 0:
            current_month += 12
            current_year -= 1
        
        # Format date string
        date_str = f"{current_year}-{current_month:02d}"
        
        # Get crime data for this month
        crimes = get_crime_data_for_date(latitude, longitude, radius, date_str)
        
        if not isinstance(crimes, dict) or "error" not in crimes:
            monthly_data[date_str] = crimes
        
        # Sleep briefly to avoid rate limiting
        time.sleep(0.2)
    
    return monthly_data