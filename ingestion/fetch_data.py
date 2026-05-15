"""
EcoStream - Hourly Live Ingestion Script
==========================================
Runs every hour via GitHub Actions cron (0 * * * *).
Fetches the most recently COMPLETED hour of AQI + weather data
for all 20 cities from Open-Meteo and upserts into Supabase.
"""

import os
import sys
import json
import time
import requests
import pandas as pd
from datetime import datetime, timezone, timedelta

sys.stdout.reconfigure(line_buffering=True)

# --- Load env (local .env or GitHub Actions secrets) ---
try:
    from dotenv import load_dotenv
    load_dotenv()
    load_dotenv('../.env')
except Exception:
    pass

SUPABASE_URL        = "https://trfetbxovhmbmwgbqdqm.supabase.co"
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or \
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRyZmV0YnhvdmhtYm13Z2JxZHFtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NjM1NjY3MCwiZXhwIjoyMDkxOTMyNjcwfQ.XgrP4c5hniQJbSK87xpEru820e24K9gLebA2bBt-Gb8"
TABLE_NAME          = "daily_aqi_weather"
REST_URL            = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}?on_conflict=city,timestamp"

CITIES = {
    "New Delhi":          (28.6139, 77.2090),
    "Kolkata":            (22.5726, 88.3639),
    "Mumbai":             (19.0760, 72.8777),
    "Bengaluru":          (12.9716, 77.5946),
    "Chennai":            (13.0827, 80.2707),
    "Hyderabad":          (17.3850, 78.4867),
    "Ahmedabad":          (23.0225, 72.5714),
    "Surat":              (21.1702, 72.8311),
    "Pune":               (18.5204, 73.8567),
    "Lucknow":            (26.8467, 80.9462),
    "Kanpur":             (26.4499, 80.3319),
    "Jaipur":             (26.9124, 75.7873),
    "Indore":             (22.7196, 75.8577),
    "Patna":              (25.5941, 85.1376),
    "Nagpur":             (21.1458, 79.0882),
    "Thiruvananthapuram": (8.5241,  76.9366),
    "Bhopal":             (23.2599, 77.4126),
    "Chandigarh":         (30.7333, 76.7794),
    "Ludhiana":           (30.9010, 75.8573),
    "Visakhapatnam":      (17.6868, 83.2185),
}

WEATHER_CODE_MAP = {
    0: "Clear", 1: "Clouds", 2: "Clouds", 3: "Clouds",
    45: "Haze", 48: "Haze",
}

def map_weather_code(code):
    """Maps WMO weather code to a human-readable string."""
    if pd.isna(code) or code is None:
        return "Unknown"
    code = int(code)
    if code == 0: return "Clear"
    elif 1 <= code <= 3: return "Clouds"
    elif 45 <= code <= 48: return "Haze"
    elif 51 <= code <= 67: return "Rain"
    elif 71 <= code <= 77: return "Snow"
    elif code >= 80: return "Rain"
    return "Unknown"

def get_target_hour():
    """
    Returns the ISO string for the last COMPLETED hour in UTC.
    e.g. if current time is 14:35 UTC, target hour is '2026-05-15T14:00'.
    This ensures we always fetch a fully-settled data point.
    """
    now_utc = datetime.now(timezone.utc)
    target  = now_utc.replace(minute=0, second=0, microsecond=0)
    return target.strftime("%Y-%m-%dT%H:00"), target

