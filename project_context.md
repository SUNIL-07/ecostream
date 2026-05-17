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

## 2. Current Phase: Complete (Entering Maintenance Mode)
The initial development of EcoStream (Phases A through D) is now 100% complete. The system is operating autonomously, fetching live data hourly, and retraining the ML model weekly.

---

## 3. Completed Phases

### Phase A: Engineering Foundation (COMPLETE)
- [x] Designed and deployed the `daily_aqi_weather` table schema in Supabase PostgreSQL.
  - Used PostGIS `GEOGRAPHY(POINT, 4326)` for spatial coordinates.
  - Schema tracks 22 variables covering air quality, meteorology, and derived features.
- [x] Built `ingestion/fetch_data.py`: hourly real-time ingestion for 20 cities.
  - Fetches from Open-Meteo Air Quality API and Forecast API simultaneously.
  - Uses Supabase REST API with `on_conflict=city,timestamp` UPSERT to prevent duplicates.
  - Configured GitHub Actions (`hourly_ingestion.yml`) to trigger on `cron: 0 * * * *`.
- [x] Pushed all code to `github.com/SUNIL-07/ecostream` (main branch).

**Key scripts:** `ingestion/fetch_data.py`, `.github/workflows/hourly_ingestion.yml`

---

### Phase B: Historical Data Engineering (COMPLETE)
The full history pipeline is now complete. Key decisions and resolutions documented below.

#### B.1 Open-Meteo Archive Availability Analysis
Ran a 10-year availability diagnostic across all 23 planned variables. Results:

| Variable Group | Availability Start | Notes |
|---|---|---|
| Core weather (temp, humidity, pressure, wind, etc.) | 2016-01-01 | 100% available across all years |
| Air Quality (AQI, PM2.5, PM10, O3, NO2, SO2, CO, AOD) | 2022-08-04 | Archive did not exist before this date |
| `visibility` | Never | 100% missing in historical archive |
| `uv_index` | Never | 100% missing in historical archive |
| `boundary_layer_height` | 2016 (with gaps) | Missing ~4.8% of rows; all of 2024 missing |

**Resolution:** 
- Set historical start date to `2022-08-05` (earliest AQI archive date).
- Removed `visibility` and `uv_index` from schema (`ALTER TABLE ... DROP COLUMN`).
- Excluded `boundary_layer_height` from `dropna()` filter (kept as nullable column).

#### B.2 Per-City Record Availability (2022-08-05 to 2026-05-12)
All 20 cities yield exactly **33,048 valid hourly records** each = **660,960 total**.

#### B.3 Historical Fetch Pipeline
**Script:** `scripts/fetch_historical_hourly.py`
- Fetches from both Open-Meteo Archive (weather) and Air Quality APIs per city.
- Merges hourly weather with daily `temp_mean`, `temp_max`, `temp_min` broadcast to hourly rows.
- Derives: `temp_range = temp_max - temp_min`, `is_weekend`, PostGIS EWKT `location` string.
- Applies `dropna()` on all columns except `boundary_layer_height`.
- Rate-limited: 60-second pause between cities to respect Open-Meteo fair-use policy.

**Output:** `artefacts/10yr_hourly_timeline.csv` (826,200 rows)

#### B.4 Historical Upload
**Script:** `scripts/upload_historical.py`
- Reads the CSV and applies the same `boundary_layer_height`-aware `dropna()`.
- Converts `NaN` to `None` for valid JSON serialization.
- Uploads in 1,000-row chunks to Supabase REST API with UPSERT.
- **Result:** ~824k rows successfully uploaded to Supabase.

---

### Phase B-ML: Feature Engineering & Preprocessing (COMPLETE)
**Script:** `scripts/ml_preprocess.py`

#### Data Sourcing (Supabase Integration)
- **Primary Source:** Pulled directly from Supabase `daily_aqi_weather` table.
- **Method:** Paginated REST API requests (1,000 rows/page) with retry logic.
- **Rows Pulled:** 661,233 records.

#### Columns Dropped
| Column | Reason |
|---|---|
| `boundary_layer_height` | 100% missing in historical archive |
| `location` (EWKT string) | Replaced by numeric `latitude` and `longitude` |
| `wind_deg` | Replaced by `wind_u` and `wind_v` vector components |
| `city` (string) | Replaced by `city_encoded` (mean AQI target encoding) |
| `timestamp` | Dropped after extracting all temporal features |
| `hour`, `month` | Replaced by sine/cosine cyclical transforms |

