import streamlit as st
import folium
from streamlit_folium import folium_static
import pandas as pd
import json
from folium.plugins import MarkerCluster

from utils.postcode_validator import validate_postcode
from services.location_service import get_location_data
from services.flood_service import get_flood_data, get_flood_risk_description, get_flood_warnings, get_nearby_flood_monitoring_stations

# Set page config
st.set_page_config(
    page_title="UK Flood Risk Map",
    page_icon="🌊",
    layout="wide"
)

# Title and description
st.title("Flood Risk Map")
st.markdown("""
This page shows flood risk information around UK postcodes, including:
- Interactive flood zone map
- Flood zone 2 (medium probability) areas
- Flood zone 3 (high probability) areas
- Nearby flood monitoring stations
- Active flood warnings
- Comprehensive flood risk assessment

Data is provided by the Environment Agency Flood Map for Planning and Flood Monitoring API.
""")

# Function to create a flood risk map
def create_flood_map(location_data, flood_data, radius=2):
    """
    Creates a folium map with flood zone data visualization.
    
    Args:
        location_data (dict): Location data for the center point
        flood_data (dict): Flood zone data 
        radius (float): Search radius in kilometers
        
    Returns:
        folium.Map: Map with flood zone visualization
    """
    # Create base map with CartoDB positron tiles for better visibility
    m = folium.Map(
        location=[location_data['latitude'], location_data['longitude']],
        zoom_start=14,
        tiles='CartoDB positron'
    )
    
    # Create feature groups for different layers
    fz2_group = folium.FeatureGroup(name="Flood Zone 2 (Medium Risk)")
    fz3_group = folium.FeatureGroup(name="Flood Zone 3 (High Risk)")
    stations_group = folium.FeatureGroup(name="Monitoring Stations")
    
    # Add a marker for the postcode
    folium.Marker(
        [location_data['latitude'], location_data['longitude']],
        popup=f"<b>{location_data['postcode']}</b><br>{location_data.get('region', '')}",
        tooltip=location_data['postcode'],
        icon=folium.Icon(color="blue", icon="home", prefix="fa")
    ).add_to(m)
    
    # Add a circle to show the search radius
    folium.Circle(
        location=[location_data['latitude'], location_data['longitude']],
        radius=radius * 1000,  # Convert km to meters
        color='#3186cc',
        fill=True,
        fill_opacity=0.1,
        popup=f"{radius}km radius"
    ).add_to(m)

    # Add Flood Zone 3 (high risk) areas first
    if len(flood_data.get('flood_zone_3', [])) > 0:
        for feature in flood_data.get('flood_zone_3', []):
            try:
                if feature.get('geometry') and feature.get('geometry', {}).get('coordinates'):
                    # Add the feature to the feature group
                    folium.GeoJson(
                        data=feature,
                        style_function=lambda x: {
                            'fillColor': '#F44336',  # Red color
                            'color': '#F44336',
                            'weight': 1,
                            'fillOpacity': 0.5
                        },
                        tooltip="Flood Zone 3 - High Probability",
                        popup=folium.Popup("High Flood Risk (Flood Zone 3)<br>Land having a 1 in 100 or greater annual probability of river flooding; or Land having a 1 in 200 or greater annual probability of sea flooding.", max_width=300)
                    ).add_to(fz3_group)
            except Exception as e:
                # Skip any invalid geometries
                continue
    
    # Add Flood Zone 2 (medium risk) areas
    if len(flood_data.get('flood_zone_2', [])) > 0:
        for feature in flood_data.get('flood_zone_2', []):
            try:
                if feature.get('geometry') and feature.get('geometry', {}).get('coordinates'):
                    # Add the feature to the feature group
                    folium.GeoJson(
                        data=feature,
                        style_function=lambda x: {
                            'fillColor': '#FFC107',  # Amber color
                            'color': '#FFC107',
                            'weight': 1,
                            'fillOpacity': 0.5
                        },
                        tooltip="Flood Zone 2 - Medium Probability",
                        popup=folium.Popup("Medium Flood Risk (Flood Zone 2)<br>Land having between a 1 in 100 and 1 in 1,000 annual probability of river flooding; or land having between a 1 in 200 and 1 in 1,000 annual probability of sea flooding.", max_width=300)
                    ).add_to(fz2_group)
            except Exception as e:
                # Skip any invalid geometries
                continue
    
    # Add flood monitoring stations if available
    stations = flood_data.get("flood_metrics", {}).get("stations", [])
    for station in stations:
        if not isinstance(station, dict):
            continue
            
        # Skip if lat/long are not available
        if 'lat' not in station or 'long' not in station:
            continue
            
        # Extract coordinates
        station_lat = station.get('lat')
        station_lon = station.get('long')
        
        # Create popup content
        popup_content = f"""
        <b>{station.get('name', 'Unknown Station')}</b><br>
        River: {station.get('river', 'Unknown river')}<br>
        Type: {station.get('type', 'Unknown type')}<br>
        Status: {station.get('status', 'Unknown status')}<br>
        """
        
        # Add reading information if available
        latest_reading = station.get('latest_reading')
        if latest_reading:
            popup_content += f"""
            <b>Latest Reading:</b><br>
            Value: {latest_reading.get('value', 'N/A')} 
            ({latest_reading.get('parameter', 'Unknown')})<br>
            Date: {latest_reading.get('date', 'N/A')}
            """
        
        # Add marker
        folium.Marker(
            [station_lat, station_lon],
            popup=folium.Popup(popup_content, max_width=300),
            icon=folium.Icon(color="green", icon="tint", prefix="fa"),
            tooltip=f"Monitoring Station: {station.get('name', 'Unknown')}"
        ).add_to(stations_group)
    
    # Add feature groups to the map
    fz3_group.add_to(m)  # Add Zone 3 first (high risk)
    fz2_group.add_to(m)  # Then Zone 2 (medium risk)
    stations_group.add_to(m)  # Add monitoring stations
    
    # Add a legend
    legend_html = '''
    <div style="position: fixed; 
        bottom: 50px; left: 50px; width: 220px; height: 130px; 
        border:2px solid grey; z-index:9999; font-size:14px;
        background-color:white;
        padding: 10px;
        border-radius: 5px;
        ">
        <p style="margin-top: 0;"><b>Flood Risk Legend</b></p>
        <div style="display: flex; align-items: center; margin-bottom: 5px;">
            <div style="background-color: #FFC107; width: 20px; height: 20px; margin-right: 5px;"></div>
            <div>Flood Zone 2 (Medium)</div>
        </div>
        <div style="display: flex; align-items: center; margin-bottom: 5px;">
            <div style="background-color: #F44336; width: 20px; height: 20px; margin-right: 5px;"></div>
            <div>Flood Zone 3 (High)</div>
        </div>
        <div style="display: flex; align-items: center;">
            <div style="color: green; margin-right: 5px;"><i class="fa fa-tint"></i></div>
            <div>Monitoring Station</div>
        </div>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    return m

# Create sidebar for search options
with st.sidebar:
    st.header("Search Flood Risk Data")
    postcode = st.text_input("Enter UK Postcode:", "").strip().upper()
    
    radius = st.slider("Search Radius (km)", min_value=0.5, max_value=5.0, value=0.5, step=0.5)
    
    search_button = st.button("Search", use_container_width=True)
    
    st.markdown("---")
    st.caption("Data sources:")
    st.caption("- Environment Agency Flood Map for Planning")
    st.caption("- Environment Agency Flood Monitoring API")
    
    st.markdown("---")
    st.info("""
    **Understanding Flood Zones:**
    
    - **Flood Zone 3**: 1% or greater annual chance of river flooding or 0.5% or greater annual chance of sea flooding
    - **Flood Zone 2**: Between 0.1% and 1% annual chance of river flooding or between 0.1% and 0.5% annual chance of sea flooding
    - **Flood Zone 1**: Less than 0.1% annual chance of river or sea flooding
    """)

# Main content area
if not postcode and not search_button:
    # Initial state
    st.info("Enter a UK postcode in the sidebar to view flood risk data.")
    
    # Display some example postcodes
    st.subheader("Example postcodes to try:")
    example_postcodes = ["SW1A 1AA", "E14 9GE", "M1 1AE", "EH1 1YZ", "CF10 1EP"]
    cols = st.columns(len(example_postcodes))
    for i, col in enumerate(cols):
        with col:
            if st.button(example_postcodes[i], key=f"example_{i}"):
                postcode = example_postcodes[i]
                search_button = True

if search_button or postcode:
    # Validate postcode
    is_valid, formatted_postcode, error_message = validate_postcode(postcode)
    
    if not is_valid:
        st.error(f"Invalid postcode: {error_message}")
    else:
        with st.spinner(f"Fetching flood risk data for {formatted_postcode}..."):
            # Fetch location data
            location_data = get_location_data(formatted_postcode)
            
            if "error" in location_data:
                st.error(f"Error fetching location data: {location_data['error']}")
            else:
                # Display location information
                st.subheader(f"Flood Risk Data for {formatted_postcode}")
                st.write(f"Area: {location_data.get('admin_district', 'N/A')}, {location_data.get('region', 'N/A')}")
                
                if 'latitude' in location_data and 'longitude' in location_data:
                    # Fetch flood data - ensure coordinates are converted to float
                    flood_data = get_flood_data(
                        float(location_data['latitude']), 
                        float(location_data['longitude']),
                        radius_km=radius
                    )
                    
                    if isinstance(flood_data, dict) and "error" in flood_data:
                        st.error(f"Error fetching flood data: {flood_data['error']}")
                    else:
                        # Add debug information
                        with st.expander("Debug Info (Developer Only)"):
                            st.write(f"Flood Zone 2 features: {len(flood_data.get('flood_zone_2', []))}")
                            st.write(f"Flood Zone 3 features: {len(flood_data.get('flood_zone_3', []))}")
                            st.write(f"Monitoring stations: {len(flood_data.get('flood_metrics', {}).get('stations', []))}")
                            st.write(f"Flood warnings: {len(flood_data.get('flood_warnings', {}).get('warnings', []))}")
                            
                            if len(flood_data.get('flood_zone_2', [])) > 0:
                                st.write("Sample Flood Zone 2 Feature:")
                                st.json(flood_data.get('flood_zone_2', [])[0])
                                
                        # Create tabs for different views
                        map_tab, info_tab = st.tabs(["Flood Map", "Flood Risk Information"])
                        
                        with map_tab:
                            # Display stats
                            flood_zone_2_count = len(flood_data.get('flood_zone_2', []))
                            flood_zone_3_count = len(flood_data.get('flood_zone_3', []))
                            
                            st.write(f"Found **{flood_zone_2_count}** Flood Zone 2 areas and **{flood_zone_3_count}** Flood Zone 3 areas within {radius}km radius")
                            
                            # Create and display flood risk map
                            try:
                                flood_map = create_flood_map(location_data, flood_data, radius)
                                folium_static(flood_map)
                            except Exception as e:
                                st.error(f"Error displaying flood map: {str(e)}")
                        
                        with info_tab:
                            # Display flood risk information
                            has_flood_zone_2 = len(flood_data.get('flood_zone_2', [])) > 0
                            has_flood_zone_3 = len(flood_data.get('flood_zone_3', [])) > 0
                            
                            risk_info = get_flood_risk_description(flood_data, location_data['longitude'], location_data['latitude'])
                            
                            # Display risk level with appropriate styling
                            risk_color = {
                                "high": "#F44336",      # Red
                                "medium": "#FFC107",    # Amber
                                "low": "#4CAF50"        # Green
                            }.get(risk_info["risk_level"], "#2196F3")  # Default blue
                            
                            # Display flood risk level metric
                            st.metric(
                                "Flood Zone Risk Level", 
                                risk_info["title"].replace(" (Flood Zone 3)", "").replace(" (Flood Zone 2)", "").replace(" (Flood Zone 1)", ""),
                                delta=None
                            )
                                
                            st.markdown(f"""
                            <div style="padding: 20px; border-radius: 10px; background-color: {risk_color}25; border: 1px solid {risk_color};">
                                <h3 style="color: {risk_color};">{risk_info["title"]}</h3>
                                <p>{risk_info["text"]}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Display flood monitoring information
                            st.subheader("Nearby Flood Monitoring Stations")
                            
                            stations = flood_data.get("flood_metrics", {}).get("stations", [])
                            if len(stations) > 0:
                                for i, station in enumerate(stations):
                                    with st.expander(f"{station.get('name', 'Unknown Station')} ({station.get('distance_km', 'Unknown')} km)"):
                                        st.write(f"**River:** {station.get('river', 'Unknown')}")
                                        st.write(f"**Type:** {station.get('type', 'Unknown')}")
                                        st.write(f"**Status:** {station.get('status', 'Unknown')}")
                                        
                                        # Show latest reading if available
                                        latest_reading = station.get("latest_reading")
                                        if latest_reading:
                                            st.write("**Latest Reading:**")
                                            st.write(f"- Value: {latest_reading.get('value', 'N/A')} ({latest_reading.get('parameter', 'Unknown Parameter')})")
                                            st.write(f"- Date: {latest_reading.get('date', 'N/A')}")
                            else:
                                st.info("No flood monitoring stations found within the search radius.")
                            
                            # Display active flood warnings
                            st.subheader("Active Flood Warnings")
                            
                            warnings = flood_data.get("flood_warnings", {}).get("warnings", [])
                            if len(warnings) > 0:
                                for warning in warnings:
                                    severity = warning.get("severity", "Unknown")
                                    severity_color = {
                                        "Severe Flood Warning": "#FF0000",
                                        "Flood Warning": "#FFA500",
                                        "Flood Alert": "#FFFF00"
                                    }.get(severity, "#2196F3")
                                    
                                    with st.expander(f"{severity} - {warning.get('description', 'No description')}"):
                                        st.write(f"**Area:** {warning.get('area', 'Unknown')}")
                                        st.write(f"**County:** {warning.get('county', 'Unknown')}")
                                        st.write(f"**Message:** {warning.get('message', 'No message')}")
                                        st.write(f"**Issued:** {warning.get('time_raised', 'Unknown')}")
                                        st.write(f"**Updated:** {warning.get('time_updated', 'Unknown')}")
                            else:
                                st.success("No active flood warnings for this area.")
                                
                            # Display flood risk guidance
                            st.subheader("Flood Risk Information")
                            
                            st.markdown("""
                            #### What do the flood zones mean?
                            
                            - **Flood Zone 1**: Low probability of flooding
                            - **Flood Zone 2**: Medium probability of flooding
                            - **Flood Zone 3**: High probability of flooding
                            
                            #### Flood Zone 2
                            Land having between a 1 in 100 and 1 in 1,000 annual probability of river flooding; or land having between a 1 in 200 and 1 in 1,000 annual probability of sea flooding.
                            
                            #### Flood Zone 3
                            Land having a 1 in 100 or greater annual probability of river flooding; or Land having a 1 in 200 or greater annual probability of sea flooding.
                            
                            #### What should I do?
                            
                            If your property is in a flood risk area:
                            
                            1. **Check your insurance** - Ensure your property is adequately insured against flood damage
                            2. **Sign up for flood warnings** - The Environment Agency offers a free flood warning service
                            3. **Prepare a flood plan** - Know what to do if flooding occurs
                            4. **Consider property flood resilience measures** - These can help reduce damage if flooding occurs
                            
                            For more information, visit the [Environment Agency website](https://www.gov.uk/check-flood-risk).
                            """)
                else:
                    st.warning("Location coordinates not available for this postcode.")