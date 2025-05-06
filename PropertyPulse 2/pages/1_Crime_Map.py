import streamlit as st
import folium
from streamlit_folium import folium_static
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import calendar
import json
from folium.plugins import MarkerCluster, HeatMap

from utils.postcode_validator import validate_postcode
from services.location_service import get_location_data
from services.crime_service import get_crime_data, get_crime_categories, get_last_year_monthly_data

# Set page config
st.set_page_config(
    page_title="UK Crime Map",
    page_icon="🚓",
    layout="wide"
)

# Title and description
st.title("UK Crime Map")
st.markdown("""
This page shows crime statistics around UK postcodes, including:
- Interactive crime heatmap
- Crime type breakdown
- Monthly trends over the past year
""")

# Function to create a crime map
def create_crime_map(location_data, crime_data, radius=1):
    """
    Creates a folium map with crime data visualization.
    
    Args:
        location_data (dict): Location data for the center point
        crime_data (list): List of crime incidents
        radius (float): Search radius in kilometers
        
    Returns:
        folium.Map: Map with crime data visualization
    """
    # Create base map
    m = folium.Map(
        location=[location_data['latitude'], location_data['longitude']],
        zoom_start=15
    )
    
    # Add a marker for the postcode
    folium.Marker(
        [location_data['latitude'], location_data['longitude']],
        popup=location_data['postcode'],
        tooltip=location_data['postcode'],
        icon=folium.Icon(color="blue", icon="home")
    ).add_to(m)
    
    # Add a circle to show the search radius
    folium.Circle(
        location=[location_data['latitude'], location_data['longitude']],
        radius=radius * 1609.34,  # Convert km to meters (1 mile = 1609.34 meters)
        color='blue',
        fill=True,
        fill_opacity=0.1
    ).add_to(m)
    
    # Group the markers for better performance
    marker_cluster = MarkerCluster().add_to(m)
    
    # Add crime markers (limit to 1000 to prevent performance issues)
    displayed_count = 0
    max_markers = 1000
    
    for crime in crime_data:
        if displayed_count >= max_markers:
            break
            
        if crime.get('location') and crime['location'].get('latitude') and crime['location'].get('longitude'):
            try:
                # Get details for popup
                category = crime.get('category', 'Unknown').replace('-', ' ').title()
                month = crime.get('month', 'Unknown')
                street = crime.get('location', {}).get('street', {}).get('name', 'Unknown location')
                outcome = crime.get('outcome_status', {})
                outcome_text = outcome.get('category', 'No outcome recorded') if outcome else 'No outcome recorded'
                outcome_date = outcome.get('date', '') if outcome else ''
                
                # Create popup content
                popup_html = f"""
                <div style='width: 200px'>
                    <b>Crime Type:</b> {category}<br>
                    <b>Date:</b> {month}<br>
                    <b>Location:</b> {street}<br>
                    <b>Outcome:</b> {outcome_text}<br>
                    {f"<b>Outcome Date:</b> {outcome_date}" if outcome_date else ""}
                </div>
                """
                
                # Determine color based on category
                colors = {
                    'Anti Social Behaviour': 'blue',
                    'Bicycle Theft': 'lightblue',
                    'Burglary': 'red',
                    'Criminal Damage Arson': 'darkred',
                    'Drugs': 'purple',
                    'Other Theft': 'orange',
                    'Possession Of Weapons': 'darkpurple',
                    'Public Order': 'pink',
                    'Robbery': 'darkred',
                    'Shoplifting': 'beige',
                    'Theft From The Person': 'orange',
                    'Vehicle Crime': 'lightred',
                    'Violent Crime': 'darkred',
                    'Other Crime': 'gray'
                }
                
                category_clean = category.lower().replace(' ', '-')
                color = 'cadetblue'  # Default color
                
                # Find the closest match for the category
                for key in colors:
                    if key.lower().replace(' ', '-') in category_clean:
                        color = colors[key]
                        break
                
                # Add the marker to the cluster
                folium.Marker(
                    location=[float(crime['location']['latitude']), float(crime['location']['longitude'])],
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=category,
                    icon=folium.Icon(color=color, icon="info-sign")
                ).add_to(marker_cluster)
                
                displayed_count += 1
            except (ValueError, TypeError) as e:
                # Skip any markers with invalid coordinates
                continue
    
    # Add a heat map layer for density visualization (using all crime data)
    heat_data = []
    for crime in crime_data:
        if crime.get('location') and crime['location'].get('latitude') and crime['location'].get('longitude'):
            try:
                heat_data.append([
                    float(crime['location']['latitude']), 
                    float(crime['location']['longitude']),
                    1  # Intensity value
                ])
            except (ValueError, TypeError):
                # Skip invalid coordinates
                continue
    
    if heat_data:
        HeatMap(heat_data, radius=15).add_to(m)
    
    return m

