import csv
import json
import urllib.request
import urllib.parse
import time
import xml.etree.ElementTree as ET
import os

MAPBOX_TOKEN = 'pk.eyJ1IjoiYW5kcmV3LXZpbmNlbnQiLCJhIjoiY202OW4wNm5yMGlubzJtcTJmMnBxb2x1cSJ9.jrR3Ucv9Nvtc-T_7aKIQCg'

def geocode_address(address):
    """Geocode an address using Mapbox API"""
    encoded_address = urllib.parse.quote(address)
    url = f'https://api.mapbox.com/geocoding/v5/mapbox.places/{encoded_address}.json?access_token={MAPBOX_TOKEN}'
    
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read())
            if data['features']:
                coords = data['features'][0]['center']
                return coords[0], coords[1]  # longitude, latitude
    except Exception as e:
        print(f"Error geocoding {address}: {str(e)}")
    return None

def create_kml_header():
    """Create KML file header"""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Style id="preferred">
      <IconStyle>
        <Icon>
          <href>http://maps.google.com/mapfiles/ms/icons/red-dot.png</href>
        </Icon>
      </IconStyle>
    </Style>
    <Style id="other">
      <IconStyle>
        <Icon>
          <href>http://maps.google.com/mapfiles/ms/icons/blue-dot.png</href>
        </Icon>
      </IconStyle>
    </Style>'''

def create_placemark(row, coords):
    """Create a KML placemark for a location"""
    style_id = "preferred" if "preferred" in row['Location Rank'].lower() else "other"
    
    return f'''
    <Placemark>
      <name>{row['Organization']}</name>
      <styleUrl>#{style_id}</styleUrl>
      <description><![CDATA[
        <h3>{row['Organization']}</h3>
        <p><strong>Address:</strong> {row['Address']}</p>
        <p><strong>Region:</strong> {row['Region']}</p>
        {'<p><strong>Tuition:</strong> ' + row['Tuition'] + '</p>' if row['Tuition'] else ''}
        {'<p><strong>Website:</strong> <a href="' + row['Website'] + '" target="_blank">Visit Website</a></p>' if row['Website'] else ''}
        <p><strong>Type:</strong> {row['Location Rank']}</p>
      ]]></description>
      <Point>
        <coordinates>{coords[0]},{coords[1]}</coordinates>
      </Point>
    </Placemark>'''

def parse_existing_kml(kml_file):
    """Parse existing KML file and return a dictionary of locations"""
    if not os.path.exists(kml_file):
        return {}
    
    try:
        tree = ET.parse(kml_file)
        root = tree.getroot()
        
        # Handle namespace in KML
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}
        
        locations = {}
        for placemark in root.findall('.//kml:Placemark', ns):
            name_elem = placemark.find('.//kml:name', ns)
            style_elem = placemark.find('.//kml:styleUrl', ns)
            coords_elem = placemark.find('.//kml:coordinates', ns)
            desc_elem = placemark.find('.//kml:description', ns)
            
            if name_elem is not None and coords_elem is not None:
                name = name_elem.text
                coords = coords_elem.text.strip().split(',')
                style = style_elem.text.replace('#', '') if style_elem is not None else 'other'
                
                # Parse description to extract metadata
                desc = desc_elem.text if desc_elem is not None else ''
                address = region = tuition = website = ''
                
                if desc:
                    # Extract address
                    addr_start = desc.find('<strong>Address:</strong>') + len('<strong>Address:</strong>')
                    addr_end = desc.find('</p>', addr_start)
                    if addr_start > -1 and addr_end > -1:
                        address = desc[addr_start:addr_end].strip()
                    
                    # Extract region
                    reg_start = desc.find('<strong>Region:</strong>') + len('<strong>Region:</strong>')
                    reg_end = desc.find('</p>', reg_start)
                    if reg_start > -1 and reg_end > -1:
                        region = desc[reg_start:reg_end].strip()
                    
                    # Extract Tuition
                    Tuition_start = desc.find('<strong>Tuition:</strong>') + len('<strong>Tuition:</strong>')
                    Tuition_end = desc.find('</p>', Tuition_start)
                    if Tuition_start > -1 and Tuition_end > -1:
                        Tuition = desc[Tuition_start:Tuition_end].strip()
                    
                    # Extract website
                    web_start = desc.find('href="') + len('href="')
                    web_end = desc.find('"', web_start)
                    if web_start > -1 and web_end > -1:
                        website = desc[web_start:web_end].strip()
                
                locations[name] = {
                    'style': style,
                    'coordinates': (float(coords[0]), float(coords[1])),
                    'address': address,
                    'region': region,
                    'Tuition': Tuition,
                    'website': website
                }
        return locations
    except Exception as e:
        print(f"Error parsing KML file {kml_file}: {str(e)}")
        return {}

def should_update_location(row, existing_location):
    """Determine if a location needs to be updated"""
    current_style = "preferred" if "preferred" in row['Location Rank'].lower() else "other"
    existing_style = existing_location['style']
    return current_style != existing_style

def create_kml_files(csv_file, output_preferred):
    """Create KML files from CSV data"""
    # Parse existing KML files
    existing_preferred = parse_existing_kml(output_preferred)
    existing_locations = {**existing_preferred}
    
    preferred_placemarks = []
    
    # First count total rows for progress
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        total_rows = sum(1 for _ in csv.DictReader(f))
    print(f"Found {total_rows} locations to process")
    
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            if not row['Address']:
                print(f"[{i}/{total_rows}] Skipping {row['Organization']} - no address")
                continue
            
            org_name = row['Organization']
            existing_location = existing_locations.get(org_name)
            
            if existing_location and not should_update_location(row, existing_location):
                print(f"[{i}/{total_rows}] Using existing data for: {org_name}")
                # Create placemark with all metadata from CSV
                placemark = create_placemark({
                    'Organization': org_name,
                    'Address': row['Address'],
                    'Region': row['Region'],
                    'Tuition': row['Tuition'],
                    'Website': row['Website'],
                    'Location Rank': 'Preferred' if existing_location['style'] == 'preferred' else 'Other'
                }, existing_location['coordinates'])
                
                if existing_location['style'] == 'preferred':
                    preferred_placemarks.append(placemark)
                else:
                    other_placemarks.append(placemark)
                continue
                
            print(f"[{i}/{total_rows}] {'Updating' if existing_location else 'Geocoding'}: {org_name} ({row['Address']})")
            coords = geocode_address(row['Address'])
            if coords:
                placemark = create_placemark(row, coords)
                if "preferred" in row['Location Rank'].lower():
                    preferred_placemarks.append(placemark)
                    status = "PREFERRED"
                else:
                    status = "OTHER"
                print(f" Successfully processed as {status}: {org_name} at {coords}")
            else:
                print(f" Failed to geocode: {org_name}")
                # If geocoding fails but we have existing data, use it
                if existing_location:
                    print(f"  Using existing coordinates for: {org_name}")
                    placemark = create_placemark({
                        'Organization': org_name,
                        'Address': row['Address'],
                        'Region': row['Region'],
                        'Tuition': row['Tuition'],
                        'Website': row['Website'],
                        'Location Rank': 'Preferred' if existing_location['style'] == 'preferred' else 'Other'
                    }, existing_location['coordinates'])
                    
                    if existing_location['style'] == 'preferred':
                        preferred_placemarks.append(placemark)
                    else:
                        other_placemarks.append(placemark)
            time.sleep(1)  # Rate limiting
    
    print(f"\nCreating KML files...")
    
    # Create preferred locations KML
    with open(output_preferred, 'w', encoding='utf-8') as f:
        f.write(create_kml_header())
        for placemark in preferred_placemarks:
            f.write(placemark)
        f.write('\n  </Document>\n</kml>')

    
    print("KML files created successfully!")
    
if __name__ == "__main__":
    csv_file = "data/other_locations.csv"
    locations_kml = "data/other_locations.kml"



    
    create_kml_files(csv_file, locations_kml)
