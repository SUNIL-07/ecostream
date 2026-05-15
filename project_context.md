# EcoStream: Project Context & Progress

## 1. Project Context
**Project:** EcoStream - A Real-Time Scalable Air Quality Analytics & Forecasting Platform.

**Objective:** Build an automated cloud-based data ingestion pipeline, train ML models for predicting a 24-hour window of Air Quality Index (AQI), explain predictions with XAI (SHAP), and visualize everything in an interactive Streamlit dashboard. Focused on 20 major cities across India.

**Tech Stack:**
- **Data APIs:** Open-Meteo Unified Suite (Air Quality API + Weather Archive/ERA5)
- **Database:** Supabase (Cloud PostgreSQL with PostGIS extension)
- **Ingestion:** GitHub Actions (Python scripts running hourly)
- **Data processing & EDA:** pandas, numpy, pyarrow, plotly, seaborn
- **ML & XAI:** scikit-learn, xgboost, lightgbm, shap (TreeSHAP)
- **UI & Deployment:** Streamlit, Streamlit Community Cloud

---

## 2. Current Phase: Phase C (Predictive Modeling & XAI)

- [ ] Train baseline XGBoost and LightGBM models on rtefacts/train_data.parquet
- [ ] Evaluate using MAE, RMSE, and R-squared on rtefacts/test_data.parquet
- [ ] Run TreeSHAP on the champion model to generate SHAP waterfall and summary plots
- [ ] Save serialized champion model for Streamlit deployment
- [ ] Connect Jupyter Notebooks to Supabase for live EDA & correlation analysis

---

## 3. Completed Phases

### Phase A: Engineering Foundation (COMPLETE)
- [x] Designed and deployed the daily_aqi_weather table schema in Supabase PostgreSQL.
  - Used PostGIS GEOGRAPHY(POINT, 4326) for spatial coordinates.
  - Schema tracks 22 variables covering air quality, meteorology, and derived features.
- [x] Built ingestion/fetch_data.py: hourly real-time ingestion for 20 cities.
  - Fetches from Open-Meteo Air Quality API and Forecast API simultaneously.
  - Uses Supabase REST API with on_conflict=city,timestamp UPSERT to prevent duplicates.
  - Configured GitHub Actions (hourly_ingestion.yml) to trigger on cron: 0 * * * *.
- [x] Pushed all code to github.com/SUNIL-07/ecostream (main branch).

**Key scripts:** ingestion/fetch_data.py, .github/workflows/hourly_ingestion.yml

---

### Phase B: Historical Data Engineering (COMPLETE)
The full history pipeline is now complete. Key decisions and resolutions documented below.

#### B.1 Open-Meteo Archive Availability Analysis
Ran a 10-year availability diagnostic across all 23 planned variables. Results:

| Variable Group | Availability Start | Notes |
|---|---|---|
| Core weather (temp, humidity, pressure, wind, etc.) | 2016-01-01 | 100% available across all years |
| Air Quality (AQI, PM2.5, PM10, O3, NO2, SO2, CO, AOD) | 2022-08-04 | Archive did not exist before this date |
| isibility | Never | 100% missing in historical archive |
| uv_index | Never | 100% missing in historical archive |
| oundary_layer_height | 2016 (with gaps) | Missing ~4.8% of rows; all of 2024 missing |

**Resolution:** 
- Set historical start date to 2022-08-05 (earliest AQI archive date).
- Removed isibility and uv_index from schema (ALTER TABLE ... DROP COLUMN).
- Excluded oundary_layer_height from dropna() filter (kept as nullable column).

#### B.2 Per-City Record Availability (2022-08-05 to 2026-05-12)
All 20 cities yield exactly **33,048 valid hourly records** each = **660,960 total** (with 87,360 rows having NULL oundary_layer_height).

#### B.3 Historical Fetch Pipeline
**Script:** scripts/fetch_historical_hourly.py
- Fetches from both Open-Meteo Archive (weather) and Air Quality APIs per city.
- Merges hourly weather with daily 	emp_mean, 	emp_max, 	emp_min broadcast to hourly rows.
- Derives: 	emp_range = temp_max - temp_min, is_weekend, PostGIS EWKT location string.
- Applies dropna() on all columns except oundary_layer_height.
- Rate-limited: 60-second pause between cities to respect Open-Meteo fair-use policy.
- Saves to rtefacts/10yr_hourly_timeline.csv.

