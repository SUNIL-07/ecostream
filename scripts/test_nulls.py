"""
EcoStream ML Preprocessing Pipeline
====================================
Loads raw historical data, performs feature engineering, and outputs
chronological train/test parquet splits ready for XGBoost/LightGBM + SHAP.

Feature Groups:
  - Raw Pollutants  : pm25, pm10, o3, no2, so2, co, aerosol_optical_depth
  - Meteorological  : temperature, temp_range, feels_like, humidity, pressure,
                      wind_u, wind_v, precipitation, solar_radiation, clouds
  - Temporal        : hour_sin, hour_cos, month_sin, month_cos, day_of_week, is_weekend
  - Spatial         : latitude, longitude, city (target-encoded)
  - Lags            : aqi/pm25/pm10 at t-1h, t-3h, t-6h, t-24h
  - Rolling         : aqi/pm25/pm10 rolling mean (3h, 24h), rolling std (6h)

Target: aqi
"""

import os
import sys
import re
import time
import requests
import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

try:
    from dotenv import load_dotenv
    load_dotenv()
    load_dotenv('../.env')
except Exception:
    pass

sys.stdout.reconfigure(line_buffering=True)

# ─── Configuration ─────────────────────────────────────────────────────────────
SUPABASE_URL        = "https://trfetbxovhmbmwgbqdqm.supabase.co"
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or \
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRyZmV0YnhvdmhtYm13Z2JxZHFtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NjM1NjY3MCwiZXhwIjoyMDkxOTMyNjcwfQ.XgrP4c5hniQJbSK87xpEru820e24K9gLebA2bBt-Gb8"
TABLE_NAME          = "daily_aqi_weather"
FALLBACK_CSV        = os.path.join("artefacts", "10yr_hourly_timeline.csv")

TRAIN_OUT   = os.path.join("artefacts", "train_data.parquet")
TEST_OUT    = os.path.join("artefacts", "test_data.parquet")
SCALER_OUT  = os.path.join("artefacts", "scaler.joblib")
IMPUTER_OUT = os.path.join("artefacts", "imputer.joblib")
FEATURES_OUT = os.path.join("artefacts", "features.joblib")

TRAIN_RATIO = 0.80
TARGET_COL  = "aqi"

LAG_COLS          = ["aqi", "pm25", "pm10"]
LAG_HOURS         = [1, 3, 6, 24]
ROLL_COLS         = ["aqi", "pm25", "pm10"]
ROLL_MEAN_WINDOWS = [3, 24]
ROLL_STD_WINDOWS  = [6]

PAGE_SIZE = 1000   # Supabase REST API max rows per request


def fetch_from_supabase():
    """
    Pulls all rows from daily_aqi_weather via paginated Supabase REST API.
    Returns a DataFrame, or None on failure.
    """
    headers = {
        "apikey":        SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type":  "application/json",
    }

    base_url = (
        f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}"
        f"?select=city,location,timestamp,aqi,pm25,pm10,o3,no2,so2,co,"
        f"aerosol_optical_depth,temperature,temp_mean,temp_range,feels_like,"
        f"humidity,pressure,wind_speed,wind_deg,clouds,precipitation,"
        f"solar_radiation,weather_condition,is_weekend"
        f"&order=city,timestamp"
    )

    # --- Get total row count first ---
    total = None
    try:
        probe_headers = headers.copy()
        probe_headers["Prefer"] = "count=exact"
        probe = requests.head(base_url, headers=probe_headers, timeout=30)
        content_range = probe.headers.get("content-range", "")
        total = int(content_range.split("/")[-1]) if "/" in content_range else None
        if total:
            print(f"  Supabase reports {total:,} total rows.")
    except Exception:
        pass

    # --- Paginated fetch ---
    all_frames = []
    offset = 0
    page   = 1

    for _ in range(1):
        url = f"{base_url}&limit={PAGE_SIZE}&offset={offset}"
        for attempt in range(1, 4):
            try:
                resp = requests.get(url, headers=headers, timeout=60)
                if resp.status_code in [200, 206]:
                    break
                print(f"  [WARN] HTTP {resp.status_code} on page {page}, attempt {attempt}")
            except Exception as e:
                print(f"  [WARN] Network error on page {page}, attempt {attempt}: {e}")
            time.sleep(3 * attempt)
        else:
            print(f"  [ERROR] Failed to fetch page {page} after 3 attempts.")
            return None

        batch = resp.json()
        if not batch:
            break

        all_frames.append(pd.DataFrame(batch))
        fetched = offset + len(batch)
        pct     = f"{fetched/total*100:.1f}%" if total else "?"
        print(f"  Page {page:>4} | rows {offset:>7} - {fetched:>7} | {pct}", end="\r")

        if len(batch) < PAGE_SIZE:
            break

        offset += PAGE_SIZE
        page   += 1
        time.sleep(0.1)   # polite pacing

    print()  # newline after progress line
    if not all_frames:
        return None

    return pd.concat(all_frames, ignore_index=True)


