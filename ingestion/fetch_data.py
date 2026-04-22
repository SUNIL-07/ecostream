import os
import requests
import pandas as pd
from datetime import datetime, timezone
from sqlalchemy import create_engine, Table, MetaData
from sqlalchemy.dialects.postgresql import insert
import warnings
warnings.filterwarnings('ignore')

try:
    from dotenv import load_dotenv
    load_dotenv()
    load_dotenv('../.env')
except:
    pass

SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")
if not SUPABASE_DB_URL:
    raise ValueError("Missing SUPABASE_DB_URL structurally!")

CITIES = {
    "New Delhi": (28.6139, 77.2090), "Kolkata": (22.5726, 88.3639), "Mumbai": (19.0760, 72.8777),
    "Bengaluru": (12.9716, 77.5946), "Chennai": (13.0827, 80.2707), "Hyderabad": (17.3850, 78.4867),
    "Ahmedabad": (23.0225, 72.5714), "Surat": (21.1702, 72.8311), "Pune": (18.5204, 73.8567),
    "Lucknow": (26.8467, 80.9462), "Kanpur": (26.4499, 80.3319), "Jaipur": (26.9124, 75.7873),
    "Indore": (22.7196, 75.8577), "Patna": (25.5941, 85.1376), "Nagpur": (21.1458, 79.0882),
    "Thiruvananthapuram": (8.5241, 76.9366), "Bhopal": (23.2599, 77.4126), "Chandigarh": (30.7333, 76.7794),
    "Ludhiana": (30.9010, 75.8573), "Visakhapatnam": (17.6868, 83.2185)
}

def map_weather_code(code):
    if pd.isna(code) or code is None: return 'Unknown'
    code = int(code)
    if code == 0: return 'Clear'
    elif 1 <= code <= 3: return 'Clouds'
    elif 45 <= code <= 48: return 'Haze'
    elif 51 <= code <= 67: return 'Rain'
    elif 71 <= code <= 77: return 'Snow'
    elif code >= 80: return 'Rain'
    return 'Unknown'

def fetch_live_data():
    records = []
    
    for city, coords in CITIES.items():
        lat, lon = coords
        
        # 1. Fetch Exact Open-Meteo Air Quality Model (Replacing WAQI identically)
        url_aqi = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&current=us_aqi,pm2_5,pm10,ozone,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide"
        res_aqi = requests.get(url_aqi)
        
        # 2. Fetch Exact Open-Meteo Weather Model explicitly capturing daily boundary identical to Historical Architecture natively
        url_w = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,surface_pressure,wind_speed_10m,wind_direction_10m,cloud_cover,weather_code&daily=temperature_2m_max,temperature_2m_min&timezone=GMT"
        res_w = requests.get(url_w)

        if res_aqi.status_code != 200 or res_w.status_code != 200:
            print(f"Skipped {city}: Core API Error [{res_aqi.status_code} | {res_w.status_code}]")
            continue
            
        cur_aqi = res_aqi.json().get('current', {})
        cur_w = res_w.json().get('current', {})
        daily_w = res_w.json().get('daily', {})
        
        if not cur_aqi or not cur_w or not daily_w:
            print(f"Skipped {city}: Blank JSON payload natively")
            continue
            
        # Structure variables into the identical matching format spanning the historical script universally natively!
        record = {
            'city': city,
            'timestamp': cur_aqi.get('time') + "+00:00", # Exact GMT constraint alignment universally
            'aqi': cur_aqi.get('us_aqi'),
            'pm25': cur_aqi.get('pm2_5'),
            'pm10': cur_aqi.get('pm10'),
            'o3': cur_aqi.get('ozone'),
            'no2': cur_aqi.get('nitrogen_dioxide'),
            'so2': cur_aqi.get('sulphur_dioxide'),
            'co': cur_aqi.get('carbon_monoxide'),
            'temperature': cur_w.get('temperature_2m'),
            'temp_min': daily_w.get('temperature_2m_min', [None])[0] if daily_w.get('temperature_2m_min') else None,
            'temp_max': daily_w.get('temperature_2m_max', [None])[0] if daily_w.get('temperature_2m_max') else None,
            'feels_like': cur_w.get('apparent_temperature'),
            'humidity': cur_w.get('relative_humidity_2m'),
            'pressure': cur_w.get('surface_pressure'),
            'wind_speed': cur_w.get('wind_speed_10m'),
            'wind_deg': cur_w.get('wind_direction_10m'),
            'clouds': cur_w.get('cloud_cover'),
            'weather_condition': map_weather_code(cur_w.get('weather_code'))
        }
        
        records.append(record)

    df = pd.DataFrame(records)
    
    # 3. Aggressive Strict DropNA constraint identically applied across real-time feeds securely!
    if df.empty: return pd.DataFrame()
    df = df.dropna()
    
    # Cast cleanly into pure python targets for PostgreSQL insertion safely
    df = df.where(pd.notnull(df), None)
    
    return df

if __name__ == "__main__":
    print("Executing automated live architecture collection cleanly...")
    df = fetch_live_data()
    
    print(f"Successfully processed exactly {len(df)} 100%-pure parameters universally!")
    if len(df) > 0:
        engine = create_engine(SUPABASE_DB_URL)
        metadata = MetaData()
        table = Table('daily_aqi_weather', metadata, autoload_with=engine)
        
        records = df.to_dict(orient='records')
        with engine.begin() as conn:
            stmt = insert(table).values(records)
            stmt = stmt.on_conflict_do_nothing(index_elements=['city', 'timestamp'])
            conn.execute(stmt)
            print("[SYNC REACHED] Successfully bridged Native Arrays into Supabase Cloud!")
