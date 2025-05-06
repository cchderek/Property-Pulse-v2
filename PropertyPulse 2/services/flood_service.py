import json
import time
from typing import Dict, List, Optional, Tuple
import math

from utils.data_fetcher import make_request

def get_bounding_box(latitude: float, longitude: float, radius_km: float = 2.0) -> Tuple[float, float, float, float]:
    """
    Calculate a bounding box around a point given a radius in kilometers.
    
    Args:
        latitude (float): Latitude of the center point
        longitude (float): Longitude of the center point
        radius_km (float): Radius in kilometers
        
    Returns:
        tuple: (min_lon, min_lat, max_lon, max_lat)
    """
    # Approximate conversion (these values are more accurate for the UK)
    # 1 degree of latitude is approximately 111 km
    # 1 degree of longitude varies with latitude, roughly cos(lat) * 111 km
    lat_change = radius_km / 111.0
    lon_change = radius_km / (111.0 * math.cos(math.radians(abs(latitude))))
    
    min_lat = latitude - lat_change
    max_lat = latitude + lat_change
    min_lon = longitude - lon_change
    max_lon = longitude + lon_change
    
    return (min_lon, min_lat, max_lon, max_lat)

def get_flood_data(latitude: float, longitude: float, radius_km: float = 2.0) -> Dict:
    """
    Retrieves flood zone data from the Environment Agency API for a specific location.
    
    Args:
        latitude (float): Latitude coordinate
        longitude (float): Longitude coordinate
        radius_km (float): Search radius in kilometers
        
    Returns:
        dict: Flood zone data including geometries for Flood Zones 2 and 3
    """
    try:
        # Calculate the bounding box for the query
        bbox = get_bounding_box(latitude, longitude, radius_km)
        
        # To ensure we get all data, we'll make separate requests for FZ2 and FZ3
        # First, get Flood Zone 2 data
        base_url = "https://environment.data.gov.uk/spatialdata/flood-map-for-planning-flood-zones/ogc/features/v1/collections/Flood_Zones_2_3_Rivers_and_Sea/items"
        
        # Make a single request for all flood zones
        params = {
            "bbox": ",".join(map(str, bbox)),
            "limit": 10000  # Significantly increased limit for larger areas
        }
        
        # Make the request with pagination handling
        all_features = []
        offset = 0
        while True:
            params["offset"] = offset
            response = make_request(base_url, params)
            
            if "features" not in response or not response["features"]:
                break
                
            all_features.extend(response["features"])
            if len(response["features"]) < params["limit"]:
                break
                
            offset += len(response["features"])
            
        response = {"features": all_features}
        
        # Split the response into FZ2 and FZ3
        response_fz2 = {"features": []}
        response_fz3 = {"features": []}
        
        if "features" in response:
            for feature in response["features"]:
                properties = feature.get("properties", {})
                flood_zone = properties.get("flood_zone", "")
                if flood_zone in ["FZ2", "2"]:
                    response_fz2["features"].append(feature)
                elif flood_zone in ["FZ3", "3"]:
                    response_fz3["features"].append(feature)
        
        # Check for errors
        if "error" in response_fz2:
            return {"error": response_fz2["error"]}
        if "error" in response_fz3:
            return {"error": response_fz3["error"]}
        
        # Process the responses
        flood_zone_2 = []
        flood_zone_3 = []
        
        # Process Flood Zone 2 and 3 data
        if "features" in response_fz2:
            flood_zone_2.extend([
                feature for feature in response_fz2["features"]
                if isinstance(feature, dict) and feature.get('geometry')
            ])
        
        if "features" in response_fz3:
            flood_zone_3.extend([
                feature for feature in response_fz3["features"]
                if isinstance(feature, dict) and feature.get('geometry')
            ])
            
        print(f"Found {len(flood_zone_2)} FZ2 and {len(flood_zone_3)} FZ3 features")
        
        # Get flood monitoring data from a different API
        flood_warnings = get_flood_warnings(latitude, longitude, radius_km)
        flood_risk_metrics = get_nearby_flood_monitoring_stations(latitude, longitude, radius_km)
        
        # Return the processed data
        return {
            "flood_zone_2": flood_zone_2,
            "flood_zone_3": flood_zone_3,
            "flood_warnings": flood_warnings,
            "flood_metrics": flood_risk_metrics,
            "center": {
                "latitude": latitude,
                "longitude": longitude
            },
            "radius_km": radius_km
        }
    
    except Exception as e:
        return {"error": f"Failed to retrieve flood data: {str(e)}"}