#### Features Engineered (52 total)
| Category | Details |
|---|---|
| Spatial | Lat/Lon parsed from PostGIS EWKT string using regex |
| Temporal | hour_sin, hour_cos, month_sin, month_cos, day_of_week, is_weekend |
| Wind vectors | `wind_u = wind_speed * cos(rad)`, `wind_v = wind_speed * sin(rad)` |
| Weather | One-hot: `wx_Clear`, `wx_Clouds`, `wx_Rain` |
| City encoding | Mean AQI per city (range: Thiruvananthapuram=66.5 to New Delhi=166.3) |
| Lag features | `aqi`, `pm25`, `pm10` at t-1h, t-3h, t-6h, t-24h (12 features) |
| Rolling stats | `aqi`, `pm25`, `pm10` rolling mean 3h/24h and std 6h (9 features) |

#### Output (Chronological Walk-Forward Split, 80/20 per city)
| File | Rows | Features |
|---|---|---|
| `artefacts/train_data.parquet` | 660,570 | 52 + target |
| `artefacts/test_data.parquet` | 165,150 | 52 + target |

**Rationale:** Chronological split ensures no "look-ahead" bias. The model trains on past data and is tested on future data per city.

---

## 4. Key Code Files

| File | Purpose | Status |
|---|---|---|
| `schema.sql` | Supabase table definition | Complete |
| `ingestion/fetch_data.py` | Hourly real-time ingestion (GitHub Actions) | Complete |
| `.github/workflows/hourly_ingestion.yml` | Cron trigger every hour | Complete |
| `scripts/fetch_historical_hourly.py` | 3.5-year historical batch fetch | Complete |
| `scripts/upload_historical.py` | Upload CSV to Supabase via REST | Complete |
| `scripts/ml_preprocess.py` | Pull from Supabase + Engineering + Split | Complete |
| `artefacts/train_data.parquet` | Training dataset | Ready |
| `artefacts/test_data.parquet` | Testing dataset | Ready |

---

## 5. Phase C: Predictive Modeling & XAI (COMPLETE)

- **Champion Model:** LightGBM Regressor (R² = ~0.998, MAE = ~0.94). Outperformed XGBoost in both training time and predictive accuracy on the 52-feature matrix.
- **Explainability (XAI):** Integrated `shap.TreeExplainer`. The dashboard uses this to generate live "Waterfall Plots" explaining exactly which meteorological or lagged features are pushing the AQI away from the baseline.
- **Model Artifacts:** `champion_model.joblib`, `scaler.joblib`, `imputer.joblib`, and `features.joblib` are saved and continuously overwritten by the retraining pipeline.

---

## 6. Phase D: Deployment & Continual Learning (COMPLETE)

### 6.1 Streamlit Dashboard (`app.py`)
- **Live Trends:** Fetches the last 72 hours of data directly from Supabase to plot dynamic historical trends.
- **XAI Integration:** Displays real-time SHAP analysis for the "Next Hour Forecast", detailing precisely which factors (e.g., `wind_speed`, `pm25_lag_1h`) are driving the pollution.
- **National Overview:** A live Mapbox visualization plotting the AQI across the 20 Indian cities.
- **7-Day Future Forecast:** Fetches 168 hours of future weather/AQI forecast from Open-Meteo on-demand. Passes this through `preprocess_live` to recursively build the lag features, allowing the LightGBM model to predict a highly accurate 1-week AQI trendline with exact IST dates and times.

### 6.2 Continual Learning Pipeline (`ml_retrain.py`)
- **Script:** `scripts/ml_retrain.py` acts as a monolithic MLOps pipeline. It triggers `ml_preprocess.py` to refresh data from Supabase, runs `RandomizedSearchCV` on LightGBM for hyperparameter tuning, and saves the new model.
- **Automation:** Configured `.github/workflows/model_retrain.yml` to trigger every Sunday at midnight (`cron: 0 0 * * 0`). It automatically pushes the updated `joblib` artifacts back to the `main` branch, allowing the Streamlit Cloud deployment to hot-reload the newly tuned model with zero downtime.

---

## 7. Future Scope (Phase E)
- Ensembling with live CPCB (Central Pollution Control Board) ground-sensor data to build a meta-learner comparing satellite (Open-Meteo) vs. Ground (CPCB) readings.
