# PropertyPulse/Home.py

import streamlit as st
# Removed unused imports like folium, pandas, etc. from Home.py

# Set page config - This should ideally be called only once,
# and if Home.py is the main entry point, it's fine here.
# If you run pages directly, each might need its own st.set_page_config.
# For a multi-page app structured with a Home.py and a pages/ folder,
# this call in Home.py typically sets the config for the whole app.
st.set_page_config(
    page_title="UK Property & Location Dashboard",
    page_icon="🏠",
    layout="wide"
)

# Title and description
st.title("UK Property & Location Dashboard")
st.markdown("""
Welcome to the UK Property and Location Dashboard! This application provides comprehensive information about UK locations by postcode, including:

- **Property Information**: Search for property details and price trends.
- **Crime Statistics**: Explore crime data and statistics for UK postcodes.
- **Flood Risk**: View flood zone data and assess flood risk.
- **Transport Information**: Find nearby transport options and station details.
- **Location Data**: View detailed information about UK postcodes.

Use the sidebar navigation or the buttons below to explore different features.
""")

# Main content - Feature showcase
st.header("Dashboard Features")

# Create a 2x2 grid for feature highlights
# Row 1
row1_col1, row1_col2 = st.columns(2)

with row1_col1:
    st.subheader("📊 Property Search")
    st.write("""
    - View detailed property price information.
    - Explore house price trends over time.
    - Compare prices across property types.
    - Analyze yearly price changes.
    """)
    if st.button("Go to Property Search", key="property_search_btn", use_container_width=True):
        st.switch_page("pages/0_Property_Search.py")

with row1_col2:
    st.subheader("🚓 Crime Statistics")
    st.write("""
    - Explore crime data by location.
    - View crime hotspots on interactive maps.
    - Analyze crime type breakdowns.
    - Track monthly crime trends.
    """)
    if st.button("Go to Crime Map", key="crime_map_btn", use_container_width=True):
        st.switch_page("pages/1_Crime_Map.py")

# Add a little space between rows
st.markdown("<br>", unsafe_allow_html=True)

# Row 2
row2_col1, row2_col2 = st.columns(2)

with row2_col1:
    st.subheader("🌊 Flood Risk")
    st.write("""
    - View flood zone maps.
    - Check flood risk by postcode.
    - See Flood Zone 2 and 3 areas.
    - Get flood risk assessment.
    """)
    if st.button("Go to Flood Risk Map", key="flood_risk_btn", use_container_width=True):
        st.switch_page("pages/2_Flood_Risk.py")

with row2_col2:
    st.subheader("🚍 Transport Information")
    st.write("""
    - Discover nearby bus stops and train stations.
    - View transport options on an interactive map.
    - Find underground/metro/tram stations.
    - (Real-time departures not yet available)
    """)
    if st.button("Go to Transport Information", key="transport_info_btn", use_container_width=True):
        st.switch_page("pages/3_Transport_Info.py")


# Add a section for getting started
st.header("Getting Started")
st.write("""
To get started, simply select a feature from the sidebar navigation (if visible) or use the buttons above.
Then enter a UK postcode to retrieve information for that location.
""")

# Example postcodes
st.subheader("Example postcodes to try:")
example_postcodes = ["SW1A 1AA", "E14 9GE", "M1 1AE", "EH1 1YZ", "CF10 1EP", "M1 1RG"]
st.write(", ".join(example_postcodes))

# Footer
st.markdown("---")
st.caption("© 2023-2024 UK Property & Location Dashboard | Data sources include: UK Land Registry, OpenStreetMap, Police UK Data API, Environment Agency APIs, Google Maps Platform APIs")