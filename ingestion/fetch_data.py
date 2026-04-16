import os
import requests
import pandas as pd
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

# Environment variables
WAQI_API_KEY = os.getenv("WAQI_API_KEY")
OWM_API_KEY = os.getenv("OWM_API_KEY")
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")

CITIES = [
    "New Delhi", "Kolkata", "Mumbai", "Bengaluru", "Chennai", 
    "Hyderabad", "Ahmedabad", "Surat", "Pune", "Lucknow", 
    "Kanpur", "Jaipur", "Indore", "Patna", "Nagpur", 
    "Thiruvananthapuram", "Bhopal", "Chandigarh", "Ludhiana", "Visakhapatnam"
]

def fetch_waqi_data(city):
    """Fetch PM2.5, NO2, O3 from WAQI."""
    url = f"https://api.waqi.info/feed/{urllib.parse.quote(city)}/?token={WAQI_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data.get('status') == 'ok':
            iaqi = data['data'].get('iaqi', {})
            return {
                'pm25': iaqi.get('pm25', {}).get('v'),
                'no2': iaqi.get('no2', {}).get('v'),
                'o3': iaqi.get('o3', {}).get('v')
            }
    return {'pm25': None, 'no2': None, 'o3': None}

def fetch_weather_data(city):
    """Fetch Temp, Humidity, Pressure, Wind from OpenWeatherMap."""
    # We append 'IN' to specify India and aid geocoding accuracy
    url = f"https://api.openweathermap.org/data/2.5/weather?q={urllib.parse.quote(city)},IN&appid={OWM_API_KEY}&units=metric"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        main = data.get('main', {})
        wind = data.get('wind', {})
        weather = data.get('weather', [{}])[0]
        return {
            'temperature': main.get('temp'),
            'humidity': main.get('humidity'),
            'pressure': main.get('pressure'),
            'wind_speed': wind.get('speed'),
            'weather_condition': weather.get('main')
        }
    return {'temperature': None, 'humidity': None, 'pressure': None, 'wind_speed': None, 'weather_condition': None}

def main():
    if not all([WAQI_API_KEY, OWM_API_KEY, SUPABASE_DB_URL]):
        print("Missing API keys or Database URL. Exiting...")
        return

    records = []
    timestamp = datetime.now(timezone.utc)
    
    for city in CITIES:
        waqi_data = fetch_waqi_data(city)
        weather_data = fetch_weather_data(city)
        
        record = {
            'city': city,
            'timestamp': timestamp,
            **waqi_data,
            **weather_data
        }
        records.append(record)

    df = pd.DataFrame(records)
    
    # Establish database connection
    engine = create_engine(SUPABASE_DB_URL)
    
    from sqlalchemy import Table, MetaData
    metadata = MetaData()
    daily_aqi_weather_table = Table('daily_aqi_weather', metadata, autoload_with=engine)
    
    with engine.begin() as conn:
        for idx, row in df.iterrows():
            stmt = insert(daily_aqi_weather_table).values(
                city=row['city'],
                timestamp=row['timestamp'],
                pm25=row['pm25'],
                no2=row['no2'],
                o3=row['o3'],
                temperature=row['temperature'],
                humidity=row['humidity'],
                pressure=row['pressure'],
                wind_speed=row['wind_speed'],
                weather_condition=row['weather_condition']
            )
            stmt = stmt.on_conflict_do_nothing(
                index_elements=['city', 'timestamp']
            )
            conn.execute(stmt)
            
    print(f"Successfully ingested {len(df)} records at {timestamp}.")

if __name__ == '__main__':
    main()
