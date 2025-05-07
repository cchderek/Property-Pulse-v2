from utils.data_fetcher import get_json_data
import pandas as pd
from datetime import datetime, timedelta
import calendar
import requests
import io
from urllib.parse import quote

def get_price_paid_data(postcode):
    """
    Fetches price paid data for properties in a specific postcode.
    
    Args:
        postcode (str): The full postcode to search for
        
    Returns:
        dict: Price paid data including transaction details
    """
    try:
        endpoint_url = "https://landregistry.data.gov.uk/landregistry/query"
        
        sparql_query = f"""
        prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        prefix owl: <http://www.w3.org/2002/07/owl#>
        prefix xsd: <http://www.w3.org/2001/XMLSchema#>
        prefix sr: <http://data.ordnancesurvey.co.uk/ontology/spatialrelations/>
        prefix ukhpi: <http://landregistry.data.gov.uk/def/ukhpi/>
        prefix lrppi: <http://landregistry.data.gov.uk/def/ppi/>
        prefix skos: <http://www.w3.org/2004/02/skos/core#>
        prefix lrcommon: <http://landregistry.data.gov.uk/def/common/>

        SELECT ?paon ?saon ?street ?town ?county ?postcode ?amount ?date ?category
        WHERE {{
            VALUES ?postcode {{"{postcode}"^^xsd:string}}

            ?addr lrcommon:postcode ?postcode.

            ?transx lrppi:propertyAddress ?addr ;
                    lrppi:pricePaid ?amount ;
                    lrppi:transactionDate ?date ;
                    lrppi:transactionCategory/skos:prefLabel ?category.

            OPTIONAL {{?addr lrcommon:county ?county}}
            OPTIONAL {{?addr lrcommon:paon ?paon}}
            OPTIONAL {{?addr lrcommon:saon ?saon}}
            OPTIONAL {{?addr lrcommon:street ?street}}
            OPTIONAL {{?addr lrcommon:town ?town}}
        }}
        ORDER BY ?date
        """

        headers = {
            'Accept': 'application/sparql-results+json',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        params = {
            'query': sparql_query
        }

        response = requests.post(endpoint_url, headers=headers, data=params)

        if response.status_code != 200:
            return {"error": f"SPARQL query failed with status code: {response.status_code}"}

        data = response.json()

        if 'results' not in data or 'bindings' not in data['results']:
            return {"error": "No price paid data found"}

        transactions = []
        for result in data['results']['bindings']:
            transaction = {
                'paon': result.get('paon', {}).get('value', ''),
                'saon': result.get('saon', {}).get('value', ''),
                'street': result.get('street', {}).get('value', ''),
                'town': result.get('town', {}).get('value', ''),
                'county': result.get('county', {}).get('value', ''),
                'amount': float(result.get('amount', {}).get('value', 0)),
                'date': result.get('date', {}).get('value', '').split('T')[0],
                'category': result.get('category', {}).get('value', '')
            }
            transactions.append(transaction)

        return {"transactions": transactions}

    except Exception as e:
        return {"error": f"Failed to get price paid data: {str(e)}"}

def get_house_price_data(postcode, outcode=None):
    """
    Fetches house price data for a UK postcode from the UK House Price Index.

    Args:
        postcode (str): The full postcode
        outcode (str): The outcode part of the postcode (e.g., SW1A for SW1A 1AA)

    Returns:
        dict: House price data including current average, trends, etc.
    """
    # Get UK HPI data using the outcode or first part of postcode
    area_code = outcode if outcode else postcode.split(' ')[0]
    return get_uk_house_price_index(area_code)

def get_uk_house_price_index(area_code):
    """
    Gets UK House Price Index data for a specific area.
    This is official data from HM Land Registry, published monthly.

    Args:
        area_code (str): The area code or outcode to search for

    Returns:
        dict: UK house price data
    """
    try:
        # The UK House Price Index API is available through the Land Registry
        # We'll use the SPARQL endpoint to query the data
        endpoint_url = "https://landregistry.data.gov.uk/landregistry/query"

        # Create a SPARQL query to get HPI data for the region
        # This is based on the UK Land Registry's official documentation
        sparql_query = f"""
        PREFIX  op:   <http://environment.data.gov.uk/reference/def/op/>
        PREFIX  rt:   <http://environment.data.gov.uk/flood-monitoring/def/core/>
        PREFIX  owl:  <http://www.w3.org/2002/07/owl#>
        PREFIX  ppd:  <http://landregistry.data.gov.uk/def/ppi/>
        PREFIX  xsd:  <http://www.w3.org/2001/XMLSchema#>
        PREFIX  skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX  ukhpi: <http://landregistry.data.gov.uk/def/ukhpi/>
        PREFIX  rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX  geo:  <http://www.w3.org/2003/01/geo/wgs84_pos#>
        PREFIX  core: <http://environment.data.gov.uk/reference/def/core/>
        PREFIX  dct:  <http://purl.org/dc/terms/>
        PREFIX  rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX  lrcommon: <http://landregistry.data.gov.uk/def/common/>
        PREFIX  api:  <http://purl.org/linked-data/api/vocab#>
        PREFIX  admingeo: <http://data.ordnancesurvey.co.uk/ontology/admingeo/>
        PREFIX  sr:   <http://data.ordnancesurvey.co.uk/ontology/spatialrelations/>

        SELECT ?refRegion ?refMonth 
               ?averagePrice ?percentageAnnualChange
               ?averagePriceDetached ?percentageAnnualChangeDetached
               ?averagePriceSemiDetached ?percentageAnnualChangeSemiDetached
               ?averagePriceTerraced ?percentageAnnualChangeTerraced
               ?averagePriceFlatMaisonette ?percentageAnnualChangeFlatMaisonette
        WHERE {{
          ?id rdf:type ukhpi:MonthlyIndicesByRegion .
          ?id ukhpi:refMonth ?refMonth

          FILTER (?refMonth <= "{datetime.now().strftime('%Y-%m')}"^^xsd:gYearMonth)
          FILTER (?refMonth >= "{(datetime.now() - timedelta(days=3652)).strftime('%Y-%m')}"^^xsd:gYearMonth)

          ?id ukhpi:refRegion ?refRegion

          # Match only district data
          FILTER(CONTAINS(LCASE(str(?refRegion)), LCASE("{area_code}"))
                 || CONTAINS(LCASE(str(?refRegion)), LCASE("{area_code.replace('-', ' ')}"))
                 || CONTAINS(LCASE(str(?refRegion)), LCASE("{area_code.replace(' ', '-')}"))
                 || CONTAINS(LCASE(str(?refRegion)), LCASE("{area_code.lower()}")))

          # Price data and yearly percentage changes
          OPTIONAL {{ ?id ukhpi:averagePrice ?averagePrice }}
          OPTIONAL {{ ?id ukhpi:percentageAnnualChange ?percentageAnnualChange }}
          
          OPTIONAL {{ ?id ukhpi:averagePriceDetached ?averagePriceDetached }}
          OPTIONAL {{ ?id ukhpi:percentageAnnualChangeDetached ?percentageAnnualChangeDetached }}
          
          OPTIONAL {{ ?id ukhpi:averagePriceSemiDetached ?averagePriceSemiDetached }}
          OPTIONAL {{ ?id ukhpi:percentageAnnualChangeSemiDetached ?percentageAnnualChangeSemiDetached }}
          
          OPTIONAL {{ ?id ukhpi:averagePriceTerraced ?averagePriceTerraced }}
          OPTIONAL {{ ?id ukhpi:percentageAnnualChangeTerraced ?percentageAnnualChangeTerraced }}
          
          OPTIONAL {{ ?id ukhpi:averagePriceFlatMaisonette ?averagePriceFlatMaisonette }}
          OPTIONAL {{ ?id ukhpi:percentageAnnualChangeFlatMaisonette ?percentageAnnualChangeFlatMaisonette }}
        }}
        ORDER BY ASC(?refMonth)
        """

        headers = {
            'Accept': 'application/sparql-results+json',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        params = {
            'query': sparql_query
        }

        response = requests.post(endpoint_url, headers=headers, data=params)

        if response.status_code != 200:
            return {"error": f"SPARQL query failed with status code: {response.status_code}"}

        data = response.json()

        if 'results' not in data or 'bindings' not in data['results'] or len(data['results']['bindings']) == 0:
            return {"error": "No house price index data found"}

        hpi_data = data['results']['bindings']
        price_data = []

        region_name = "England"
        if hpi_data and 'refRegion' in hpi_data[0]:
            region_uri = hpi_data[0]['refRegion']['value']
            if 'region/' in region_uri:
                region_name = region_uri.split('region/')[1].replace('-', ' ').title()

        property_types = ["Detached", "Semi-detached", "Terraced", "Flat/Maisonette"]

        for entry in hpi_data:
            date_str = entry.get('refMonth', {}).get('value', '')

            # Extract price data
            average_price = float(entry.get('averagePrice', {}).get('value', 0)) if 'averagePrice' in entry else 0
            detached_price = float(entry.get('averagePriceDetached', {}).get('value', 0)) if 'averagePriceDetached' in entry else 0
            semi_detached_price = float(entry.get('averagePriceSemiDetached', {}).get('value', 0)) if 'averagePriceSemiDetached' in entry else 0
            terraced_price = float(entry.get('averagePriceTerraced', {}).get('value', 0)) if 'averagePriceTerraced' in entry else 0
            flat_price = float(entry.get('averagePriceFlatMaisonette', {}).get('value', 0)) if 'averagePriceFlatMaisonette' in entry else 0
            
            # Extract percentage annual change data
            average_pct_change = float(entry.get('percentageAnnualChange', {}).get('value', 0)) if 'percentageAnnualChange' in entry else None
            detached_pct_change = float(entry.get('percentageAnnualChangeDetached', {}).get('value', 0)) if 'percentageAnnualChangeDetached' in entry else None
            semi_detached_pct_change = float(entry.get('percentageAnnualChangeSemiDetached', {}).get('value', 0)) if 'percentageAnnualChangeSemiDetached' in entry else None
            terraced_pct_change = float(entry.get('percentageAnnualChangeTerraced', {}).get('value', 0)) if 'percentageAnnualChangeTerraced' in entry else None
            flat_pct_change = float(entry.get('percentageAnnualChangeFlatMaisonette', {}).get('value', 0)) if 'percentageAnnualChangeFlatMaisonette' in entry else None

            try:
                date_obj = datetime.strptime(date_str, '%Y-%m')
                formatted_date = date_obj.strftime('%Y-%m-%d')
            except:
                formatted_date = f"{date_str}-01" if '-' in date_str else date_str

            # Add average price data
            if average_price > 0:
                existing_entry = next(
                    (item for item in price_data 
                     if item['date'] == formatted_date 
                     and item['property_type'] == 'Average'
                     and item['average_price'] != round(average_price)), 
                    None
                )
                if not existing_entry:
                    entry_data = {
                        'date': formatted_date,
                        'average_price': round(average_price),
                        'property_type': 'Average'
                    }
                    # Add percentage change if available
                    if average_pct_change is not None:
                        entry_data['percentage_annual_change'] = round(average_pct_change, 2)
                    price_data.append(entry_data)

            # Add detached price data
            if detached_price > 0:
                existing_entry = next(
                    (item for item in price_data 
                     if item['date'] == formatted_date 
                     and item['property_type'] == 'Detached'
                     and item['average_price'] != round(detached_price)), 
                    None
                )
                if not existing_entry:
                    entry_data = {
                        'date': formatted_date,
                        'average_price': round(detached_price),
                        'property_type': 'Detached'
                    }
                    # Add percentage change if available
                    if detached_pct_change is not None:
                        entry_data['percentage_annual_change'] = round(detached_pct_change, 2)
                    price_data.append(entry_data)

            # Add semi-detached price data
            if semi_detached_price > 0:
                existing_entry = next(
                    (item for item in price_data 
                     if item['date'] == formatted_date 
                     and item['property_type'] == 'Semi-detached'
                     and item['average_price'] != round(semi_detached_price)), 
                    None
                )
                if not existing_entry:
                    entry_data = {
                        'date': formatted_date,
                        'average_price': round(semi_detached_price),
                        'property_type': 'Semi-detached'
                    }
                    # Add percentage change if available
                    if semi_detached_pct_change is not None:
                        entry_data['percentage_annual_change'] = round(semi_detached_pct_change, 2)
                    price_data.append(entry_data)

            # Add terraced price data
            if terraced_price > 0:
                existing_entry = next(
                    (item for item in price_data 
                     if item['date'] == formatted_date 
                     and item['property_type'] == 'Terraced'
                     and item['average_price'] != round(terraced_price)), 
                    None
                )
                if not existing_entry:
                    entry_data = {
                        'date': formatted_date,
                        'average_price': round(terraced_price),
                        'property_type': 'Terraced'
                    }
                    # Add percentage change if available
                    if terraced_pct_change is not None:
                        entry_data['percentage_annual_change'] = round(terraced_pct_change, 2)
                    price_data.append(entry_data)

            # Add flat/maisonette price data
            if flat_price > 0:
                existing_entry = next(
                    (item for item in price_data 
                     if item['date'] == formatted_date 
                     and item['property_type'] == 'Flat/Maisonette'
                     and item['average_price'] != round(flat_price)), 
                    None
                )
                if not existing_entry:
                    entry_data = {
                        'date': formatted_date,
                        'average_price': round(flat_price),
                        'property_type': 'Flat/Maisonette'
                    }
                    # Add percentage change if available
                    if flat_pct_change is not None:
                        entry_data['percentage_annual_change'] = round(flat_pct_change, 2)
                    price_data.append(entry_data)

        if price_data:
            recent_date = max([datetime.strptime(item['date'], '%Y-%m-%d') for item in price_data 
                             if item['property_type'] == 'Average'])
            recent_date_str = recent_date.strftime('%Y-%m-%d')

            year_ago_date = (recent_date - timedelta(days=365))
            year_ago_date_str = year_ago_date.strftime('%Y-%m-%d')

            average_recent = next((item['average_price'] for item in price_data 
                                 if item['date'] == recent_date_str and item['property_type'] == 'Average'), 0)

            average_entries = [item for item in price_data if item['property_type'] == 'Average']
            dates = [datetime.strptime(item['date'], '%Y-%m-%d') for item in average_entries]
            closest_year_ago = min(dates, key=lambda d: abs(d - year_ago_date)) if dates else None

            if closest_year_ago:
                year_ago_date_str = closest_year_ago.strftime('%Y-%m-%d')
                average_year_ago = next((item['average_price'] for item in price_data 
                                       if item['date'] == year_ago_date_str and item['property_type'] == 'Average'), 0)

                if average_year_ago > 0:
                    yearly_change_percentage = ((average_recent - average_year_ago) / average_year_ago) * 100
                else:
                    yearly_change_percentage = None
            else:
                yearly_change_percentage = None

            return {
                "current_average_price": round(average_recent) if average_recent > 0 else None,
                "yearly_change_percentage": yearly_change_percentage,
                "price_data": price_data,
                "property_types": property_types + ["Average"],
                "region_name": region_name
            }

        return {"error": "No valid house price data found"}

    except Exception as e:
        return {"error": f"Failed to get UK House Price Index data: {str(e)}"}