# ─── Step 1: Load & Initial Clean ──────────────────────────────────────────────
print("=" * 65)
print("STEP 1 — Loading Data from Supabase")
print("=" * 65)

df = fetch_from_supabase()

if df is None or df.empty:
    print("  [WARN] Supabase pull failed or returned empty. Falling back to local CSV.")
    if not os.path.exists(FALLBACK_CSV):
        print(f"  [ERROR] Fallback CSV also not found: {FALLBACK_CSV}")
        sys.exit(1)
    df = pd.read_csv(FALLBACK_CSV, low_memory=False)
    print(f"  Loaded {len(df):,} rows from local CSV (fallback).")
else:
    print(f"  Pulled {len(df):,} rows x {len(df.columns)} columns from Supabase.")

# Drop boundary_layer_height — entirely null in historical archive
df.drop(columns=["boundary_layer_height"], errors="ignore", inplace=True)
print(f"  Dropped 'boundary_layer_height' column (null in archive).")

# ─── Step 2: Parse Timestamp & Sort ────────────────────────────────────────────
print("\nSTEP 2 — Parsing Timestamps & Sorting")
df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
df = df.sort_values(["city", "timestamp"]).reset_index(drop=True)
print(f"  Date range: {df['timestamp'].min()} -> {df['timestamp'].max()}")

# ─── Step 3: Extract Lat/Lon from PostGIS EWKT ─────────────────────────────────
print("\nSTEP 3 — Extracting Latitude & Longitude from Location String")
# Format: "SRID=4326;POINT(lon lat)"
def parse_ewkt(ewkt_str):
    try:
        coords = re.search(r"POINT\(([^ ]+) ([^ )]+)\)", str(ewkt_str))
        return float(coords.group(1)), float(coords.group(2))  # lon, lat
    except Exception:
        return np.nan, np.nan

df[["longitude", "latitude"]] = pd.DataFrame(
    df["location"].apply(parse_ewkt).tolist(), index=df.index
)
df.drop(columns=["location"], inplace=True)
print(f"  Extracted lat/lon for {df['latitude'].notnull().sum():,} rows.")

# ─── Step 4: Temporal Feature Engineering ─────────────────────────────────────
print("\nSTEP 4 — Temporal Feature Engineering")

df["hour"]        = df["timestamp"].dt.hour
df["month"]       = df["timestamp"].dt.month
df["day_of_week"] = df["timestamp"].dt.dayofweek  # 0=Monday, 6=Sunday

# Cyclical sine/cosine transforms so 23:00 and 00:00 are adjacent
df["hour_sin"]    = np.sin(2 * np.pi * df["hour"]  / 24)
df["hour_cos"]    = np.cos(2 * np.pi * df["hour"]  / 24)
df["month_sin"]   = np.sin(2 * np.pi * df["month"] / 12)
df["month_cos"]   = np.cos(2 * np.pi * df["month"] / 12)

# Drop the raw hour/month now that cyclical versions are created
df.drop(columns=["hour", "month"], inplace=True)

# is_weekend: already exists, cast to int for tree models
df["is_weekend"] = df["is_weekend"].astype(int)
print("  Created: hour_sin, hour_cos, month_sin, month_cos, day_of_week.")

# ─── Step 5: Wind Vector Components ───────────────────────────────────────────
print("\nSTEP 5 — Wind Vector Components (U, V)")
wind_rad = np.deg2rad(df["wind_deg"])
df["wind_u"] = df["wind_speed"] * np.cos(wind_rad)   # East-West
df["wind_v"] = df["wind_speed"] * np.sin(wind_rad)   # North-South
df.drop(columns=["wind_deg"], inplace=True)
print("  Created wind_u, wind_v from wind_deg + wind_speed.")

# ─── Step 6: Encode weather_condition ─────────────────────────────────────────
print("\nSTEP 6 — Encoding 'weather_condition' (One-Hot)")
df = pd.get_dummies(df, columns=["weather_condition"], prefix="wx", drop_first=False)
weather_cols = [c for c in df.columns if c.startswith("wx_")]
print(f"  Created {len(weather_cols)} one-hot columns: {weather_cols}")

# ─── Step 7: City Target Encoding ─────────────────────────────────────────────
print("\nSTEP 7 — City Target Encoding (Mean AQI per City)")
city_target_map = df.groupby("city")[TARGET_COL].mean().to_dict()
df["city_encoded"] = df["city"].map(city_target_map)
df.drop(columns=["city"], inplace=True)
print(f"  Encoded {len(city_target_map)} cities by mean AQI.")
for city, val in sorted(city_target_map.items(), key=lambda x: -x[1]):
    print(f"    {city:<25} -> {val:.1f}")

