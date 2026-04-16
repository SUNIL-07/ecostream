import os
import requests
import pandas as pd
from datetime import datetime, timezone
from sqlalchemy import create_engine, Table, MetaData
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
    """Fetch all available AQI metrics from WAQI."""
    url = f"https://api.waqi.info/feed/{urllib.parse.quote(city)}/?token={WAQI_API_KEY}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'ok':
                aqi = data['data'].get('aqi')
                iaqi = data['data'].get('iaqi', {})
                return {
                    'aqi': aqi if aqi != '-' else None,
                    'pm25': iaqi.get('pm25', {}).get('v'),
                    'pm10': iaqi.get('pm10', {}).get('v'),
                    'o3': iaqi.get('o3', {}).get('v'),
                    'no2': iaqi.get('no2', {}).get('v'),
                    'so2': iaqi.get('so2', {}).get('v'),
                    'co': iaqi.get('co', {}).get('v')
                }
    except Exception as e:
        print(f"Error fetching WAQI for {city}: {e}")
        
    return {'aqi': None, 'pm25': None, 'pm10': None, 'o3': None, 'no2': None, 'so2': None, 'co': None}

def fetch_weather_data(city):
    """Fetch granular Weather metrics from OpenWeatherMap."""
    url = f"https://api.openweathermap.org/data/2.5/weather?q={urllib.parse.quote(city)},IN&appid={OWM_API_KEY}&units=metric"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            main = data.get('main', {})
            wind = data.get('wind', {})
            clouds = data.get('clouds', {}).get('all')
            weather = data.get('weather', [{}])[0].get('main')
            return {
                'temperature': main.get('temp'),
                'temp_min': main.get('temp_min'),
                'temp_max': main.get('temp_max'),
                'feels_like': main.get('feels_like'),
                'humidity': main.get('humidity'),
                'pressure': main.get('pressure'),
                'wind_speed': wind.get('speed'),
                'wind_deg': wind.get('deg'),
                'clouds': clouds,
                'weather_condition': weather
            }
    except Exception as e:
        print(f"Error fetching OWM for {city}: {e}")
        
    return {
        'temperature': None, 'temp_min': None, 'temp_max': None, 'feels_like': None, 
        'humidity': None, 'pressure': None, 'wind_speed': None, 'wind_deg': None, 
        'clouds': None, 'weather_condition': None
    }

def main():
    if not all([WAQI_API_KEY, OWM_API_KEY, SUPABASE_DB_URL]):
        print("Missing API keys or Database URL. Exiting...")
        return

    records = []
    timestamp = datetime.now(timezone.utc)
    
    print(f"Starting pipeline for {len(CITIES)} cities...")
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
    
    print("Connecting to Supabase PostgreSQL...")
    engine = create_engine(SUPABASE_DB_URL)
    
    metadata = MetaData()
    daily_aqi_weather_table = Table('daily_aqi_weather', metadata, autoload_with=engine)
    
    with engine.begin() as conn:
        for idx, row in df.iterrows():
            stmt = insert(daily_aqi_weather_table).values(
                city=row['city'],
                timestamp=row['timestamp'],
                aqi=row['aqi'],
                pm25=row['pm25'],
                pm10=row['pm10'],
                o3=row['o3'],
                no2=row['no2'],
                so2=row['so2'],
                co=row['co'],
                temperature=row['temperature'],
                temp_min=row['temp_min'],
                temp_max=row['temp_max'],
                feels_like=row['feels_like'],
                humidity=row['humidity'],
                pressure=row['pressure'],
                wind_speed=row['wind_speed'],
                wind_deg=row['wind_deg'],
                clouds=row['clouds'],
                weather_condition=row['weather_condition']
            )
            stmt = stmt.on_conflict_do_nothing(
                index_elements=['city', 'timestamp']
            )
            conn.execute(stmt)
            
    print(f"Successfully ingested {len(df)} records into the super-schema at {timestamp}.")

if __name__ == '__main__':
    main()
