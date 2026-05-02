import os
import sys
import requests
import pandas as pd
from datetime import datetime, timedelta
import time

# Force unbuffered stdout so progress is visible in real time
sys.stdout.reconfigure(line_buffering=True)

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

REQUEST_TIMEOUT = 120  # seconds — historical API returns large payloads
MAX_RETRIES = 5
RETRY_BACKOFF = 60  # seconds to wait on rate-limit before retrying
CITY_PAUSE = 60    # seconds to wait between cities


def map_weather_code(code):
    """Map Open-Meteo WMO weather codes to human-readable condition strings."""
    if pd.isna(code):
        return 'Unknown'
    code = int(code)
    if code == 0:
        return 'Clear'
    elif 1 <= code <= 3:
        return 'Clouds'
    elif 45 <= code <= 48:
        return 'Haze'
    elif 51 <= code <= 67:
        return 'Rain'
    elif 71 <= code <= 77:
        return 'Snow'
    elif code >= 80:
        return 'Rain'
    return 'Unknown'


def safe_get(url, retries=MAX_RETRIES):
    """GET request with timeout, retry on 429 rate-limits, and error handling."""
    for attempt in range(1, retries + 1):
        try:
            res = requests.get(url, timeout=REQUEST_TIMEOUT)
            if res.status_code == 429:
                wait = RETRY_BACKOFF * attempt
                print(f"    [RATE-LIMIT] 429 received, waiting {wait}s before retry {attempt}/{retries}...")
                time.sleep(wait)
                continue
            if res.status_code != 200:
                print(f"    [ERROR] HTTP {res.status_code}: {res.text[:200]}")
                return None
            return res
        except requests.exceptions.Timeout:
            print(f"    [TIMEOUT] Attempt {attempt}/{retries} timed out after {REQUEST_TIMEOUT}s")
            time.sleep(10)
        except requests.exceptions.RequestException as e:
            print(f"    [ERROR] Request failed: {e}")
            return None
    print(f"    [FAILED] All {retries} retries exhausted.")
    return None


def fetch_data(city, lat, lon):
    """
    Fetch ~10 years of hourly AQI + weather data for a single city.
    Returns a clean DataFrame with all NaN/null rows dropped.
    """
    start = "2016-01-01"
    # Use yesterday to ensure archive data is fully available
    end = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    # --- 1. Air Quality (hourly) ---
    print(f"  -> Pulling hourly AQI data ({start} to {end})...")
    url_aqi = (
        f"https://air-quality-api.open-meteo.com/v1/air-quality"
        f"?latitude={lat}&longitude={lon}"
        f"&start_date={start}&end_date={end}"
        f"&hourly=us_aqi,pm2_5,pm10,ozone,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide"
        f"&timezone=GMT"
    )

    res_aqi = safe_get(url_aqi)
    if res_aqi is None:
        return pd.DataFrame()

    data_aqi = res_aqi.json().get('hourly', {})
    if not data_aqi or 'time' not in data_aqi:
        print("  -> WARNING: No AQI hourly data returned from API.")
        return pd.DataFrame()

    df_aqi = pd.DataFrame(data_aqi)
    df_aqi['time'] = pd.to_datetime(df_aqi['time'], utc=True)
    print(f"     AQI rows received: {len(df_aqi)}")

    # --- 2. Weather (hourly + daily boundaries for temp_min/temp_max) ---
    print(f"  -> Pulling hourly weather + daily temperature bounds...")
    url_w = (
        f"https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lat}&longitude={lon}"
        f"&start_date={start}&end_date={end}"
        f"&hourly=temperature_2m,apparent_temperature,relative_humidity_2m,surface_pressure,"
        f"wind_speed_10m,wind_direction_10m,cloud_cover,weather_code"
        f"&daily=temperature_2m_max,temperature_2m_min"
        f"&timezone=GMT"
    )

    res_w = safe_get(url_w)
    if res_w is None:
        return pd.DataFrame()

    raw_weather = res_w.json()
    data_w_hourly = raw_weather.get('hourly', {})
    data_w_daily = raw_weather.get('daily', {})

    if not data_w_hourly or 'time' not in data_w_hourly:
        print("  -> WARNING: No hourly weather data returned.")
        return pd.DataFrame()
    if not data_w_daily or 'time' not in data_w_daily:
        print("  -> WARNING: No daily weather data returned.")
        return pd.DataFrame()

    df_w_hourly = pd.DataFrame(data_w_hourly)
    df_w_hourly['time'] = pd.to_datetime(df_w_hourly['time'], utc=True)
    df_w_hourly['date'] = df_w_hourly['time'].dt.date
    print(f"     Weather hourly rows: {len(df_w_hourly)}")

    df_w_daily = pd.DataFrame(data_w_daily)
    df_w_daily['time'] = pd.to_datetime(df_w_daily['time'], utc=True)
    df_w_daily['date'] = df_w_daily['time'].dt.date

    # Broadcast daily temp_min/temp_max onto every hourly row of that date
    df_w = pd.merge(
        df_w_hourly,
        df_w_daily[['date', 'temperature_2m_max', 'temperature_2m_min']],
        on='date', how='left'
    )

    # --- 3. Merge AQI + Weather on timestamp ---
    merged = pd.merge(df_aqi, df_w, on='time', how='inner')
    print(f"     Merged rows (inner join): {len(merged)}")

    if merged.empty:
        print("  -> WARNING: Merge produced zero rows.")
        return pd.DataFrame()

    merged['city'] = city
    merged['timestamp'] = merged['time']

    # Rename columns to match DB schema
    schema_mapped = merged.rename(columns={
        'us_aqi': 'aqi', 'pm2_5': 'pm25', 'pm10': 'pm10', 'ozone': 'o3',
        'nitrogen_dioxide': 'no2', 'sulphur_dioxide': 'so2', 'carbon_monoxide': 'co',
        'temperature_2m': 'temperature', 'temperature_2m_min': 'temp_min', 'temperature_2m_max': 'temp_max',
        'apparent_temperature': 'feels_like', 'relative_humidity_2m': 'humidity',
        'surface_pressure': 'pressure', 'wind_speed_10m': 'wind_speed',
        'wind_direction_10m': 'wind_deg', 'cloud_cover': 'clouds', 'weather_code': 'weather_condition'
    })

    # Map weather codes to human-readable strings
    schema_mapped['weather_condition'] = schema_mapped['weather_condition'].apply(map_weather_code)

    # Select only the columns matching our DB schema
    final_cols = [
        'city', 'timestamp', 'aqi', 'pm25', 'pm10', 'o3', 'no2', 'so2', 'co',
        'temperature', 'temp_min', 'temp_max', 'feels_like', 'humidity', 'pressure',
        'wind_speed', 'wind_deg', 'clouds', 'weather_condition'
    ]
    final_df = schema_mapped[final_cols].copy()

    # --- 4. Strict null/NaN filtering ---
    before_drop = len(final_df)
    # Drop rows where ANY column has NaN/null (critical for ML target quality)
    final_df = final_df.dropna()
    dropped = before_drop - len(final_df)
    print(f"     Dropped {dropped} rows with NaN/null values ({dropped/before_drop*100:.1f}%)")

    if final_df.empty:
        print("  -> WARNING: All rows had NaN values — empty result after filtering.")
        return pd.DataFrame()

    # Round float columns to 2 decimal places for storage efficiency
    numerical_cols = final_df.select_dtypes(include=['float64']).columns
    final_df[numerical_cols] = final_df[numerical_cols].round(2)

    # Final validation: ensure no NaN/null remain
    remaining_nulls = final_df.isnull().sum().sum()
    if remaining_nulls > 0:
        print(f"  -> ERROR: {remaining_nulls} null values remain after dropna — this should not happen!")
        final_df = final_df.dropna()

    print(f"  -> Final clean rows: {len(final_df)}")
    return final_df