# ─── Step 8: Lag Features ─────────────────────────────────────────────────────
print("\nSTEP 8 — Lag Features (per city group)")
df = df.sort_values(["city_encoded", "latitude", "longitude", "timestamp"]).reset_index(drop=True)

for col in LAG_COLS:
    for lag in LAG_HOURS:
        lag_name = f"{col}_lag_{lag}h"
        df[lag_name] = df.groupby(
            ["city_encoded", "latitude", "longitude"]
        )[col].shift(lag)
        print(f"  Created {lag_name}")

# ─── Step 9: Rolling Statistics ───────────────────────────────────────────────
print("\nSTEP 9 — Rolling Statistics (per city group)")

for col in ROLL_COLS:
    for w in ROLL_MEAN_WINDOWS:
        roll_name = f"{col}_roll_mean_{w}h"
        df[roll_name] = (
            df.groupby(["city_encoded", "latitude", "longitude"])[col]
            .transform(lambda x: x.shift(1).rolling(window=w, min_periods=1).mean())
        )
        print(f"  Created {roll_name}")

    for w in ROLL_STD_WINDOWS:
        roll_name = f"{col}_roll_std_{w}h"
        df[roll_name] = (
            df.groupby(["city_encoded", "latitude", "longitude"])[col]
            .transform(lambda x: x.shift(1).rolling(window=w, min_periods=1).std())
        )
        print(f"  Created {roll_name}")

# ─── Step 10: Drop Nulls (from lag creation initial window) ───────────────────
print("\nSTEP 10 — Dropping NaN rows from lag/rolling warm-up window")
print("  Nulls found per column:")
null_counts = df.isnull().sum()
for col, count in null_counts[null_counts > 0].items():
    print(f"    {col:<25} : {count:,} ({count/len(df)*100:.1f}%)")

before = len(df)
df = df.fillna(0).dropna()
after = len(df)
print(f"  Dropped {before - after:,} rows ({(before-after)/before*100:.1f}% of total).")
print(f"  Clean rows remaining: {after:,}")

# ─── Step 11: Drop Timestamp (no longer needed as a raw feature) ──────────────
df = df.drop(columns=["timestamp"])

# ─── Step 11: Chronological Train/Test Split (per city) ───────────────────────
print("\nSTEP 11 — Chronological Train/Test Split (80% / 20% per city)")

train_chunks = []
test_chunks  = []

for (city_enc, lat, lon), group in df.groupby(
    ["city_encoded", "latitude", "longitude"], sort=False
):
    group = group.reset_index(drop=True)
    split_idx = int(len(group) * TRAIN_RATIO)
    train_chunks.append(group.iloc[:split_idx])
    test_chunks.append(group.iloc[split_idx:])

train_df = pd.concat(train_chunks).reset_index(drop=True)
test_df  = pd.concat(test_chunks).reset_index(drop=True)

# ─── Step 12: Imputation & Scaling ───────────────────────────────────────────
print("\nSTEP 12 — Imputation & Scaling (StandardScaler)")
feature_cols = [c for c in train_df.columns if c != TARGET_COL]

# Impute missing values (if any survived) using Median
imputer = SimpleImputer(strategy="median")
train_df[feature_cols] = imputer.fit_transform(train_df[feature_cols])
test_df[feature_cols]  = imputer.transform(test_df[feature_cols])

# Scale features to mean=0, std=1
scaler = StandardScaler()
train_df[feature_cols] = scaler.fit_transform(train_df[feature_cols])
test_df[feature_cols]  = scaler.transform(test_df[feature_cols])

# Save transformer objects for inference
joblib.dump(imputer, IMPUTER_OUT)
joblib.dump(scaler, SCALER_OUT)
joblib.dump(feature_cols, FEATURES_OUT)
print(f"  Saved imputer, scaler, and features to 'artefacts/'")

print(f"  TRAIN: {len(train_df):,} rows × {len(train_df.columns)} features")
print(f"  TEST : {len(test_df):,}  rows × {len(test_df.columns)} features")

# ─── Step 13: Save as Parquet ─────────────────────────────────────────────────
print("\nSTEP 13 — Saving Parquet Files (Overwriting)")
train_df.to_parquet(TRAIN_OUT, index=False, engine="pyarrow")
test_df.to_parquet(TEST_OUT,  index=False, engine="pyarrow")
print(f"  Saved -> {TRAIN_OUT}")
print(f"  Saved -> {TEST_OUT}")

# ─── Final Summary ────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("PREPROCESSING COMPLETE")
print("=" * 65)
print(f"  Total features : {len(feature_cols)}")
print(f"  Target         : {TARGET_COL}")
print(f"  Train rows     : {len(train_df):,}")
print(f"  Test rows      : {len(test_df):,}")
print(f"\n  Full feature list (Scaled):")
for i, f in enumerate(sorted(feature_cols), 1):
    print(f"    {i:>3}. {f}")
