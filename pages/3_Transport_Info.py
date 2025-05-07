import streamlit as st
import folium
from streamlit_folium import folium_static
import requests
import math # For distance calculation
import time # For potential delay between API calls

# Assuming you have this utility or replace with basic validation
# (Using the sample postcode_validator from previous comments)
from utils.postcode_validator import validate_postcode


# Set page config
st.set_page_config(
    page_title="Transport Information",
    page_icon="🚍",
    layout="wide"
)

# Title and description
st.title("Transport Information")
st.markdown("""
This page shows transport options and stations near UK postcodes, using Google Maps data, including:
- Bus stops and routes (as available via Google)
- Train stations
- Underground/metro stations (where available)
- Tram stops (including Metrolink)
""")

# --- Google Maps API Functions ---
GOOGLE_MAPS_API_KEY = st.secrets.get("GOOGLE_MAPS_API_KEY")
if not GOOGLE_MAPS_API_KEY:
    st.error("Google Maps API Key not found in secrets. Please add it to your Streamlit secrets.")
    st.stop()

@st.cache_data
def get_google_geocode_data(postcode: str):
    """Get location data (lat, lon) for a postcode using Google Geocoding API."""
    geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": postcode,
        "key": GOOGLE_MAPS_API_KEY,
        "components": "country:GB"
    }
    try:
        response = requests.get(geocode_url, params=params)
        response.raise_for_status()
        data = response.json()
        if data["status"] == "OK" and data["results"]:
            location = data["results"][0]["geometry"]["location"]
            address_components = data["results"][0]["address_components"]

            admin_district = next((comp["long_name"] for comp in address_components if "administrative_area_level_2" in comp["types"]), None)
            region = next((comp["long_name"] for comp in address_components if "administrative_area_level_1" in comp["types"]), None)
            formatted_address = data["results"][0].get("formatted_address", postcode)

            return {
                "latitude": location["lat"],
                "longitude": location["lng"],
                "postcode": postcode,
                "formatted_address": formatted_address,
                "admin_district": admin_district,
                "region": region
            }
        elif data["status"] == "ZERO_RESULTS":
            return {"error": f"Postcode not found by Google: {postcode}"}
        else:
            st.error(f"Google Geocoding API Error: {data.get('status')} - {data.get('error_message', '')}")
            return {"error": f"Geocoding API returned status: {data.get('status')}"}
    except requests.exceptions.RequestException as e:
        st.error(f"Request failed for geocoding: {str(e)}")
        return {"error": str(e)}
    except Exception as e:
        st.error(f"An unexpected error occurred during geocoding: {str(e)}")
        return {"error": str(e)}