def get_flood_warnings(latitude: float, longitude: float, radius_km: float = 10.0) -> Dict:
    """
    Retrieves active flood warnings from the Environment Agency Flood Monitoring API
    for a specific location.
    
    Args:
        latitude (float): Latitude coordinate
        longitude (float): Longitude coordinate
        radius_km (float): Search radius in kilometers
        
    Returns:
        dict: Flood warnings data
    """
    try:
        # Convert radius from km to degrees (approximate)
        lat_radius = radius_km / 111.0  # 1 degree of latitude is approximately 111 km
        
        # Build the URL for the Flood Monitoring API
        base_url = "https://environment.data.gov.uk/flood-monitoring/id/floods"
        
        # Make the request to the API - no spatial filter available in API, 
        # so we'll filter results ourselves
        response = make_request(base_url, {})
        
        if "error" in response:
            return {"error": response["error"]}
        
        # Filter warnings by location
        warnings = []
        if "items" in response:
            for warning in response["items"]:
                # Check if the warning has location data
                if not isinstance(warning, dict):
                    continue
                
                # Get the flood area
                flood_area = warning.get("floodArea", {})
                if not isinstance(flood_area, dict):
                    continue
                    
                # Check if county matches (if available)
                county = flood_area.get("county", "")
                
                # Add warning to list - we'll display all active warnings as they're usually important
                warnings.append({
                    "severity": warning.get("severity", "Unknown"),
                    "severity_level": warning.get("severityLevel", 0),
                    "description": warning.get("description", "No description available"),
                    "area": warning.get("eaAreaName", "Unknown area"),
                    "county": county,
                    "message": warning.get("message", ""),
                    "time_raised": warning.get("timeRaised", ""),
                    "time_updated": warning.get("timeMessageChanged", "")
                })
        
        return {
            "count": len(warnings),
            "warnings": warnings
        }
        
    except Exception as e:
        return {
            "count": 0,
            "warnings": [],
            "error": f"Failed to retrieve flood warnings: {str(e)}"
        }

def get_nearby_flood_monitoring_stations(latitude: float, longitude: float, radius_km: float = 10.0) -> Dict:
    """
    Retrieves nearby flood monitoring stations from the Environment Agency API.
    
    Args:
        latitude (float): Latitude coordinate
        longitude (float): Longitude coordinate
        radius_km (float): Search radius in kilometers
        
    Returns:
        dict: Nearby flood monitoring stations data
    """
    try:
        # Build the URL for the Environment Agency Flood Monitoring API
        base_url = "https://environment.data.gov.uk/flood-monitoring/id/stations"
        
        # Set parameters for the query
        params = {
            "lat": latitude,
            "long": longitude,
            "dist": radius_km,  # The API uses a distance parameter in km
            "_limit": 5  # Limit to 5 nearby stations
        }
        
        # Make the request to the API
        response = make_request(base_url, params)
        
        if "error" in response:
            return {"error": response["error"]}
        
        # Extract station data
        stations = []
        if "items" in response:
            for station in response["items"]:
                if not isinstance(station, dict):
                    continue
                    
                # Get current reading if available
                latest_reading = None
                measures = station.get("measures", [])
                
                if isinstance(measures, list) and len(measures) > 0:
                    for measure in measures:
                        if isinstance(measure, dict) and "latestReading" in measure:
                            latest_reading = {
                                "value": measure.get("latestReading", {}).get("value", "N/A"),
                                "date": measure.get("latestReading", {}).get("dateTime", "N/A"),
                                "parameter": measure.get("parameterName", "Unknown parameter")
                            }
                            break
                
                # Add station to list
                stations.append({
                    "name": station.get("label", "Unknown station"),
                    "river": station.get("riverName", "Unknown river"),
                    "type": station.get("stationType", "Unknown type"),
                    "status": station.get("status", "Unknown status"),
                    "distance_km": station.get("distance", "Unknown distance"),
                    "latest_reading": latest_reading
                })
        
        return {
            "count": len(stations),
            "stations": stations
        }
        
    except Exception as e:
        return {
            "count": 0,
            "stations": [],
            "error": f"Failed to retrieve flood monitoring stations: {str(e)}"
        }