if __name__ == '__main__':
    output_dir = 'artefacts'
    file_path = os.path.join(output_dir, '10yr_hourly_timeline.csv')

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Check which cities are already collected
    done_cities = []
    if os.path.exists(file_path):
        try:
            # Only read the 'city' column to check existing cities (memory efficient)
            existing_df = pd.read_csv(file_path, usecols=['city'])
            done_cities = existing_df['city'].unique().tolist()
            del existing_df
        except Exception as e:
            print(f"Warning: Could not read existing CSV: {e}")

    remaining = [c for c in CITIES if c not in done_cities]
    print(f"Cities already collected: {len(done_cities)}/{len(CITIES)}")
    print(f"Cities remaining: {len(remaining)} -> {remaining}")
    print(f"{'='*60}")

    total = len(CITIES)
    success_count = 0
    fail_count = 0

    for idx, (city, coords) in enumerate(CITIES.items(), 1):
        if city in done_cities:
            print(f"[{idx}/{total}] SKIP {city} (already collected)")
            continue

        print(f"\n[{idx}/{total}] Fetching data for {city}...")
        try:
            df = fetch_data(city, coords[0], coords[1])
            if not df.empty:
                header_flag = not os.path.exists(file_path)
                df.to_csv(file_path, mode='a', header=header_flag, index=False)
                print(f"  => Saved {len(df)} rows for {city}")
                success_count += 1
            else:
                print(f"  => WARNING: No valid data for {city}, skipping.")
                fail_count += 1

            # Rate-limit pause between cities to respect Open-Meteo fair usage
            if idx < total:
                print(f"  -> Waiting {CITY_PAUSE}s before next city (rate-limit courtesy)...")
                time.sleep(CITY_PAUSE)
        except Exception as e:
            print(f"  => CRITICAL ERROR on {city}: {e}")
            fail_count += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"COLLECTION COMPLETE")
    print(f"  Newly collected: {success_count}")
    print(f"  Failed/skipped:  {fail_count}")
    print(f"  Previously done: {len(done_cities)}")

    if os.path.exists(file_path):
        final = pd.read_csv(file_path, usecols=['city'])
        unique_cities = final['city'].unique()
        total_rows = len(final)
        del final
        # Get actual row count
        row_count = sum(1 for _ in open(file_path)) - 1  # subtract header
        print(f"  Total rows in CSV: {row_count}")
        print(f"  Unique cities: {len(unique_cities)} -> {sorted(unique_cities)}")

        missing = set(CITIES.keys()) - set(unique_cities)
        if missing:
            print(f"  MISSING cities: {missing}")
        else:
            print(f"  All 20 cities successfully collected!")
    else:
        print(f"  WARNING: No output file was created.")
