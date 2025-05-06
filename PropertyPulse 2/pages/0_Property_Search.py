import streamlit as st
import folium
from streamlit_folium import folium_static
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

from utils.postcode_validator import validate_postcode
from services.location_service import get_location_data
from services.property_service import get_house_price_data, get_price_paid_data

# Set page config
st.set_page_config(
    page_title="UK Property Search Dashboard",
    page_icon="🏠",
    layout="wide"
)

# Title and description
st.title("UK Property Search Dashboard")
st.markdown("""
This dashboard provides comprehensive property information by postcode, including:
- Location data
- Interactive map
- House price trends
- Crime statistics (via Crime Map page)
""")

# Create sidebar for search
with st.sidebar:
    st.header("Search Property")
    postcode = st.text_input("Enter UK Postcode:", "").strip().upper()
    search_button = st.button("Search", use_container_width=True)
    
    st.markdown("---")
    
    # Add a note about the Crime Map page
    st.info("Check the Crime Map page in the navigation menu to explore crime statistics by postcode.")
    
    st.markdown("---")
    st.caption("Data sources:")
    st.caption("- UK Land Registry")
    st.caption("- OpenStreetMap")

# Main content area
if not postcode and not search_button:
    # Initial state
    st.info("Enter a UK postcode in the sidebar to get started.")
    
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
        with st.spinner(f"Fetching data for {formatted_postcode}..."):
            # Fetch location data
            location_data = get_location_data(formatted_postcode)
            
            if "error" in location_data:
                st.error(f"Error fetching location data: {location_data['error']}")
            else:
                # Display location information
                st.subheader("Location Information")
                
                # Create columns for basic info
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Postcode:** {formatted_postcode}")
                    st.write(f"**Region:** {location_data.get('region', 'N/A')}")
                    st.write(f"**District:** {location_data.get('admin_district', 'N/A')}")
                
                with col2:
                    st.write(f"**Country:** {location_data.get('country', 'N/A')}")
                    st.write(f"**Ward:** {location_data.get('admin_ward', 'N/A')}")
                    st.write(f"**Parliamentary Constituency:** {location_data.get('parliamentary_constituency', 'N/A')}")
                
                # Create a map centered on the postcode
                st.subheader("Location Map")
                
                if 'latitude' in location_data and 'longitude' in location_data:
                    try:
                        m = folium.Map(
                            location=[location_data['latitude'], location_data['longitude']],
                            zoom_start=15
                        )
                        
                        # Add a marker for the postcode
                        folium.Marker(
                            [location_data['latitude'], location_data['longitude']],
                            popup=formatted_postcode,
                            tooltip=formatted_postcode,
                            icon=folium.Icon(color="red", icon="home")
                        ).add_to(m)
                        
                        # Display the map
                        folium_static(m)
                    except Exception as e:
                        st.error(f"Error displaying map: {str(e)}")
                else:
                    st.warning("Location coordinates not available for this postcode.")
                
                # Fetch and display property price data
                st.subheader("Property Price Information")
                
                property_data = get_house_price_data(formatted_postcode, location_data.get('admin_district', '').lower())
                
                if "error" in property_data:
                    st.error(f"Error fetching property data: {property_data['error']}")
                else:
                    # Display current average price
                    price_col1, price_col2 = st.columns(2)
                    
                    with price_col1:
                        avg_price = property_data.get('current_average_price', 'N/A')
                        if avg_price != 'N/A':
                            avg_price = f"£{avg_price:,.0f}"
                        st.metric("Current Average Price", avg_price)
                        
                    with price_col2:
                        yearly_change = property_data.get('yearly_change_percentage', 'N/A')
                        if yearly_change != 'N/A':
                            yearly_change = f"{yearly_change:.1f}%"
                        st.metric("Yearly Change", yearly_change)
                    
                    # Display property price trends for the county/region
                    if 'price_data' in property_data and len(property_data['price_data']) > 0:
                        price_data_df = pd.DataFrame(property_data['price_data'])
                        
                        # Get the district name with better fallbacks
                        district = location_data.get('admin_district')
                        if not district or district.lower() == 'not available':
                            district = location_data.get('region', 'England')
                        
                        st.subheader(f"Property Price Trends in {district}")
                        
                        # Check if we have property type data
                        if 'property_type' in price_data_df.columns:
                            # Create a chart of property prices by type over time
                            property_types = sorted(list(set(price_data_df['property_type'])))
                            
                            # Filter to exclude data points without property type
                            valid_data = price_data_df[price_data_df['property_type'].notnull()]
                            
                            if not valid_data.empty:
                                # Create tabs for different graph types
                                price_tab, percent_change_tab = st.tabs(["Average Prices", "Annual Percentage Change"])
                                
                                with price_tab:
                                    # Create line chart showing price trends by property type
                                    fig_price = px.line(
                                        valid_data,
                                        x='date',
                                        y='average_price',
                                        color='property_type',
                                        title=f'Average Price by Property Type in {district} ({(datetime.now() - timedelta(days=3652)).year}-{datetime.now().year})',
                                        labels={
                                            'date': 'Date', 
                                            'average_price': 'Average Price (£)', 
                                            'property_type': 'Property Type'
                                        }
                                    )
                                    
                                    # Format the chart
                                    fig_price.update_layout(
                                        xaxis_title="Date",
                                        yaxis_title="Average Price (£)",
                                        hovermode="x unified",
                                        legend_title="Property Type",
                                        height=500
                                    )
                                    
                                    # Improve the appearance
                                    fig_price.update_traces(
                                        mode="lines",
                                        line=dict(width=2)
                                    )
                                    
                                    # Format y-axis to show pound sign
                                    fig_price.update_layout(
                                        yaxis=dict(
                                            tickprefix="£",
                                            separatethousands=True
                                        )
                                    )
                                    
                                    # Show the chart
                                    st.plotly_chart(fig_price, use_container_width=True)
                                
                                with percent_change_tab:
                                    # Check if percentage annual change data is available
                                    if 'percentage_annual_change' in valid_data.columns:
                                        # Filter to show only data with percentage change values
                                        pct_change_data = valid_data[valid_data['percentage_annual_change'].notnull()]
                                        
                                        if not pct_change_data.empty:
                                            # Create line chart showing percentage change trends by property type
                                            fig_pct = px.line(
                                                pct_change_data,
                                                x='date',
                                                y='percentage_annual_change',
                                                color='property_type',
                                                title=f'Yearly Price Change (%) by Property Type in {district} ({(datetime.now() - timedelta(days=3652)).year}-{datetime.now().year})',
                                                labels={
                                                    'date': 'Date', 
                                                    'percentage_annual_change': 'Annual Change (%)', 
                                                    'property_type': 'Property Type'
                                                }
                                            )
                                            
                                            # Format the chart
                                            fig_pct.update_layout(
                                                xaxis_title="Date",
                                                yaxis_title="Annual Change (%)",
                                                hovermode="x unified",
                                                legend_title="Property Type",
                                                height=500
                                            )
                                            
                                            # Improve the appearance
                                            fig_pct.update_traces(
                                                mode="lines",
                                                line=dict(width=2)
                                            )
                                            
                                            # Add a reference line at y=0
                                            fig_pct.add_hline(
                                                y=0, 
                                                line_dash="dash", 
                                                line_color="gray",
                                                annotation_text="No change",
                                                annotation_position="bottom right"
                                            )
                                            
                                            # Format y-axis to show percentage
                                            fig_pct.update_layout(
                                                yaxis=dict(
                                                    ticksuffix="%"
                                                )
                                            )
                                            
                                            # Show the chart
                                            st.plotly_chart(fig_pct, use_container_width=True)
                                        else:
                                            st.warning("No percentage change data available for this region.")
                                    else:
                                        st.warning("Percentage change data not available in the dataset.")
                                
                                # Show the latest price data in a table
                                st.subheader("Latest Average Prices by Property Type (with Year-over-Year Change)")
                                
                                # Get the most recent date in the data
                                latest_date = max(pd.to_datetime(valid_data['date']))
                                
                                # Filter to just the most recent data
                                latest_data = valid_data[pd.to_datetime(valid_data['date']).dt.date >= (latest_date.date() - timedelta(days=90))]
                                
                                # Group by property type and get the latest price and percentage change for each
                                latest_prices = latest_data.groupby('property_type').agg({
                                    'average_price': 'mean',
                                    'percentage_annual_change': 'last'
                                }).reset_index()
                                
                                # Filter out 'Average' property type
                                latest_prices = latest_prices[latest_prices['property_type'] != 'Average']
                                
                                # Format the values
                                latest_prices['average_price'] = latest_prices['average_price'].apply(lambda x: f"£{int(x):,}")
                                latest_prices['percentage_annual_change'] = latest_prices['percentage_annual_change'].apply(lambda x: f"YoY Change: {x:+.1f}%" if pd.notnull(x) else "N/A")
                                
                                # Display in columns with fixed number
                                cols = st.columns(4)  # Fixed number of columns
                                for i, row in latest_prices.iterrows():
                                    with cols[i % 4]:  # Use modulo to wrap around columns
                                        st.metric(
                                            row['property_type'], 
                                            row['average_price'],
                                            row['percentage_annual_change'] if row['percentage_annual_change'] != 'N/A' else None
                                        )
                                
                            else:
                                st.warning("No property type price data available for this region.")
                        else:
                            # If property type data isn't available, show overall price trend
                            fig = px.line(
                                price_data_df, 
                                x='date', 
                                y='average_price',
                                title=f'Property Price Trends in {district}',
                                labels={'date': 'Date', 'average_price': 'Average Price (£)'}
                            )
                            fig.update_layout(
                                xaxis_title="Date",
                                yaxis_title="Average Price (£)",
                                hovermode="x unified"
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        
                        # Display data table
                        with st.expander("View Price Data Table"):
                            # Determine what data to display
                            display_df = None
                            
                            if 'property_type' in price_data_df.columns:
                                if 'filtered_df' in locals() and not locals()['filtered_df'].empty:
                                    display_df = locals()['filtered_df'].copy()
                                else:
                                    display_df = price_data_df.copy()
                            else:
                                display_df = price_data_df.copy()
                            
                            # Format the price column
                            display_df['average_price'] = display_df['average_price'].apply(lambda x: f"£{x:,.0f}")
                            
                            # Determine which columns to show
                            if 'property_type' in display_df.columns and 'bedrooms' in display_df.columns:
                                column_config = {
                                    "date": "Date",
                                    "average_price": "Average Price",
                                    "property_type": "Property Type",
                                    "bedrooms": "Bedrooms"
                                }
                            else:
                                column_config = {
                                    "date": "Date",
                                    "average_price": "Average Price"
                                }
                            
                            st.dataframe(
                                display_df,
                                column_config=column_config,
                                hide_index=True
                            )
                    else:
                        st.warning("No price trend data available for this area.")

# Footer
# Add Property Sales History section
                st.subheader("Property Sales History")
                price_paid_data = get_price_paid_data(formatted_postcode)
                
                if "error" in price_paid_data:
                    st.error(f"Error fetching price paid data: {price_paid_data['error']}")
                else:
                    transactions = price_paid_data.get("transactions", [])
                    if transactions:
                        # Group transactions by SAON (secondary address)
                        sales_by_property = {}
                        for t in transactions:
                            key = f"{t['saon']}_{t['paon']}_{t['street']}"
                            if key not in sales_by_property:
                                sales_by_property[key] = []
                            sales_by_property[key].append(t)
                        
                        # Calculate profit/loss for properties with multiple sales
                        for property_key, sales in sales_by_property.items():
                            if len(sales) > 1:
                                sales.sort(key=lambda x: x['date'])
                                
                                # Create an expander for each property
                                property_str = f"{sales[0]['saon']} {sales[0]['paon']} {sales[0]['street']}".strip()
                                if not property_str:
                                    property_str = "Unknown Property"
                                    
                                with st.expander(f"Sales History: {property_str}"):
                                    # Create a DataFrame for all sales
                                    df = pd.DataFrame(sales)
                                    df['amount'] = df['amount'].apply(lambda x: f"£{x:,.0f}")
                                    st.dataframe(
                                        df[['date', 'amount', 'category']],
                                        column_config={
                                            "date": "Sale Date",
                                            "amount": "Price",
                                            "category": "Category"
                                        },
                                        hide_index=True
                                    )
                                    
                                    # Calculate and display profit/loss
                                    first_sale = sales[0]
                                    last_sale = sales[-1]
                                    price_diff = last_sale['amount'] - first_sale['amount']
                                    price_diff_pct = (price_diff / first_sale['amount']) * 100
                                    
                                    years_diff = (datetime.strptime(last_sale['date'], '%Y-%m-%d') - 
                                                datetime.strptime(first_sale['date'], '%Y-%m-%d')).days / 365.25
                                    
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.metric(
                                            "Total Profit/Loss",
                                            f"£{price_diff:,.0f}",
                                            f"{price_diff_pct:+.1f}%"
                                        )
                                    with col2:
                                        annual_return = (price_diff_pct / years_diff) if years_diff > 0 else 0
                                        st.metric(
                                            "Average Annual Return",
                                            f"{annual_return:+.1f}%"
                                        )
                                    with col3:
                                        st.metric(
                                            "Years Held",
                                            f"{years_diff:.1f}"
                                        )
                    else:
                        st.info("No sales history found for this postcode.")

st.markdown("---")
st.caption("© 2023 UK Property Search Dashboard | Data sources: UK Land Registry, OpenStreetMap, Police UK Data API")