# Create sidebar for search options
with st.sidebar:
    st.header("Search Crime Data")
    postcode = st.text_input("Enter UK Postcode:", "").strip().upper()
    
    radius = st.slider("Search Radius (km)", min_value=0.5, max_value=5.0, value=1.0, step=0.5)
    
    # Date selection (last 6 months + all option)
    today = datetime.now()
    months = []
    # Add option for all data
    months.append(("", "All data (last 12 months)"))
    
    # Add the last 12 months as options
    for i in range(12):
        # Calculate month by subtracting months properly
        year = today.year
        month = today.month - i
        
        # Adjust year if we go into previous year
        while month <= 0:
            month += 12
            year -= 1
            
        # Create date for first of the month
        month_date = datetime(year, month, 1)
        date_str = f"{month_date.year}-{month_date.month:02d}"
        display_str = f"{calendar.month_name[month_date.month]} {month_date.year}"
        # Only add if not already in the list
        if not any(date_str == m[0] for m in months):
            months.append((date_str, display_str))
    
    selected_date = st.selectbox(
        "Select Month:",
        options=[m[0] for m in months],
        format_func=lambda x: next((m[1] for m in months if m[0] == x), x),
        index=0
    )
    
    search_button = st.button("Search", use_container_width=True)
    
    st.markdown("---")
    st.caption("Data source:")
    st.caption("- Police UK Data API")

