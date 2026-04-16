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

## 5. Phased Methodology
*   **Phase A: Engineering (The Foundation):** Setup Supabase. Create the hourly Python ingestion script. Configure GitHub Actions to run the script and push data to Supabase 24/7.
*   **Phase B: Empirical Analytics (EDA):** Extract multidimensional data directly from Supabase to local Jupyter Notebooks. Analyze lag features, correlation matrices, and time-of-day impacts.
*   **Phase C: Predictive Intelligence & XAI:** Build feature pipelines. Train XGBoost, LightGBM, and RF. Evaluate models using MAE and RMSE. Apply SHAP to the champion model to extract plain-text or visual explanations.
*   **Phase D: Deployment & Communication:** Develop a Streamlit application connected directly to Supabase and the serialized Champion model. Publish via Streamlit Cloud for public access.
