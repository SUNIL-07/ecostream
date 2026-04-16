import os
import requests
import pandas as pd
from datetime import datetime
import numpy as np

# Suppress pandas chained assignment warnings smoothly
pd.options.mode.chained_assignment = None

os.makedirs('artefacts', exist_ok=True)

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
    
    try:
        res_aqi = requests.get(url_aqi)
        data_aqi = res_aqi.json().get('hourly', {})
        df_aqi = pd.DataFrame(data_aqi)
        if not df_aqi.empty:
            df_aqi['time'] = pd.to_datetime(df_aqi['time'])
    except:
        df_aqi = pd.DataFrame()

    print(f"  -> Pulling Weather...")
    url_w = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={start}&end_date={end}&hourly=temperature_2m,apparent_temperature,relative_humidity_2m,surface_pressure,wind_speed_10m,wind_direction_10m,cloud_cover,weather_code"
    try:
        res_w = requests.get(url_w)
        data_w = res_w.json().get('hourly', {})
        df_w = pd.DataFrame(data_w)
        if not df_w.empty:
            df_w['time'] = pd.to_datetime(df_w['time'])
    except:
        df_w = pd.DataFrame()
        
    if not df_aqi.empty and not df_w.empty:
        merged = pd.merge(df_aqi, df_w, on='time', how='inner')
        merged['date'] = merged['time'].dt.date
        
        # Calculate daily aggregates
        daily = merged.groupby('date').agg({
            'us_aqi': 'mean',
            'pm2_5': 'mean',
            'pm10': 'mean',
            'ozone': 'mean',
            'nitrogen_dioxide': 'mean',
            'sulphur_dioxide': 'mean',
            'carbon_monoxide': 'mean',
            'temperature_2m': ['mean', 'min', 'max'],
            'apparent_temperature': 'mean',
            'relative_humidity_2m': 'mean',
            'surface_pressure': 'mean',
            'wind_speed_10m': 'mean',
            'wind_direction_10m': 'mean',
            'cloud_cover': 'mean',
            'weather_code': 'median' # median WMO code is robust
        })
        
        # Flatten MultiIndex
        daily.columns = ['_'.join(col).strip() if type(col) is tuple else col for col in daily.columns.values]
        daily = daily.reset_index()
        
        # Enforce exactly 18 specific Schema Rules
        daily['city'] = city
        daily['timestamp'] = pd.to_datetime(daily['date'])
        
        schema_mapped = daily.rename(columns={
            'us_aqi_mean': 'aqi',
            'pm2_5_mean': 'pm25',
            'pm10_mean': 'pm10',
            'ozone_mean': 'o3',
            'nitrogen_dioxide_mean': 'no2',
            'sulphur_dioxide_mean': 'so2',
            'carbon_monoxide_mean': 'co',
            'temperature_2m_mean': 'temperature',
            'temperature_2m_min': 'temp_min',
            'temperature_2m_max': 'temp_max',
            'apparent_temperature_mean': 'feels_like',
            'relative_humidity_2m_mean': 'humidity',
            'surface_pressure_mean': 'pressure',
            'wind_speed_10m_mean': 'wind_speed',
            'wind_direction_10m_mean': 'wind_deg',
            'cloud_cover_mean': 'clouds'
        })
        
        # Map code to UI String perfectly
        schema_mapped['weather_condition'] = schema_mapped['weather_code_median'].apply(map_weather_code)
        
        # Force specific schema array natively
        final_df = schema_mapped[[
            'city', 'timestamp', 'aqi', 'pm25', 'pm10', 'o3', 'no2', 'so2', 'co',
            'temperature', 'temp_min', 'temp_max', 'feels_like', 'humidity', 'pressure',
            'wind_speed', 'wind_deg', 'clouds', 'weather_condition'
        ]]
        
        return final_df
    return pd.DataFrame()

if __name__ == '__main__':
    all_data = []
    total = len(CITIES)
    current = 1
    
    print("Initiating massive 10-year historical extraction sequence...\n")
    for city, coords in CITIES.items():
        print(f"[{current}/{total}] Accessing archives for {city}...")
        try:
            df = fetch_data(city, coords[0], coords[1])
            if not df.empty:
                all_data.append(df)
        except Exception as e:
            print(f"Critical error on {city}: {e}")
        current += 1
        
    if all_data:
        final = pd.concat(all_data, ignore_index=True)
        final = final.sort_values(by=['city', 'timestamp'])
        
        # Format the arrays nicely for the Model to consume seamlessly
        numerical_cols = final.select_dtypes(include=['float64']).columns
        final[numerical_cols] = final[numerical_cols].round(2)
        
        file_path = 'artefacts/10yr_historical_data.csv'
        final.to_csv(file_path, index=False)
        print(f"\n[✓] SUCCESS: Synthesized 10-years into an elegant array!")
        print(f"[✓] Location: {file_path}")
        print(f"[✓] Dimensions: {len(final)} total rows created.")
        print("\nHead representation mapping against schema.sql:")
        print(final.head())
    else:
        print("Failed to pull any valid data into array.")
