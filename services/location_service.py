from utils.data_fetcher import get_json_data

def get_location_data(postcode):
    """
    Retrieves location data for a given postcode using postcodes.io API.
    
    Args:
        postcode (str): The UK postcode to search for
        
    Returns:
        dict: Location data including coordinates, administrative areas, etc.
    """
    # Remove spaces for API call
    postcode_no_space = postcode.replace(" ", "")
    
    # Call the postcodes.io API
    url = f"https://api.postcodes.io/postcodes/{postcode_no_space}"
    response_data = get_json_data(url)
    
    if "error" in response_data:
        return response_data
    
    # Check if response is as expected
    if "result" not in response_data:
        return {"error": "Unexpected API response format"}
    
    result = response_data["result"]
    
    # Extract the outcode (first part of postcode)
    outcode = postcode.split(" ")[0] if " " in postcode else postcode
    
    # Extract and organize relevant location data
    location_data = {
        "postcode": result.get("postcode", postcode),
        "outcode": outcode,
        "latitude": result.get("latitude"),
        "longitude": result.get("longitude"),
        "region": result.get("region"),
        "country": result.get("country"),
        "admin_district": result.get("admin_district"),
        "admin_ward": result.get("admin_ward"),
        "parliamentary_constituency": result.get("parliamentary_constituency"),
        "european_electoral_region": result.get("european_electoral_region"),
        "primary_care_trust": result.get("primary_care_trust"),
        "nuts": result.get("nuts"),
        "codes": result.get("codes", {})
    }
    
    return location_data

def get_nearby_postcodes(latitude, longitude, radius=1000, limit=10):
    """
    Gets nearby postcodes based on coordinates.
    
    Args:
        latitude (float): Latitude coordinate
        longitude (float): Longitude coordinate
        radius (int): Search radius in meters
        limit (int): Maximum number of results
        
    Returns:
        list: List of nearby postcodes with their data
    """
    url = "https://api.postcodes.io/postcodes"
    params = {
        "lat": latitude,
        "lon": longitude,
        "radius": radius,
        "limit": limit
    }
    
    response_data = get_json_data(url, params)
    
    if "error" in response_data:
        return response_data
    
    if "result" not in response_data:
        return {"error": "Unexpected API response format"}
    
    return response_data["result"]