**Output:** 826,200 rows (660,960 valid + 165,240 Ahmedabad partial re-fetch rows)

#### B.4 Historical Upload
**Script:** scripts/upload_historical.py
- Reads the CSV and applies the same oundary_layer_height-aware dropna().
- Converts NaN to None via df.replace({np.nan: None}) for valid JSON serialization.
- Uploads in 1,000-row chunks to Supabase REST API with UPSERT.
- **Result:** 824,200 rows successfully uploaded to Supabase.

#### B.5 Live Ingestion Sync
ingestion/fetch_data.py updated to match historical schema exactly:
- Added: erosol_optical_depth, 	emp_mean, 	emp_range, precipitation, solar_radiation, oundary_layer_height, is_weekend, PostGIS location.
- Removed: isibility, uv_index, 	emp_min, 	emp_max.
- Same oundary_layer_height-aware dropna() logic applied.

**Key scripts:** scripts/fetch_historical_hourly.py, scripts/upload_historical.py, ingestion/fetch_data.py, schema.sql

---

### Phase B-ML: Feature Engineering & Preprocessing (COMPLETE)
**Script:** scripts/ml_preprocess.py

#### Input
- Source: rtefacts/10yr_hourly_timeline.csv (826,200 rows, 25 columns)
- Date range: 2022-08-05 to 2026-05-12

#### Columns Dropped
| Column | Reason |
|---|---|
| oundary_layer_height | 100% missing in historical archive |
| isibility | 100% missing (already removed from schema) |
| uv_index | 100% missing (already removed from schema) |
| location (EWKT string) | Replaced by numeric latitude and longitude |
| wind_deg | Replaced by wind_u and wind_v vector components |
| city (string) | Replaced by city_encoded (mean AQI target encoding) |
| 	imestamp | Dropped after extracting all temporal features |
| hour, month | Replaced by sine/cosine cyclical transforms |

#### Features Engineered (52 total)
| Category | Details |
|---|---|
| Spatial | Lat/Lon parsed from PostGIS EWKT string using regex |
| Temporal | hour_sin, hour_cos, month_sin, month_cos, day_of_week, is_weekend |
| Wind vectors | wind_u = wind_speed x cos(rad), wind_v = wind_speed x sin(rad) |
| Weather | One-hot: wx_Clear, wx_Clouds, wx_Rain |
| City encoding | Mean AQI per city (range: Thiruvananthapuram=66.5 to New Delhi=166.3) |
| Lag features | aqi, pm25, pm10 at t-1h, t-3h, t-6h, t-24h (12 features) |
| Rolling stats | aqi, pm25, pm10 rolling mean 3h/24h and std 6h (9 features) |

#### Filters Applied
- dropna() after lag creation removed 480 rows (24h warm-up window) = 0.06% loss
- Clean rows retained: **825,720**

#### Output (Chronological Walk-Forward Split, 80/20 per city)
| File | Rows |
|---|---|
| rtefacts/train_data.parquet | 660,570 |
| rtefacts/test_data.parquet | 165,150 |

---

## 4. Key Code Files

| File | Purpose | Status |
|---|---|---|
| schema.sql | Supabase table definition | Complete |
| ingestion/fetch_data.py | Hourly real-time ingestion (GitHub Actions) | Complete |
| .github/workflows/hourly_ingestion.yml | Cron trigger every hour | Complete |
| scripts/fetch_historical_hourly.py | 3.5-year historical batch fetch | Complete |
| scripts/upload_historical.py | Upload CSV to Supabase via REST | Complete |
| scripts/ml_preprocess.py | Feature engineering + train/test split | Complete |
| rtefacts/train_data.parquet | 660,570 rows, 52 features | Ready |
| rtefacts/test_data.parquet | 165,150 rows, 52 features | Ready |

---

## 5. Future Phases

- **Phase C:** Train XGBoost / LightGBM. Evaluate MAE, R2. Run TreeSHAP.
- **Phase D:** Streamlit dashboard connected to Supabase + serialized model.
