# Project Document: EcoStream
### Subtitle: A Real-Time Scalable Air Quality Analytics & Forecasting Platform

## 1. Problem Statement
Urban air quality is deteriorating globally, leading to significant public health risks. While raw data is increasingly available via open APIs, decision-makers and citizens lack a unified, real-time platform that translates high-velocity data into actionable insights. Existing solutions provide historical snapshots but fail to offer interpretable 24-hour forecasts that explain *why* pollution spikes occur (e.g., the influence of humidity vs. temperature). EcoStream bridges this gap by providing an always-on, predictive, and interpretable platform focused on 20 major cities across India.

## 2. S.M.A.R.T. Objectives
*   **O1 (Specific & Time-bound):** Build an automated cloud-based data ingestion pipeline using GitHub Actions to fetch and store real-time $PM_{2.5}$, $NO_2$, and $O_3$ data (via WAQI API) and weather data (via OpenWeatherMap API) for 20 Indian cities hourly into a Supabase PostgreSQL database.
*   **O2 (Measurable):** Perform automated Geospatial and Temporal Data Pre-processing & EDA to identify daily and seasonal pollution cycles and feature engineering for multidimensional time-series data.
*   **O3 (Achievable):** Evaluate 6 modeling architectures and train the 3 best-performing machine learning models for forecasting a rolling 24-hour window of AQI. 
*   **O4 (Relevant):** Implement Explainable AI (XAI) using SHAP values to identify and visualize the impact of weather and temporal variables on pollution spikes for a common audience.
*   **O5 (Time-bound):** Deploy an interactive Streamlit dashboard featuring live tracking, forecast visualizations, and automated interpretability charts.

## 3. Technology Stack
*   **Data Sources:** WAQI (World Air Quality Index) API & OpenWeatherMap API.
*   **Database:** Supabase (Cloud PostgreSQL).
*   **Ingestion & Orchestration:** GitHub Actions running a Python ingestion script every hour.
*   **Data Processing:** `pandas`, `numpy`, `sqlalchemy`.
*   **Exploratory Data Analysis:** `plotly.express`, `seaborn`, `matplotlib`.
*   **Machine Learning framework:** `scikit-learn`, `xgboost`, `lightgbm`.
*   **Interpretability (XAI):** `shap` (TreeSHAP).
*   **Deployment UI:** `streamlit`, Streamlit Community Cloud.

## 4. Modeling Strategy & Explainability
Handling 20 cities with multidimensional time-series data requires robust models. We will evaluate 6 architectures:
1.  **XGBoost:** Gradient boosting (Excellent for tabular time-series).
2.  **LightGBM:** Fast, distributed gradient boosting.
3.  **Random Forest:** Ensemble bagging baseline.
4.  **Prophet (Meta):** Additive seasonality model.
5.  **SARIMAX:** Traditional statistical model with exogenous variables (weather).
6.  **Temporal Fusion Transformer (TFT):** Complex deep learning for multi-horizon forecasting.

**Selection:** 
We will train the top 3 best-suited models that integrate well with Explainable AI: **XGBoost, LightGBM, and Random Forest**. These tree-based algorithms integrate natively with **TreeSHAP**, allowing us to generate highly understandable charts (e.g., "High humidity increased the AQI prediction by 20 points today").
*Note on the 20 cities:* We will use a global modeling approach where `city_name` (or coordinates) is encoded as a categorical feature, allowing a single robust model to learn from cross-city patterns.

**City List:**
1.  **New Delhi**: (28.6139, 77.2090)
2.  **Kolkata**: (22.5726, 88.3639)
3.  **Mumbai**: (19.0760, 72.8777)
4.  **Bengaluru**: (12.9716, 77.5946)
5.  **Chennai**: (13.0827, 80.2707)
6.  **Hyderabad**: (17.3850, 78.4867)
7.  **Ahmedabad**: (23.0225, 72.5714)
8.  **Surat**: (21.1702, 72.8311)
9.  **Pune**: (18.5204, 73.8567)
10. **Lucknow**: (26.8467, 80.9462)
11. **Kanpur**: (26.4499, 80.3319)
12. **Jaipur**: (26.9124, 75.7873)
13. **Indore**: (22.7196, 75.8577)
14. **Patna**: (25.5941, 85.1376)
15. **Nagpur**: (21.1458, 79.0882)
16. **Thiruvananthapuram**: (8.5241, 76.9366)
17. **Bhopal**: (23.2599, 77.4126)
18. **Chandigarh**: (30.7333, 76.7794)
19. **Ludhiana**: (30.9010, 75.8573)
20. **Visakhapatnam**: (17.6868, 83.2185)

## 5. Phased Methodology
*   **Phase A: Engineering (The Foundation):** Setup Supabase. Create the hourly Python ingestion script. Configure GitHub Actions to run the script and push data to Supabase 24/7.
*   **Phase B: Empirical Analytics (EDA):** Extract multidimensional data directly from Supabase to local Jupyter Notebooks. Analyze lag features, correlation matrices, and time-of-day impacts.
*   **Phase C: Predictive Intelligence & XAI:** Build feature pipelines. Train XGBoost, LightGBM, and RF. Evaluate models using MAE and RMSE. Apply SHAP to the champion model to extract plain-text or visual explanations.
*   **Phase D: Deployment & Communication:** Develop a Streamlit application connected directly to Supabase and the serialized Champion model. Publish via Streamlit Cloud for public access.

---

## 6. Phase B: Feature Engineering & Preprocessing Report

*Script:* scripts/ml_preprocess.py | *Completed:* 2026-05-15

### 6.1 Data Source