def point_in_polygon(point, polygon):
    """Check if a point is inside a polygon using ray casting algorithm."""
    x, y = point
    n = len(polygon)
    inside = False
    p1x, p1y = polygon[0]
    for i in range(n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside

def check_point_in_flood_zones(longitude: float, latitude: float, flood_data: dict) -> tuple:
    """Check if a point is within any flood zones."""
    point = (longitude, latitude)
    in_zone_2 = False
    in_zone_3 = False
    
    # Check Flood Zone 3 first (higher priority)
    for feature in flood_data.get('flood_zone_3', []):
        geometry = feature.get('geometry', {})
        if geometry.get('type') == 'Polygon':
            coordinates = geometry['coordinates']
            # Check each ring in the polygon
            for ring in coordinates:
                if point_in_polygon(point, ring):
                    in_zone_3 = True
                    break
        elif geometry.get('type') == 'MultiPolygon':
            coordinates = geometry['coordinates']
            # Check each polygon in the multipolygon
            for polygon in coordinates:
                for ring in polygon:
                    if point_in_polygon(point, ring):
                        in_zone_3 = True
                        break
        if in_zone_3:
            break
                
    # Check Flood Zone 2 if not in Zone 3
    if not in_zone_3:
        for feature in flood_data.get('flood_zone_2', []):
            geometry = feature.get('geometry', {})
            if geometry.get('type') == 'Polygon':
                coordinates = geometry['coordinates']
                # Check each ring in the polygon
                for ring in coordinates:
                    if point_in_polygon(point, ring):
                        in_zone_2 = True
                        break
            elif geometry.get('type') == 'MultiPolygon':
                coordinates = geometry['coordinates']
                # Check each polygon in the multipolygon
                for polygon in coordinates:
                    for ring in polygon:
                        if point_in_polygon(point, ring):
                            in_zone_2 = True
                            break
            if in_zone_2:
                break
    
    return in_zone_2, in_zone_3

def get_flood_risk_description(flood_data: dict, longitude: float, latitude: float) -> Dict:
    """
    Provides a description of the flood risk based on whether the location point
    falls within Flood Zones 2 or 3.
    
    Args:
        flood_data (dict): The flood zone data
        longitude (float): Longitude of the location
        latitude (float): Latitude of the location
        
    Returns:
        dict: Description of flood risk levels including title, text, and risk level
    """
    # Check if the exact point is in any flood zones
    in_zone_2, in_zone_3 = check_point_in_flood_zones(longitude, latitude, flood_data)
    
    if in_zone_3:
        return {
            "title": "High Flood Risk (Flood Zone 3)",
            "text": (
                "This location is within a high flood risk area (1% or greater annual probability of river flooding, "
                "or 0.5% or greater annual probability of sea flooding). "
                "Properties at this location have a high probability of flooding."
            ),
            "risk_level": "high"
        }
    elif in_zone_2:
        return {
            "title": "Medium Flood Risk (Flood Zone 2)",
            "text": (
                "This area has a medium probability of flooding (between 0.1% and 1% annual probability of river flooding, "
                "or between 0.1% and 0.5% annual probability of sea flooding). "
                "Properties in this zone have a medium probability of flooding."
            ),
            "risk_level": "medium"
        }
    else:
        return {
            "title": "Low Flood Risk (Flood Zone 1)",
            "text": (
                "This area has a low probability of flooding (less than 0.1% annual probability). "
                "Properties in this zone have a low probability of flooding."
            ),
            "risk_level": "low"
        }