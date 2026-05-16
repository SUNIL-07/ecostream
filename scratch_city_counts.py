import os
import requests
import pandas as pd
from datetime import datetime, timedelta
import time

CITIES = {
    "New Delhi": (28.6139, 77.2090), "Kolkata": (22.5726, 88.3639), "Mumbai": (19.0760, 72.8777),
    "Bengaluru": (12.9716, 77.5946), "Chennai": (13.0827, 80.2707), "Hyderabad": (17.3850, 78.4867),
    "Ahmedabad": (23.0225, 72.5714), "Surat": (21.1702, 72.8311), "Pune": (18.5204, 73.8567),
    "Lucknow": (26.8467, 80.9462), "Kanpur": (26.4499, 80.3319), "Jaipur": (26.9124, 75.7873),
    "Indore": (22.7196, 75.8577), "Patna": (25.5941, 85.1376), "Nagpur": (21.1458, 79.0882),
    "Thiruvananthapuram": (8.5241, 76.9366), "Bhopal": (23.2599, 77.4126), "Chandigarh": (30.7333, 76.7794),
    "Ludhiana": (30.9010, 75.8573), "Visakhapatnam": (17.6868, 83.2185)
}

def safe_get(url, retries=5):
    for attempt in range(1, retries + 1):
        try:
            res = requests.get(url, timeout=60)
            if res.status_code == 429:
                time.sleep(10 * attempt)
                continue
            if res.status_code == 200:
                return res
        except:
            time.sleep(5)
    return None

start = "2022-08-05"
end = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

results = []
print(f"Fetching from {start} to {end}...")

for city, (lat, lon) in CITIES.items():
    print(f"Processing {city}...")
    
    url_aqi = (
        f"https://air-quality-api.open-meteo.com/v1/air-quality"
        f"?latitude={lat}&longitude={lon}&start_date={start}&end_date={end}"
        f"&hourly=us_aqi,pm2_5,pm10,ozone,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide,aerosol_optical_depth"
        f"&timezone=GMT"
    )
    
    url_w = (
        f"https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lat}&longitude={lon}&start_date={start}&end_date={end}"
        f"&hourly=temperature_2m,apparent_temperature,relative_humidity_2m,surface_pressure,"
        f"wind_speed_10m,wind_direction_10m,cloud_cover,weather_code,precipitation,"
        f"shortwave_radiation,boundary_layer_height"
        f"&daily=temperature_2m_mean,temperature_2m_max,temperature_2m_min"
        f"&timezone=GMT"
    )
    
    res_aqi = safe_get(url_aqi)
    res_w = safe_get(url_w)
    
    if not res_aqi or not res_w:
        results.append({'City': city, 'Valid Records': 0, 'BLH Missing': 0})
        continue
        
    df_aqi = pd.DataFrame(res_aqi.json().get('hourly', {}))
    raw_w = res_w.json()
    df_w_hourly = pd.DataFrame(raw_w.get('hourly', {}))
    df_w_daily = pd.DataFrame(raw_w.get('daily', {}))
    
    if df_aqi.empty or df_w_hourly.empty or df_w_daily.empty:
        results.append({'City': city, 'Valid Records': 0, 'BLH Missing': 0})
        continue
        
    df_aqi['time'] = pd.to_datetime(df_aqi['time'])
    df_w_hourly['time'] = pd.to_datetime(df_w_hourly['time'])
    df_w_daily['time'] = pd.to_datetime(df_w_daily['time'])
    
    df_w_hourly['date'] = df_w_hourly['time'].dt.date
    df_w_daily['date'] = df_w_daily['time'].dt.date
    
    df_w = pd.merge(
        df_w_hourly,
        df_w_daily[['date', 'temperature_2m_mean', 'temperature_2m_max', 'temperature_2m_min']],
        on='date', how='left'
    )
    df = pd.merge(df_aqi, df_w, on='time', how='inner')
    
    # We want to drop rows where any column EXCEPT boundary_layer_height is NaN.
    cols_to_check = [c for c in df.columns if c not in ['time', 'date', 'boundary_layer_height']]
    df_clean = df.dropna(subset=cols_to_check)
    
    valid_count = len(df_clean)
    blh_missing_count = df_clean['boundary_layer_height'].isnull().sum()
    
    results.append({
        'City': city,
        'Valid Records': valid_count,
        'BLH Nulls (Kept)': blh_missing_count
    })
    
    time.sleep(2) # rate limit pause

df_res = pd.DataFrame(results)
print("\n--- RESULTS ---")
print(df_res.to_string(index=False))

total_records = df_res['Valid Records'].sum()
print(f"\nTotal Valid Records Across All Cities: {total_records}")