| Property | Value |
|---|---|
| Source file | rtefacts/10yr_hourly_timeline.csv |
| Raw rows loaded | 826,200 |
| Raw columns | 25 |
| Date range | 2022-08-05 to 2026-05-12 |
| Cities | 20 Indian cities |
| Granularity | Hourly |

### 6.2 Column Drops & Filters Applied

| Column | Action | Reason |
|---|---|---|
| oundary_layer_height | Dropped | 100% missing in Open-Meteo historical archive |
| isibility | Dropped (schema-level) | 100% missing in Open-Meteo historical archive |
| uv_index | Dropped (schema-level) | 100% missing in Open-Meteo historical archive |
| location (EWKT string) | Replaced | Parsed into numeric latitude and longitude columns |
| wind_deg | Replaced | Decomposed into wind_u and wind_v vector components |
| city (string) | Replaced | Target-encoded into city_encoded (mean AQI per city) |
| 	imestamp | Dropped post-engineering | All temporal info extracted into derived features |
| hour, month | Dropped | Replaced by cyclical sine/cosine transforms |

### 6.3 Feature Engineering Steps

#### A. Spatial: Lat/Lon Extraction
- Input: PostGIS EWKT string SRID=4326;POINT(lon lat) in location column.
- Output: Two new numeric columns longitude and latitude.
- Method: Regex parse on the POINT(...) pattern.

#### B. Temporal Features: Cyclical Transforms

| Feature | Formula | Captures |
|---|---|---|
| hour_sin | sin(2pi x hour/24) | Daily cycle continuity |
| hour_cos | cos(2pi x hour/24) | Daily cycle continuity |
| month_sin | sin(2pi x month/12) | Seasonal cycle continuity |
| month_cos | cos(2pi x month/12) | Seasonal cycle continuity |
| day_of_week | timestamp.dayofweek (0=Mon) | Weekly traffic patterns |
| is_weekend | Pre-existing, cast to int | Industrial/traffic proxy |

#### C. Wind Vector Decomposition
- wind_u = wind_speed x cos(wind_rad) (East-West component)
- wind_v = wind_speed x sin(wind_rad) (North-South component)

#### D. Weather Condition One-Hot Encoding
weather_condition encoded into: wx_Clear, wx_Clouds, wx_Rain

#### E. City Target Encoding (Mean AQI)

| City | Encoded Value |
|---|---|
| New Delhi | 166.3 |
| Ludhiana | 143.7 |
| Kanpur | 137.7 |
| Patna | 136.4 |
| Lucknow | 132.7 |
| Kolkata | 125.9 |
| Chandigarh | 116.5 |
| Mumbai | 116.4 |
| Surat | 110.4 |
| Jaipur | 105.9 |
| Nagpur | 104.8 |
| Visakhapatnam | 104.4 |
| Ahmedabad | 89.8 |
| Indore | 89.3 |
| Hyderabad | 88.3 |
| Pune | 87.0 |
| Bhopal | 86.2 |
| Chennai | 75.1 |
| Bengaluru | 70.6 |
| Thiruvananthapuram | 66.5 |

#### F. Lag Features (Autocorrelation Memory)
Calculated per city group, chronologically sorted to prevent cross-city contamination.

| Variable | Lags Created |
|---|---|
| qi | aqi_lag_1h, aqi_lag_3h, aqi_lag_6h, aqi_lag_24h |
| pm25 | pm25_lag_1h, pm25_lag_3h, pm25_lag_6h, pm25_lag_24h |
| pm10 | pm10_lag_1h, pm10_lag_3h, pm10_lag_6h, pm10_lag_24h |

#### G. Rolling Statistics (Trend & Volatility)
Computed using shift(1) before the rolling window to prevent look-ahead leakage.

| Feature | Window | Purpose |
|---|---|---|
| *_roll_mean_3h | 3h | Short-term trend smoothing |
| *_roll_mean_24h | 24h | Diurnal baseline reference |
| *_roll_std_6h | 6h | Volatility / spike detection |

Applied to: qi, pm25, pm10 (9 features total)

### 6.4 NaN Filtering After Engineering

| Stage | Rows |
|---|---|
| After lag/rolling creation | 826,200 |
| Dropped (24h lag warm-up, 0.06%) | 480 |
| Clean rows retained | 825,720 |

### 6.5 Final Feature Set: 52 Features + 1 Target

| Category | Features | Count |
|---|---|---|
| Raw Pollutants | pm25, pm10, o3, no2, so2, co, aerosol_optical_depth | 7 |
| Meteorological | temperature, temp_mean, temp_range, feels_like, humidity, pressure, wind_speed, wind_u, wind_v, precipitation, solar_radiation, clouds | 12 |
| Temporal | hour_sin, hour_cos, month_sin, month_cos, day_of_week, is_weekend | 6 |
| Spatial | latitude, longitude, city_encoded | 3 |
| Lag Features | 3 variables x 4 horizons (1h, 3h, 6h, 24h) | 12 |
| Rolling Stats | 3 variables x 3 statistics (mean 3h, mean 24h, std 6h) | 9 |
| Weather One-Hot | wx_Clear, wx_Clouds, wx_Rain | 3 |
| **Total** | | **52** |

**Target variable:** qi

### 6.6 Chronological Train/Test Split

Split performed per city group using walk-forward validation. No random shuffle — strictly 80% earliest data for training and 20% latest for testing, per city.

| Split | Rows | Output File |
|---|---|---|
| Training | 660,570 | rtefacts/train_data.parquet |
| Test | 165,150 | rtefacts/test_data.parquet |
| Total | 825,720 | |

**Note:** Chronological split is mandatory for time-series data. Random splits cause temporal leakage where the model sees future data during training, producing artificially inflated metrics that do not reflect real-world performance.