def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance between two lat/lon points in meters."""
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return round(distance)

@st.cache_data(ttl=600) # Cache for 10 minutes
def get_google_places_data(lat, lon, radius=1000, origin_lat=None, origin_lon=None):
    """Get nearby transport places using multiple Google Places API (Nearby Search) calls."""
    places_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

    # Added "Metrolink station" and "tram stop" as keyword searches
    queries = [
        {"type": "train_station"},
        {"type": "subway_station"},
        {"type": "light_rail_station"}, # Should cover trams generally
        {"keyword": "Metrolink station"}, # Specific keyword for Manchester Metrolink
        {"keyword": "tram stop"},         # More generic keyword for trams
        {"type": "bus_station"},
        {"keyword": "bus stop"}
    ]

    all_places_dict = {} # Use dict with place_id as key for deduplication

    # --- Optional Debugging ---
    # st.session_state.debug_api_calls = [] # Initialize if not present
    # --- End Optional Debugging ---


    for query_detail in queries:
        params = {
            "key": GOOGLE_MAPS_API_KEY,
            "location": f"{lat},{lon}",
            "radius": int(radius),
        }
        params.update(query_detail)

        # --- Optional Debugging ---
        # current_call_debug = {"query": query_detail, "status": None, "results_count": 0, "results_sample": []}
        # --- End Optional Debugging ---

        try:
            response = requests.get(places_url, params=params)
            response.raise_for_status()
            data = response.json()

            # --- Optional Debugging ---
            # current_call_debug["status"] = data.get("status")
            # --- End Optional Debugging ---

            if data["status"] == "OK":
                # --- Optional Debugging ---
                # current_call_debug["results_count"] = len(data.get("results", []))
                # current_call_debug["results_sample"] = data.get("results", [])[:3] # Sample of first 3
                # --- End Optional Debugging ---

                for place in data.get("results", []):
                    place_id = place.get("place_id")
                    if not place_id:
                        continue

                    google_types = place.get("types", [])
                    place_name_lower = place.get("name", "").lower()
                    app_type = None

                    # Prioritize "Metrolink" in name for tram classification
                    if "metrolink" in place_name_lower:
                        app_type = "tram_stop"
                    elif "subway_station" in google_types:
                        app_type = "tube_station"
                    elif "light_rail_station" in google_types: # This is Google's typical type for trams
                        app_type = "tram_stop"
                    # Check for "tram" in name if other type classifications didn't catch it
                    elif "tram" in place_name_lower and "train_station" not in google_types: # Avoid misclassifying trains with "tram" in name
                        app_type = "tram_stop"
                    elif "train_station" in google_types:
                        app_type = "train_station"
                    elif "bus_station" in google_types or "bus_stop" in google_types:
                        app_type = "bus_stop"


                    if app_type and place_id not in all_places_dict: # Add if new and type assigned
                        place_lat = place["geometry"]["location"]["lat"]
                        place_lon = place["geometry"]["location"]["lng"]
                        distance_val = haversine(origin_lat or lat, origin_lon or lon, place_lat, place_lon) if origin_lat and origin_lon else None

                        all_places_dict[place_id] = {
                            "name": place.get("name"),
                            "latitude": place_lat,
                            "longitude": place_lon,
                            "type": app_type,
                            "description": place.get("vicinity"),
                            "google_place_id": place_id,
                            "distance": distance_val,
                            "google_types": google_types, # Store original types for debugging/info
                            "debug_query_source": query_detail # Store which query found this
                        }
            elif data["status"] not in ["ZERO_RESULTS", "OK"]: # Log other errors
                st.warning(f"Google Places API query ({query_detail}) returned status: {data.get('status')} - {data.get('error_message', '')}")
                # current_call_debug["error_message"] = data.get('error_message', '')

            # Consider a small delay if making many calls rapidly
            # time.sleep(0.05)

        except requests.exceptions.RequestException as e:
            st.error(f"Request failed for places query {query_detail}: {str(e)}")
            # current_call_debug["status"] = "REQUEST_EXCEPTION"
            # current_call_debug["error_message"] = str(e)
            return {"error": str(e), "member": list(all_places_dict.values())}
        except Exception as e:
            st.error(f"An unexpected error occurred during places fetch for {query_detail}: {str(e)}")
            # current_call_debug["status"] = "UNEXPECTED_EXCEPTION"
            # current_call_debug["error_message"] = str(e)
            return {"error": str(e), "member": list(all_places_dict.values())}
        # finally:
            # --- Optional Debugging ---
            # st.session_state.debug_api_calls.append(current_call_debug)
            # --- End Optional Debugging ---


    return {"member": list(all_places_dict.values())}


def create_transport_map(location_data, transport_data):
    """Create a folium map with transport locations"""
    m = folium.Map(
        location=[location_data['latitude'], location_data['longitude']],
        zoom_start=15,
        tiles='CartoDB positron'
    )

    transport_groups = {
        'train_station': folium.FeatureGroup(name="Train Stations"),
        'bus_stop': folium.FeatureGroup(name="Bus Stops"),
        'tube_station': folium.FeatureGroup(name="Underground Stations"),
        'tram_stop': folium.FeatureGroup(name="Tram Stops")
    }

    folium.Marker(
        [location_data['latitude'], location_data['longitude']],
        popup=f"<b>Postcode:</b> {location_data['postcode']}<br>{location_data.get('formatted_address', '')}",
        icon=folium.Icon(color='red', icon='home', prefix='fa')
    ).add_to(m)

    if 'member' in transport_data:
        for place in transport_data['member']:
            if not all(k in place for k in ['name', 'latitude', 'longitude', 'type']):
                continue

            distance_str = f"{place.get('distance')}m" if place.get('distance') is not None else "N/A"
            popup_content = f"""
                <div style='min-width: 200px'>
                    <b>{place['name']}</b><br>
                    <i>{place.get('description', 'N/A')}</i><br>
                    <b>Type:</b> {place['type'].replace('_', ' ').title()}<br>
                    <b>Distance:</b> {distance_str}<br>
                    <small><i>Found by: {place.get('debug_query_source', {})}</i></small><br>
                    <small><i>Google Types: {place.get('google_types', [])}</i></small>
                </div>
            """ # Added debug info to popup

            marker_config = {
                'train_station': {'color': 'green', 'icon': 'train', 'tooltip': 'Train Station'},
                'bus_stop': {'color': 'orange', 'icon': 'bus', 'tooltip': 'Bus Stop'},
                'tube_station': {'color': 'purple', 'icon': 'subway', 'tooltip': 'Underground Station'},
                'tram_stop': {'color': 'darkred', 'icon': 'train', 'tooltip': 'Tram Stop'} # FontAwesome has 'tram' icon too
            }

            place_type_lower = place['type'].lower()
            if place_type_lower in marker_config and place_type_lower in transport_groups:
                config = marker_config[place_type_lower]
                # Use 'tram' icon if available and it's a tram stop
                icon_to_use = config['icon']
                if place_type_lower == 'tram_stop':
                    icon_to_use = 'tram' # Try FontAwesome 'tram' icon

                folium.Marker(
                    [place['latitude'], place['longitude']],
                    popup=folium.Popup(popup_content, max_width=350), # Increased max_width for debug
                    icon=folium.Icon(color=config['color'], icon=icon_to_use, prefix='fa'),
                    tooltip=config['tooltip']
                ).add_to(transport_groups[place_type_lower])

    for group in transport_groups.values():
        group.add_to(m)

    folium.LayerControl().add_to(m)

    legend_html = '''
    <div style="position: fixed; bottom: 50px; left: 50px;
        background-color: white; padding: 10px; border-radius: 5px;
        border: 2px solid grey; z-index: 1000; max-height: 250px; overflow-y: auto;">
        <h4 style="margin-top: 0;">Transport Legend</h4>
        <div style="display: flex; align-items: center; margin: 5px;">
            <i class="fa fa-home" style="color: red; margin-right: 8px;"></i>
            <span>Your Location</span>
        </div>
        <div style="display: flex; align-items: center; margin: 5px;">
            <i class="fa fa-train" style="color: green; margin-right: 8px;"></i>
            <span>Train Station</span>
        </div>
        <div style="display: flex; align-items: center; margin: 5px;">
            <i class="fa fa-bus" style="color: orange; margin-right: 8px;"></i>
            <span>Bus Stop</span>
        </div>
        <div style="display: flex; align-items: center; margin: 5px;">
            <i class="fa fa-subway" style="color: purple; margin-right: 8px;"></i>
            <span>Underground Station</span>
        </div>
        <div style="display: flex; align-items: center; margin: 5px;">
            <i class="fa fa-tram" style="color: darkred; margin-right: 8px;"></i> <!-- Changed icon for legend -->
            <span>Tram Stop</span>
        </div>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    return m

# --- Streamlit UI ---

if "postcode_for_search" not in st.session_state:
    st.session_state.postcode_for_search = ""
if "search_triggered_by_example" not in st.session_state:
    st.session_state.search_triggered_by_example = False
# if "debug_api_calls" not in st.session_state: # For optional debugging
#    st.session_state.debug_api_calls = []


with st.sidebar:
    st.header("Search Transport")
    postcode_input_val = st.text_input(
        "Enter UK Postcode:",
        value=st.session_state.postcode_for_search,
        key="postcode_text_entry"
    ).strip().upper()

    if postcode_input_val != st.session_state.postcode_for_search:
        st.session_state.postcode_for_search = postcode_input_val
        st.session_state.search_triggered_by_example = False

    radius_km = st.slider("Search Radius (km)", 0.1, 5.0, 1.5, 0.1) # Default radius increased slightly
    radius_m = radius_km * 1000
    search_button_clicked = st.button("Search", use_container_width=True)

    st.markdown("---")
    st.caption("Data source:")
    st.caption("- Google Maps Platform APIs")

active_postcode = st.session_state.postcode_for_search

if not active_postcode and not search_button_clicked and not st.session_state.search_triggered_by_example:
    st.info("Enter a UK postcode in the sidebar to view transport information.")
    st.subheader("Example postcodes to try:")
    # Added Manchester postcodes
    example_postcodes = ["SW1A 1AA", "M1 1RG", "M2 1LT", "E14 9GE", "EH1 1YZ", "CF10 1EP"]
    cols = st.columns(len(example_postcodes))
    for i, col in enumerate(cols):
        with col:
            if st.button(example_postcodes[i], key=f"example_{i}"):
                st.session_state.postcode_for_search = example_postcodes[i]
                st.session_state.search_triggered_by_example = True
                st.rerun()

should_search = search_button_clicked or st.session_state.search_triggered_by_example

if should_search and active_postcode:
    if st.session_state.search_triggered_by_example:
        st.session_state.search_triggered_by_example = False
    # st.session_state.debug_api_calls = [] # Reset debug info for new search

    is_valid, formatted_postcode, error_message = validate_postcode(active_postcode)

    if not is_valid:
        st.error(f"Invalid postcode format: {error_message} (Postcode: {active_postcode})")
    else:
        with st.spinner(f"Fetching data for {formatted_postcode}..."):
            location_data = get_google_geocode_data(formatted_postcode)

            if "error" in location_data:
                st.error(f"Error fetching location data: {location_data['error']}")
            else:
                st.subheader(f"Transport Information for {location_data.get('formatted_address', formatted_postcode)}")
                st.write(f"Area: {location_data.get('admin_district', 'N/A')}, {location_data.get('region', 'N/A')}")

                if 'latitude' in location_data and 'longitude' in location_data:
                    transport_data = get_google_places_data(
                        location_data['latitude'],
                        location_data['longitude'],
                        radius=radius_m,
                        origin_lat=location_data['latitude'],
                        origin_lon=location_data['longitude']
                    )

                    if "error" in transport_data and not transport_data.get("member"):
                        st.error(f"Error fetching transport data: {transport_data['error']}")
                    elif not transport_data.get("member"):
                         st.info(f"No relevant transport locations found by Google Places API within {radius_km} km for {formatted_postcode}.")
                    else:
                        if "error" in transport_data:
                             st.warning(f"Partial data shown due to an error during transport data fetch: {transport_data['error']}")

                        map_tab, details_tab = st.tabs(["Transport Map", "Station Details"])

                        with map_tab:
                            transport_map = create_transport_map(location_data, transport_data)
                            folium_static(transport_map, width=None, height=600)

                        with details_tab:
                            # --- Optional Debugging ---
                            # with st.expander("API Call Debug Info (Raw)"):
                            #    st.json(st.session_state.get("debug_api_calls", []))
                            # --- End Optional Debugging ---

                            if 'member' in transport_data and transport_data['member']:
                                transport_types_display = {
                                    'train_station': 'Train Stations',
                                    'tube_station': 'Underground Stations',
                                    'bus_stop': 'Bus Stops',
                                    'tram_stop': 'Tram Stops'
                                }

                                stations_by_type = {key: [] for key in transport_types_display.keys()}
                                for place in transport_data['member']:
                                    place_type_lower = place.get('type', '').lower()
                                    if place_type_lower in stations_by_type:
                                        stations_by_type[place_type_lower].append(place)

                                for pt_key in stations_by_type:
                                    stations_by_type[pt_key].sort(key=lambda x: x.get('distance') if x.get('distance') is not None else float('inf'))

                                found_any_stations = False
                                for type_key, display_name in transport_types_display.items():
                                    stations = stations_by_type[type_key]
                                    if stations:
                                        found_any_stations = True
                                        st.subheader(display_name)
                                        for station in stations:
                                            with st.expander(f"{station.get('name', 'Unknown Name')}"):
                                                st.write(f"**Address/Vicinity:** {station.get('description', 'N/A')}")
                                                distance_str = f"{station.get('distance')}m" if station.get('distance') is not None else "N/A"
                                                st.write(f"**Distance:** {distance_str}")
                                                if 'latitude' in station and 'longitude' in station:
                                                    st.write(f"**Location:** {station['latitude']:.5f}, {station['longitude']:.5f}")
                                                st.caption(f"Found by query: {station.get('debug_query_source', {}).get('type') or station.get('debug_query_source', {}).get('keyword')}")
                                                st.caption(f"Google Types: {station.get('google_types', [])}")
                                                if station.get('google_place_id'):
                                                    gmaps_url = f"https://www.google.com/maps/search/?api=1&query=Google&query_place_id={station['google_place_id']}"
                                                    st.markdown(f"[View on Google Maps]({gmaps_url})")
                                if not found_any_stations:
                                    st.info(f"No transport locations of the configured types found within {radius_km} km.")
                            else:
                                st.info(f"No transport locations found within {radius_km} km.")
                else:
                    st.error("Could not determine latitude and longitude for the postcode.")
elif should_search and not active_postcode:
    st.warning("Please enter a postcode to search.")
    if st.session_state.search_triggered_by_example:
        st.session_state.search_triggered_by_example = False