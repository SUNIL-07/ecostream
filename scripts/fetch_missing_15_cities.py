import os
import requests
import pandas as pd
from datetime import datetime
import numpy as np
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
    print(f"  -> Pulling AQI...")
    url_aqi = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&start_date={start}&end_date={end}&hourly=us_aqi,pm2_5,pm10,ozone,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide"
    
    res_aqi = requests.get(url_aqi)
    if res_aqi.status_code == 429:
        print("  [ERROR] Rate limit hit on AQI API. Open-Meteo requires backoff.")
        return pd.DataFrame()
        
    df_aqi = pd.DataFrame()
    data_aqi = res_aqi.json().get('hourly', {})
    if data_aqi:
        df_aqi = pd.DataFrame(data_aqi)
        df_aqi['time'] = pd.to_datetime(df_aqi['time'])

    print(f"  -> Pulling Weather...")
    url_w = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={start}&end_date={end}&hourly=temperature_2m,apparent_temperature,relative_humidity_2m,surface_pressure,wind_speed_10m,wind_direction_10m,cloud_cover,weather_code"
    
    res_w = requests.get(url_w)
    if res_w.status_code == 429:
        print("  [ERROR] Rate limit hit on Weather API. Open-Meteo requires backoff.")
        return pd.DataFrame()
        
    df_w = pd.DataFrame()
    data_w = res_w.json().get('hourly', {})
    if data_w:
        df_w = pd.DataFrame(data_w)
        df_w['time'] = pd.to_datetime(df_w['time'])
        
    if not df_aqi.empty and not df_w.empty:
        merged = pd.merge(df_aqi, df_w, on='time', how='inner')
        merged['date'] = merged['time'].dt.date
        
        daily = merged.groupby('date').agg({
            'us_aqi': 'mean', 'pm2_5': 'mean', 'pm10': 'mean', 'ozone': 'mean',
            'nitrogen_dioxide': 'mean', 'sulphur_dioxide': 'mean', 'carbon_monoxide': 'mean',
            'temperature_2m': ['mean', 'min', 'max'], 'apparent_temperature': 'mean',
            'relative_humidity_2m': 'mean', 'surface_pressure': 'mean', 'wind_speed_10m': 'mean',
            'wind_direction_10m': 'mean', 'cloud_cover': 'mean', 'weather_code': 'median'
        })
        
        daily.columns = ['_'.join(col).strip() if type(col) is tuple else col for col in daily.columns.values]
        daily = daily.reset_index()
        
        daily['city'] = city
        daily['timestamp'] = pd.to_datetime(daily['date'])
        
        schema_mapped = daily.rename(columns={
            'us_aqi_mean': 'aqi', 'pm2_5_mean': 'pm25', 'pm10_mean': 'pm10', 'ozone_mean': 'o3',
            'nitrogen_dioxide_mean': 'no2', 'sulphur_dioxide_mean': 'so2', 'carbon_monoxide_mean': 'co',
            'temperature_2m_mean': 'temperature', 'temperature_2m_min': 'temp_min', 'temperature_2m_max': 'temp_max',
            'apparent_temperature_mean': 'feels_like', 'relative_humidity_2m_mean': 'humidity',
            'surface_pressure_mean': 'pressure', 'wind_speed_10m_mean': 'wind_speed',
            'wind_direction_10m_mean': 'wind_deg', 'cloud_cover_mean': 'clouds'
        })
        
        schema_mapped['weather_condition'] = schema_mapped['weather_code_median'].apply(map_weather_code)
        
        final_df = schema_mapped[[
            'city', 'timestamp', 'aqi', 'pm25', 'pm10', 'o3', 'no2', 'so2', 'co',
            'temperature', 'temp_min', 'temp_max', 'feels_like', 'humidity', 'pressure',
            'wind_speed', 'wind_deg', 'clouds', 'weather_condition'
        ]]
        
        # Round neatly
        numerical_cols = final_df.select_dtypes(include=['float64']).columns
        final_df[numerical_cols] = final_df[numerical_cols].round(2)
        
        return final_df
    return pd.DataFrame()

if __name__ == '__main__':
    file_path = 'artefacts/10yr_historical_data.csv'
    
    try:
        existing_df = pd.read_csv(file_path)
        done_cities = existing_df['city'].unique().tolist()
    except FileNotFoundError:
        done_cities = []
        
    print(f"Pre-existing compiled cities: {len(done_cities)}")
    
    current = 1
    total = len(CITIES)
    for city, coords in CITIES.items():
        if city in done_cities:
            print(f"[{current}/{total}] Skipping {city} (Already exists in CSV)")
            current += 1
            continue
            
        print(f"[{current}/{total}] Extracting robust archive for {city}...")
        try:
            df = fetch_data(city, coords[0], coords[1])
            if not df.empty:
                # Mode append
                header_flag = not os.path.exists(file_path)
                df.to_csv(file_path, mode='a', header=header_flag, index=False)
                print(f"  -> Appended {len(df)} rows for {city} securely.")
            else:
                print(f"  -> WARNING: Empty response for {city}.")
                
            # Crucial: Prevent 429 Too Many Requests rate limit
            print("  -> Sleeping for 12 seconds to reset Open-Meteo Rate Limiter...")
            time.sleep(12)
        except Exception as e:
            print(f"Critical error on {city}: {e}")
            
        current += 1
        
    final = pd.read_csv(file_path)
    print(f"\nTotal extraction fully rectified! Final CSV encompasses {final['city'].nunique()} distinct cities!")