# Main content area
if not postcode and not search_button:
    # Initial state
    st.info("Enter a UK postcode in the sidebar to view crime data.")
    
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
        with st.spinner(f"Fetching crime data for {formatted_postcode}..."):
            # Fetch location data
            location_data = get_location_data(formatted_postcode)
            
            if "error" in location_data:
                st.error(f"Error fetching location data: {location_data['error']}")
            else:
                # Display location information
                st.subheader(f"Crime Data for {formatted_postcode}")
                st.write(f"Area: {location_data.get('admin_district', 'N/A')}, {location_data.get('region', 'N/A')}")
                
                if 'latitude' in location_data and 'longitude' in location_data:
                    # Fetch crime data
                    crime_data = get_crime_data(
                        location_data['latitude'], 
                        location_data['longitude'],
                        radius=radius,
                        date=selected_date
                    )
                    
                    if isinstance(crime_data, dict) and "error" in crime_data:
                        st.error(f"Error fetching crime data: {crime_data['error']}")
                    else:
                        # Create tabs for different views
                        map_tab, stats_tab, trends_tab = st.tabs(["Crime Map", "Crime Statistics", "Monthly Trends"])
                        
                        with map_tab:
                            # Display stats
                            total_crimes = len(crime_data)
                            if selected_date:
                                st.write(f"Found **{total_crimes}** crimes within {radius}km radius in {months[0][1] if selected_date == months[0][0] else next((m[1] for m in months if m[0] == selected_date), selected_date)}")
                            else:
                                st.write(f"Found **{total_crimes}** crimes within {radius}km radius over the last 12 months")
                            
                            # Create and display crime map
                            if crime_data:
                                try:
                                    crime_map = create_crime_map(location_data, crime_data, radius)
                                    folium_static(crime_map)
                                except Exception as e:
                                    st.error(f"Error displaying crime map: {str(e)}")
                            else:
                                st.info("No crime data found for this location and time period.")
                        
                        with stats_tab:
                            if crime_data:
                                # Convert crime data to DataFrame for analysis
                                crimes_df = pd.DataFrame(crime_data)
                                
                                # Display crime type breakdown
                                st.subheader("Crime Type Breakdown")
                                
                                if 'category' in crimes_df.columns:
                                    # Clean category names for display
                                    crimes_df['category_display'] = crimes_df['category'].apply(
                                        lambda x: x.replace('-', ' ').title()
                                    )
                                    
                                    # Count crimes by category
                                    crime_counts = crimes_df['category_display'].value_counts().reset_index()
                                    crime_counts.columns = ['Crime Type', 'Count']
                                    
                                    # Calculate percentages
                                    crime_counts['Percentage'] = crime_counts['Count'] / crime_counts['Count'].sum() * 100
                                    
                                    # Create two columns
                                    col1, col2 = st.columns([3, 2])
                                    
                                    with col1:
                                        # Create pie chart
                                        fig = px.pie(
                                            crime_counts, 
                                            values='Count', 
                                            names='Crime Type',
                                            title='Crime Types by Percentage',
                                            hole=0.4
                                        )
                                        fig.update_traces(textposition='inside', textinfo='percent+label')
                                        st.plotly_chart(fig, use_container_width=True)
                                    
                                    with col2:
                                        # Show table with numbers
                                        st.dataframe(
                                            crime_counts,
                                            column_config={
                                                "Crime Type": st.column_config.TextColumn("Crime Type"),
                                                "Count": st.column_config.NumberColumn("Count"),
                                                "Percentage": st.column_config.NumberColumn(
                                                    "Percentage",
                                                    format="%.1f%%"
                                                )
                                            },
                                            hide_index=True
                                        )
                                    
                                    # Display crime outcomes
                                    st.subheader("Crime Outcomes")
                                    
                                    # Extract outcome data
                                    outcome_data = []
                                    for _, crime in crimes_df.iterrows():
                                        outcome = crime.get('outcome_status', {})
                                        category = outcome.get('category', 'No outcome recorded') if outcome else 'No outcome recorded'
                                        outcome_data.append(category)
                                    
                                    outcomes_df = pd.DataFrame({'Outcome': outcome_data})
                                    outcome_counts = outcomes_df['Outcome'].value_counts().reset_index()
                                    outcome_counts.columns = ['Outcome', 'Count']
                                    outcome_counts['Percentage'] = outcome_counts['Count'] / outcome_counts['Count'].sum() * 100
                                    
                                    # Display outcomes
                                    col1, col2 = st.columns([3, 2])
                                    
                                    with col1:
                                        # Create pie chart
                                        fig = px.pie(
                                            outcome_counts, 
                                            values='Count', 
                                            names='Outcome',
                                            title='Crime Outcomes by Percentage',
                                            hole=0.4
                                        )
                                        fig.update_traces(textposition='inside', textinfo='percent+label')
                                        st.plotly_chart(fig, use_container_width=True)
                                    
                                    with col2:
                                        # Show table with numbers
                                        st.dataframe(
                                            outcome_counts,
                                            column_config={
                                                "Outcome": st.column_config.TextColumn("Outcome"),
                                                "Count": st.column_config.NumberColumn("Count"),
                                                "Percentage": st.column_config.NumberColumn(
                                                    "Percentage",
                                                    format="%.1f%%"
                                                )
                                            },
                                            hide_index=True
                                        )
                                else:
                                    st.warning("Crime category data not available in the dataset.")
                            else:
                                st.info("No crime data found for this location and time period.")
                        
                        with trends_tab:
                            st.subheader("Monthly Crime Trends")
                            
                            with st.spinner("Fetching historical crime data..."):
                                # Get data for the last year
                                monthly_data = get_last_year_monthly_data(
                                    location_data['latitude'], 
                                    location_data['longitude'],
                                    radius=radius
                                )
                                
                                if monthly_data and len(monthly_data) > 0:
                                    # Prepare data for chart
                                    trend_data = []
                                    for month, crimes in monthly_data.items():
                                        # Skip if we got an error response
                                        if isinstance(crimes, dict) and "error" in crimes:
                                            continue
                                            
                                        date_obj = datetime.strptime(month, '%Y-%m')
                                        display_month = date_obj.strftime('%b %Y')
                                        
                                        # Count crimes by category
                                        if crimes:
                                            crimes_df = pd.DataFrame(crimes)
                                            
                                            if 'category' in crimes_df.columns:
                                                # Get all crime counts
                                                total_count = len(crimes)
                                                trend_data.append({
                                                    'Month': display_month,
                                                    'Crime Count': total_count,
                                                    'Month_sort': date_obj  # For sorting
                                                })
                                                
                                                # Get counts by category
                                                categories = crimes_df['category'].value_counts().to_dict()
                                                for category, count in categories.items():
                                                    category_display = category.replace('-', ' ').title()
                                                    trend_data.append({
                                                        'Month': display_month,
                                                        'Crime Category': category_display,
                                                        'Crime Count': count,
                                                        'Month_sort': date_obj  # For sorting
                                                    })
                                    
                                    if trend_data:
                                        # Create DataFrame from trend data
                                        trend_df = pd.DataFrame(trend_data)
                                        
                                        # Sort by date
                                        trend_df = trend_df.sort_values('Month_sort')
                                        
                                        # Create two tabs for different trend views
                                        total_tab, category_tab = st.tabs(["Total Crimes", "By Category"])
                                        
                                        with total_tab:
                                            # Filter to just total counts (entries without Crime Category)
                                            total_df = trend_df[~trend_df['Crime Category'].notna()]
                                            
                                            # Create a line chart of total crimes over time
                                            fig = px.line(
                                                total_df,
                                                x='Month',
                                                y='Crime Count',
                                                title=f'Total Crimes by Month within {radius}km of {formatted_postcode}',
                                                markers=True
                                            )
                                            
                                            st.plotly_chart(fig, use_container_width=True)
                                        
                                        with category_tab:
                                            # Filter to just entries with categories
                                            category_df = trend_df[trend_df['Crime Category'].notna()]
                                            
                                            # Get the top 8 categories
                                            top_categories = category_df.groupby('Crime Category')['Crime Count'].sum().nlargest(8).index.tolist()
                                            filtered_df = category_df[category_df['Crime Category'].isin(top_categories)]
                                            
                                            # Create a line chart by category
                                            fig = px.line(
                                                filtered_df,
                                                x='Month',
                                                y='Crime Count',
                                                color='Crime Category',
                                                title=f'Crime Categories by Month within {radius}km of {formatted_postcode}',
                                                markers=True
                                            )
                                            
                                            st.plotly_chart(fig, use_container_width=True)
                                            
                                    else:
                                        st.warning("Could not process the monthly trend data.")
                                else:
                                    st.warning("Unable to fetch historical crime data for trend analysis.")
                else:
                    st.error("Location coordinates not available for this postcode.")

# Footer
st.markdown("---")
st.caption("© 2023 UK Crime Map | Data source: Police UK Data API")