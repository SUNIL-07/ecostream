import os
import requests
import pandas as pd
from datetime import datetime
import time

pd.options.mode.chained_assignment = None

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
    if pd.isna(code): return 'Unknown'
    code = int(code)
    if code == 0: return 'Clear'
    elif 1 <= code <= 3: return 'Clouds'
    elif 45 <= code <= 48: return 'Haze'
    elif 51 <= code <= 67: return 'Rain'
    elif 71 <= code <= 77: return 'Snow'
    elif code >= 80: return 'Rain'
    return 'Unknown'

def fetch_data(city, lat, lon):
    start = "2016-01-01"
    end = "2026-04-16"
    print(f"  -> Pulling Strict Hourly AQI...")
    url_aqi = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&start_date={start}&end_date={end}&hourly=us_aqi,pm2_5,pm10,ozone,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide&timezone=GMT"
    
    res_aqi = requests.get(url_aqi)
    if res_aqi.status_code == 429:
        print("  [ERROR] Rate limit on AQI API.")
        return pd.DataFrame()
        
    data_aqi = res_aqi.json().get('hourly', {})
    if not data_aqi: return pd.DataFrame()
    df_aqi = pd.DataFrame(data_aqi)
    df_aqi['time'] = pd.to_datetime(df_aqi['time'], utc=True) # Lock natively to UTC matching live pipeline

    print(f"  -> Pulling Linked Hourly + Daily Boundary Weather...")
    url_w = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={start}&end_date={end}&hourly=temperature_2m,apparent_temperature,relative_humidity_2m,surface_pressure,wind_speed_10m,wind_direction_10m,cloud_cover,weather_code&daily=temperature_2m_max,temperature_2m_min&timezone=GMT"
    
    res_w = requests.get(url_w)
    if res_w.status_code == 429:
        print("  [ERROR] Rate limit on Weather API.")
        return pd.DataFrame()
        
    raw_weather = res_w.json()
    data_w_hourly = raw_weather.get('hourly', {})
    data_w_daily = raw_weather.get('daily', {})
    
    if not data_w_hourly or not data_w_daily: return pd.DataFrame()
    
    df_w_hourly = pd.DataFrame(data_w_hourly)
    df_w_hourly['time'] = pd.to_datetime(df_w_hourly['time'], utc=True)
    df_w_hourly['date'] = df_w_hourly['time'].dt.date
    
    df_w_daily = pd.DataFrame(data_w_daily)
    df_w_daily['time'] = pd.to_datetime(df_w_daily['time'], utc=True)
    df_w_daily['date'] = df_w_daily['time'].dt.date
    
    # Broadcast daily bounds exclusively onto the hourly grids natively
    df_w = pd.merge(df_w_hourly, df_w_daily[['date', 'temperature_2m_max', 'temperature_2m_min']], on='date', how='left')

    # Merge final AQI matching hourly structural array organically
    merged = pd.merge(df_aqi, df_w, on='time', how='inner')
    
    merged['city'] = city
    merged['timestamp'] = merged['time'] # No longer creating a separate 00:00 timestamp! Uses rigorous pure hourly tracking natively!
    
    schema_mapped = merged.rename(columns={
        'us_aqi': 'aqi', 'pm2_5': 'pm25', 'pm10': 'pm10', 'ozone': 'o3',
        'nitrogen_dioxide': 'no2', 'sulphur_dioxide': 'so2', 'carbon_monoxide': 'co',
        'temperature_2m': 'temperature', 'temperature_2m_min': 'temp_min', 'temperature_2m_max': 'temp_max',
        'apparent_temperature': 'feels_like', 'relative_humidity_2m': 'humidity',
        'surface_pressure': 'pressure', 'wind_speed_10m': 'wind_speed',
        'wind_direction_10m': 'wind_deg', 'cloud_cover': 'clouds', 'weather_code': 'weather_condition'
    })
    
    # Transform numeric category condition algorithm natively
    schema_mapped['weather_condition'] = schema_mapped['weather_condition'].apply(map_weather_code)
    
    final_df = schema_mapped[[
        'city', 'timestamp', 'aqi', 'pm25', 'pm10', 'o3', 'no2', 'so2', 'co',
        'temperature', 'temp_min', 'temp_max', 'feels_like', 'humidity', 'pressure',
        'wind_speed', 'wind_deg', 'clouds', 'weather_condition'
    ]]
    
    # Critical Filter: Explicitly drop structural rows containing pure API blanks for ML Targets
    final_df = final_df.dropna(subset=['aqi'])
    if final_df.empty: return pd.DataFrame()
    
    # Round gracefully for massive memory footprint lowering natively
    numerical_cols = final_df.select_dtypes(include=['float64']).columns
    final_df[numerical_cols] = final_df[numerical_cols].round(2)
    
    return final_df

if __name__ == '__main__':
    file_path = 'artefacts/10yr_hourly_timeline.csv'
    
    try:
        existing_df = pd.read_csv(file_path)
        done_cities = existing_df['city'].unique().tolist()
    except FileNotFoundError:
        done_cities = []
        
    print(f"Pre-existing verified cities: {len(done_cities)}")
    
    current = 1
    total = len(CITIES)
    for city, coords in CITIES.items():
        if city in done_cities:
            print(f"[{current}/{total}] Skipping {city} (Already strictly mapped)")
            current += 1
            continue
            
        print(f"[{current}/{total}] Locking 1.5M hourly parameters natively for {city}...")
        try:
            df = fetch_data(city, coords[0], coords[1])
            if not df.empty:
                header_flag = not os.path.exists(file_path)
                df.to_csv(file_path, mode='a', header=header_flag, index=False)
                print(f"  -> Successfully generated {len(df)} pure hourly rows!")
            else:
                print(f"  -> WARNING: Empty target blocks skipped natively.")
                
            time.sleep(12)
        except Exception as e:
            print(f"Critical error on {city}: {e}")
            
        current += 1
        
    final = pd.read_csv(file_path)
    print(f"\nTimeline Integration Complete! Pure hourly resolution array spans {len(final)} unique targets!")
