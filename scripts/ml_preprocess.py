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
import numpy as np
import pandas as pd

sys.stdout.reconfigure(line_buffering=True)

# ─── Configuration ─────────────────────────────────────────────────────────────
INPUT_CSV   = os.path.join("artefacts", "10yr_hourly_timeline.csv")
TRAIN_OUT   = os.path.join("artefacts", "train_data.parquet")
TEST_OUT    = os.path.join("artefacts", "test_data.parquet")

TRAIN_RATIO = 0.80   # 80% train / 20% test, chronological per city
TARGET_COL  = "aqi"

LAG_COLS    = ["aqi", "pm25", "pm10"]
LAG_HOURS   = [1, 3, 6, 24]

ROLL_COLS   = ["aqi", "pm25", "pm10"]
ROLL_MEAN_WINDOWS = [3, 24]   # hours
ROLL_STD_WINDOWS  = [6]       # hours

# ─── Step 1: Load & Initial Clean ──────────────────────────────────────────────
print("=" * 65)
print("STEP 1 — Loading Data")
print("=" * 65)

if not os.path.exists(INPUT_CSV):
    print(f"[ERROR] Input file not found: {INPUT_CSV}")
    sys.exit(1)

df = pd.read_csv(INPUT_CSV, low_memory=False)
print(f"  Loaded {len(df):,} rows × {len(df.columns)} columns")

# Drop boundary_layer_height — entirely null in historical archive
df.drop(columns=["boundary_layer_height"], errors="ignore", inplace=True)
print(f"  Dropped 'boundary_layer_height' (100% missing in archive).")

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
df = df.groupby(["city_encoded", "latitude", "longitude"], group_keys=False).apply(
    lambda g: g.sort_values("timestamp")
)

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
before = len(df)
df = df.dropna()
after = len(df)
print(f"  Dropped {before - after:,} rows ({(before-after)/before*100:.1f}% of total).")
print(f"  Clean rows remaining: {after:,}")

# ─── Step 11: Drop Timestamp (no longer needed as a raw feature) ──────────────
df = df.drop(columns=["timestamp"])

# ─── Step 12: Chronological Train/Test Split (per city) ───────────────────────
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
    print(
        f"  city_enc={city_enc:.1f} | lat={lat} | "
        f"train={split_idx:,} | test={len(group)-split_idx:,}"
    )

train_df = pd.concat(train_chunks).reset_index(drop=True)
test_df  = pd.concat(test_chunks).reset_index(drop=True)

print(f"\n  TRAIN: {len(train_df):,} rows × {len(train_df.columns)} features")
print(f"  TEST : {len(test_df):,}  rows × {len(test_df.columns)} features")

# ─── Step 13: Save as Parquet ─────────────────────────────────────────────────
print("\nSTEP 12 — Saving Parquet Files")
train_df.to_parquet(TRAIN_OUT, index=False, engine="pyarrow")
test_df.to_parquet(TEST_OUT,  index=False, engine="pyarrow")
print(f"  Saved -> {TRAIN_OUT}")
print(f"  Saved -> {TEST_OUT}")

# ─── Final Summary ────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("PREPROCESSING COMPLETE")
print("=" * 65)
feature_cols = [c for c in train_df.columns if c != TARGET_COL]
print(f"  Total features : {len(feature_cols)}")
print(f"  Target         : {TARGET_COL}")
print(f"  Train rows     : {len(train_df):,}")
print(f"  Test rows      : {len(test_df):,}")
print(f"\n  Full feature list:")
for i, f in enumerate(sorted(feature_cols), 1):
    print(f"    {i:>3}. {f}")