def fetch_live_data():
    target_str, target_dt = get_target_hour()
    date_str = target_dt.strftime("%Y-%m-%d")
    is_weekend = target_dt.weekday() >= 5

    print(f"Target hour (UTC): {target_str}")
    records = []

    for city, (lat, lon) in CITIES.items():
        print(f"  -> Fetching {city}...", end=" ")

        # --- Air Quality (hourly endpoint, filter to target hour) ---
        url_aqi = (
            f"https://air-quality-api.open-meteo.com/v1/air-quality"
            f"?latitude={lat}&longitude={lon}"
            f"&hourly=us_aqi,pm2_5,pm10,ozone,nitrogen_dioxide,"
            f"sulphur_dioxide,carbon_monoxide,aerosol_optical_depth"
            f"&start_date={date_str}&end_date={date_str}&timezone=GMT"
        )

        # --- Weather (hourly + daily for temp_mean/range) ---
        url_w = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&hourly=temperature_2m,apparent_temperature,relative_humidity_2m,"
            f"surface_pressure,wind_speed_10m,wind_direction_10m,cloud_cover,"
            f"weather_code,precipitation,shortwave_radiation,boundary_layer_height"
            f"&daily=temperature_2m_mean,temperature_2m_max,temperature_2m_min"
            f"&start_date={date_str}&end_date={date_str}&timezone=GMT"
        )

        try:
            res_aqi = requests.get(url_aqi, timeout=30)
            res_w   = requests.get(url_w,   timeout=30)
        except Exception as e:
            print(f"[ERROR] {e}")
            continue

        if res_aqi.status_code != 200 or res_w.status_code != 200:
            print(f"[SKIP] API {res_aqi.status_code}/{res_w.status_code}")
            continue

        aqi_hourly = res_aqi.json().get("hourly", {})
        w_hourly   = res_w.json().get("hourly", {})
        w_daily    = res_w.json().get("daily", {})

        if not aqi_hourly or not w_hourly or not w_daily:
            print("[SKIP] Empty response")
            continue

        # Find the index matching our target hour
        times = aqi_hourly.get("time", [])
        try:
            idx = times.index(target_str)
        except ValueError:
            print(f"[SKIP] Target hour {target_str} not in response")
            continue

        def g(d, key): return d.get(key, [None])[idx] if d.get(key) else None
        def d0(d, key): return d.get(key, [None])[0] if d.get(key) else None

        temp_max   = d0(w_daily, "temperature_2m_max")
        temp_min   = d0(w_daily, "temperature_2m_min")
        temp_range = round(temp_max - temp_min, 2) if temp_max and temp_min else None

        record = {
            "city":                 city,
            "location":             f"SRID=4326;POINT({lon} {lat})",
            "timestamp":            target_str + "+00:00",
            "aqi":                  g(aqi_hourly, "us_aqi"),
            "pm25":                 g(aqi_hourly, "pm2_5"),
            "pm10":                 g(aqi_hourly, "pm10"),
            "o3":                   g(aqi_hourly, "ozone"),
            "no2":                  g(aqi_hourly, "nitrogen_dioxide"),
            "so2":                  g(aqi_hourly, "sulphur_dioxide"),
            "co":                   g(aqi_hourly, "carbon_monoxide"),
            "aerosol_optical_depth":g(aqi_hourly, "aerosol_optical_depth"),
            "temperature":          g(w_hourly,   "temperature_2m"),
            "temp_mean":            d0(w_daily,   "temperature_2m_mean"),
            "temp_range":           temp_range,
            "feels_like":           g(w_hourly,   "apparent_temperature"),
            "humidity":             g(w_hourly,   "relative_humidity_2m"),
            "pressure":             g(w_hourly,   "surface_pressure"),
            "wind_speed":           g(w_hourly,   "wind_speed_10m"),
            "wind_deg":             g(w_hourly,   "wind_direction_10m"),
            "clouds":               g(w_hourly,   "cloud_cover"),
            "boundary_layer_height":g(w_hourly,   "boundary_layer_height"),
            "precipitation":        g(w_hourly,   "precipitation"),
            "solar_radiation":      g(w_hourly,   "shortwave_radiation"),
            "weather_condition":    map_weather_code(g(w_hourly, "weather_code")),
            "is_weekend":           is_weekend,
        }

        # Validate all core fields are present (BLH is nullable — skip it)
        core_keys = [k for k in record if k not in ("boundary_layer_height", "location")]
        if any(record[k] is None for k in core_keys):
            missing = [k for k in core_keys if record[k] is None]
            print(f"[SKIP] Missing core fields: {missing}")
            continue

        records.append(record)
        print("OK")
        time.sleep(0.3)  # polite rate-limit pause

    return pd.DataFrame(records)


def upload_to_supabase(df):
    if df.empty:
        print("No records to upload.")
        return

    import numpy as np
    df = df.replace({float("nan"): None, pd.NaT: None})
    records = df.to_dict(orient="records")

    headers = {
        "apikey":        SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "resolution=merge-duplicates",
    }

    print(f"Uploading {len(records)} records to Supabase...")
    try:
        resp = requests.post(REST_URL, headers=headers,
                             data=json.dumps(records), timeout=60)
        if resp.status_code in (200, 201, 204):
            print(f"[OK] Upload successful (HTTP {resp.status_code})")
        else:
            print(f"[ERROR] Upload failed: {resp.status_code} - {resp.text[:300]}")
    except Exception as e:
        print(f"[ERROR] Upload exception: {e}")


if __name__ == "__main__":
    print("=" * 55)
    print("EcoStream - Hourly Ingestion Run")
    print(f"UTC time: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')}")
    print("=" * 55)

    df = fetch_live_data()
    print(f"\nFetched {len(df)} valid city records.")
    upload_to_supabase(df)
