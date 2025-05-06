import re
import requests

def validate_postcode(postcode):
    """
    Validates a UK postcode using regex and optional API verification.
    
    Args:
        postcode (str): The postcode to validate
        
    Returns:
        tuple: (is_valid, formatted_postcode, error_message)
    """
    if not postcode:
        return False, "", "Postcode cannot be empty"
    
    # Remove all whitespace
    postcode = postcode.replace(" ", "").upper()
    
    # UK postcode regex pattern
    # Basic pattern that covers most UK postcodes
    uk_postcode_pattern = r'^[A-Z]{1,2}[0-9][A-Z0-9]?[0-9][A-Z]{2}$'
    
    if not re.match(uk_postcode_pattern, postcode):
        return False, postcode, "Invalid postcode format"
    
    # Format the postcode with a space before the last three characters
    formatted_postcode = postcode[:-3] + " " + postcode[-3:]
    
    # Optionally validate using postcodes.io API
    try:
        response = requests.get(f"https://api.postcodes.io/postcodes/{postcode}/validate")
        if response.status_code == 200:
            data = response.json()
            if data["status"] == 200:
                if data["result"]:
                    return True, formatted_postcode, ""
                else:
                    return False, formatted_postcode, "Postcode not found in database"
        return True, formatted_postcode, ""  # If API fails, fall back to regex validation
    except:
        return True, formatted_postcode, ""  # If API call fails, fall back to regex validation
