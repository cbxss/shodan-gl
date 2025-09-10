#!/usr/bin/env python3
import shodan
import pandas as pd
import folium
from folium.plugins import HeatMap

def load_api_key():
    """Load Shodan API key from .env file"""
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('SHODAN_API_KEY='):
                    return line.split('=', 1)[1].strip()
    except FileNotFoundError:
        print("Error: .env file not found")
        return None
    return None

def search_ipcams(api_key, limit=1000):
    """Search for IP cameras using Shodan"""
    api = shodan.Shodan(api_key)
    
    # Search queries for IP cameras
    queries = [
        'webcam',
        'camera',
        'title:"IP Camera"',
        'title:"Network Camera"',
        'title:"Live View"',
        'product:"webcam"',
        'port:8080 camera',
        'port:8081 camera'
    ]
    
    results = []
    
    for query in queries:
        try:
            print(f"Searching for: {query}")
            search_results = api.search(query, limit=min(100, limit))
            
            for result in search_results['matches']:
                if result.get('location') and result['location'].get('latitude') and result['location'].get('longitude'):
                    camera_data = {
                        'ip': result['ip_str'],
                        'port': result['port'],
                        'latitude': result['location']['latitude'],
                        'longitude': result['location']['longitude'],
                        'country': result['location'].get('country_name', 'Unknown'),
                        'city': result['location'].get('city', 'Unknown'),
                        'org': result.get('org', 'Unknown'),
                        'product': result.get('product', 'Unknown'),
                        'query': query
                    }
                    results.append(camera_data)
            
            limit -= len(search_results['matches'])
            if limit <= 0:
                break
                
        except Exception as e:
            print(f"Error searching for {query}: {e}")
            continue
    
    return results

def create_map(camera_data):
    """Create interactive map with IP camera locations"""
    if not camera_data:
        print("No camera data to display")
        return None
    
    df = pd.DataFrame(camera_data)
    
    # Remove duplicates based on IP
    df = df.drop_duplicates(subset=['ip'])
    
    print(f"Found {len(df)} unique IP cameras with location data")
    
    # Create base map centered on mean coordinates
    center_lat = df['latitude'].mean()
    center_lon = df['longitude'].mean()
    
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=2,
        tiles='OpenStreetMap'
    )
    
    # Add markers for each camera
    for _, camera in df.iterrows():
        popup_text = f"""
        <b>IP:</b> {camera['ip']}:{camera['port']}<br>
        <b>Location:</b> {camera['city']}, {camera['country']}<br>
        <b>Org:</b> {camera['org']}<br>
        <b>Product:</b> {camera['product']}<br>
        <b>Query:</b> {camera['query']}
        """
        
        folium.Marker(
            location=[camera['latitude'], camera['longitude']],
            popup=folium.Popup(popup_text, max_width=300),
            tooltip=f"{camera['ip']} - {camera['city']}, {camera['country']}"
        ).add_to(m)
    
    # Add heatmap layer
    heat_data = [[row['latitude'], row['longitude']] for _, row in df.iterrows()]
    HeatMap(heat_data).add_to(m)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    return m, df

def main():
    """Main function"""
    print("Shodan IP Camera Map Generator")
    print("=" * 40)
    
    # Load API key
    api_key = load_api_key()
    if not api_key:
        print("Error: Could not load Shodan API key from .env file")
        return
    
    # Search for IP cameras
    print("Searching for IP cameras...")
    camera_data = search_ipcams(api_key, limit=500)
    
    if not camera_data:
        print("No IP cameras found with location data")
        return
    
    # Create map
    print("Creating map...")
    map_obj, df = create_map(camera_data)
    
    if map_obj:
        # Save map
        map_filename = 'ipcam_map.html'
        map_obj.save(map_filename)
        print(f"Map saved as {map_filename}")
        
        # Save data
        data_filename = 'ipcam_data.csv'
        df.to_csv(data_filename, index=False)
        print(f"Data saved as {data_filename}")
        
        # Print statistics
        print("\nStatistics:")
        print(f"Total cameras found: {len(df)}")
        print(f"Countries: {df['country'].nunique()}")
        print(f"Top countries:")
        print(df['country'].value_counts().head())

if __name__ == "__main__":
    main()