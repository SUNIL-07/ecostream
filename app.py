"""
EcoStream - Air Quality Forecasting Dashboard
==============================================
Live dashboard for monitoring and predicting AQI across 20 Indian cities.
"""

import streamlit as st
import pandas as pd
import numpy as np
import os
import joblib
import requests
import json
import shap
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Page Config
st.set_page_config(page_title="EcoStream Dashboard", page_icon="🍃", layout="wide")
load_dotenv()

# --- Configuration ---
SUPABASE_URL = "https://trfetbxovhmbmwgbqdqm.supabase.co"
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRyZmV0YnhvdmhtYm13Z2JxZHFtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NjM1NjY3MCwiZXhwIjoyMDkxOTMyNjcwfQ.XgrP4c5hniQJbSK87xpEru820e24K9gLebA2bBt-Gb8"
TABLE_NAME = "daily_aqi_weather"

MODEL_PATH   = "artefacts/champion_model.joblib"
SCALER_PATH  = "artefacts/scaler.joblib"
IMPUTER_PATH = "artefacts/imputer.joblib"
FEATURES_PATH = "artefacts/features.joblib"

CITIES = {
    "New Delhi": (28.6139, 77.2090), "Kolkata": (22.5726, 88.3639), "Mumbai": (19.0760, 72.8777),
    "Bengaluru": (12.9716, 77.5946), "Chennai": (13.0827, 80.2707), "Hyderabad": (17.3850, 78.4867),
    "Ahmedabad": (23.0225, 72.5714), "Surat": (21.1702, 72.8311), "Pune": (18.5204, 73.8567),
    "Lucknow": (26.8467, 80.9462), "Kanpur": (26.4499, 80.3319), "Jaipur": (26.9124, 75.7873),
    "Indore": (22.7196, 75.8577), "Patna": (25.5941, 85.1376), "Nagpur": (21.1458, 79.0882),
    "Thiruvananthapuram": (8.5241, 76.9366), "Bhopal": (23.2599, 77.4126), "Chandigarh": (30.7333, 76.7794),
    "Ludhiana": (30.9010, 75.8573), "Visakhapatnam": (17.6868, 83.2185)
}

# Target encoding from training
CITY_ENCODING = {
    'New Delhi': 166.3, 'Ludhiana': 143.7, 'Kanpur': 137.7, 'Patna': 136.4, 
    'Lucknow': 132.7, 'Kolkata': 125.9, 'Chandigarh': 116.5, 'Mumbai': 116.4, 
    'Surat': 110.4, 'Jaipur': 105.9, 'Nagpur': 104.8, 'Visakhapatnam': 104.4, 
    'Ahmedabad': 89.8, 'Indore': 89.3, 'Hyderabad': 88.3, 'Pune': 87.0, 
    'Bhopal': 86.2, 'Chennai': 75.1, 'Bengaluru': 70.6, 'Thiruvananthapuram': 66.5
}

# --- Helper Functions ---
@st.cache_data(ttl=300)
def fetch_latest_records(city=None, limit=48):
    headers = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
    url = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}?order=timestamp.desc&limit={limit}"
    if city:
        url += f"&city=eq.{city}"
    
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return pd.DataFrame(resp.json())
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_future_forecast(city):
    lat, lon = CITIES[city]
    url_aqi = f'https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&hourly=us_aqi,pm2_5,pm10,ozone,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide,aerosol_optical_depth&past_days=1&forecast_days=7&timezone=Asia%2FKolkata'
    url_w = f'https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,apparent_temperature,relative_humidity_2m,surface_pressure,wind_speed_10m,wind_direction_10m,cloud_cover,weather_code,precipitation,shortwave_radiation,boundary_layer_height&daily=temperature_2m_mean,temperature_2m_max,temperature_2m_min&past_days=1&forecast_days=7&timezone=Asia%2FKolkata'
    
    try:
        res_aqi = requests.get(url_aqi).json()
        res_w = requests.get(url_w).json()
        
        df_aqi = pd.DataFrame(res_aqi['hourly'])
        df_w = pd.DataFrame(res_w['hourly'])
        df_w_daily = pd.DataFrame(res_w['daily'])
        
        df_aqi['time'] = pd.to_datetime(df_aqi['time']).dt.tz_localize('Asia/Kolkata')
        df_w['time'] = pd.to_datetime(df_w['time']).dt.tz_localize('Asia/Kolkata')
        df_w_daily['time'] = pd.to_datetime(df_w_daily['time']).dt.tz_localize('Asia/Kolkata')
        
        df_w_daily['date'] = df_w_daily['time'].dt.date
        df_w['date'] = df_w['time'].dt.date
        
        df = pd.merge(df_aqi, df_w, on='time')
        df = pd.merge(df, df_w_daily[['date', 'temperature_2m_mean', 'temperature_2m_max', 'temperature_2m_min']], on='date')
        
        df['temp_range'] = df['temperature_2m_max'] - df['temperature_2m_min']
        
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
        
        df.rename(columns={
            'time': 'timestamp', 'us_aqi': 'aqi', 'pm2_5': 'pm25', 'ozone': 'o3',
            'nitrogen_dioxide': 'no2', 'sulphur_dioxide': 'so2', 'carbon_monoxide': 'co',
            'temperature_2m': 'temperature', 'temperature_2m_mean': 'temp_mean',
            'apparent_temperature': 'feels_like', 'relative_humidity_2m': 'humidity',
            'surface_pressure': 'pressure', 'wind_speed_10m': 'wind_speed',
            'wind_direction_10m': 'wind_deg', 'cloud_cover': 'clouds',
            'shortwave_radiation': 'solar_radiation', 'weather_code': 'weather_condition'
        }, inplace=True)
        df['weather_condition'] = df['weather_condition'].apply(map_weather_code)
        df['city'] = city
        return df
    except Exception as e:
        print(f"Error fetching forecast: {e}")
        return pd.DataFrame()


def get_aqi_category(aqi):
    if aqi <= 50: return "Good", "#00e400"
    if aqi <= 100: return "Satisfactory", "#92d050"
    if aqi <= 200: return "Moderate", "#ffff00"
    if aqi <= 300: return "Poor", "#ff9900"
    if aqi <= 400: return "Very Poor", "#ff0000"
    return "Severe", "#7e0023"

def preprocess_live(df, return_all_future=False):
    """Applies the same feature engineering as the training script."""
    df = df.copy()
    
    # Ensure timestamp is datetime before accessing .dt accessor
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    if df['timestamp'].dt.tz is None:
        # If naive (from open-meteo), assume it's already localized to IST due to timezone=Asia%2FKolkata
        df['timestamp'] = df['timestamp'].dt.tz_localize('Asia/Kolkata')
    else:
        df['timestamp'] = df['timestamp'].dt.tz_convert("Asia/Kolkata")
    df = df.sort_values('timestamp')

    
    # 1. Lat/Lon
    lat, lon = CITIES[df['city'].iloc[0]]
    df['latitude'] = lat
    df['longitude'] = lon
    
    # 2. Temporal
    df['hour'] = df['timestamp'].dt.hour
    df['month'] = df['timestamp'].dt.month
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    df['is_weekend'] = df['day_of_week'] >= 5
    
    # 3. Wind
    wind_rad = np.radians(df['wind_deg'])
    df['wind_u'] = df['wind_speed'] * np.cos(wind_rad)
    df['wind_v'] = df['wind_speed'] * np.sin(wind_rad)
    
    # 4. Weather OHE
    df['wx_Clear'] = df['weather_condition'] == 'Clear'
    df['wx_Clouds'] = df['weather_condition'] == 'Clouds'
    df['wx_Rain'] = df['weather_condition'].isin(['Rain', 'Drizzle', 'Snow'])
    
    # 5. City Encoding
    df['city_encoded'] = df['city'].map(CITY_ENCODING)
    
    # 6. Lags & Rolling
    for col in ['aqi', 'pm25', 'pm10']:
        for lag in [1, 3, 6, 24]:
            df[f'{col}_lag_{lag}h'] = df[col].shift(lag)
        df[f'{col}_roll_mean_3h'] = df[col].shift(1).rolling(3).mean()
        df[f'{col}_roll_mean_24h'] = df[col].shift(1).rolling(24).mean()
        df[f'{col}_roll_std_6h'] = df[col].shift(1).rolling(6).std()
    
    if return_all_future:
        # Return all rows that are in the future
        now_ist = pd.Timestamp.utcnow().tz_convert("Asia/Kolkata")
        return df[df['timestamp'] >= now_ist].dropna(subset=[f'aqi_lag_{l}h' for l in [1,3,6,24]])
    
    return df.iloc[-1:] # Return only the most recent row for prediction

# --- UI Components ---
st.title("🍃 EcoStream: Live AQI Forecasting & XAI")
st.markdown("Automated Cloud-Native Air Quality Analytics for 20 Indian Cities.")

# Sidebar
st.sidebar.header("🌍 Selection")
selected_city = st.sidebar.selectbox("Choose City", list(CITIES.keys()))
refresh = st.sidebar.button("🔄 Refresh Data")

# Load Models
@st.cache_resource
def load_models():
    return (
        joblib.load(MODEL_PATH), 
        joblib.load(SCALER_PATH), 
        joblib.load(IMPUTER_PATH),
        joblib.load(FEATURES_PATH)
    )

try:
    model, scaler, imputer, features = load_models()
    model_loaded = True
except:
    st.error("Models not found. Please run scripts/ml_preprocess.py and scripts/ml_train.py first.")
    model_loaded = False

# Fetch Data
with st.spinner(f"Fetching data for {selected_city}..."):
    city_data = fetch_latest_records(selected_city, limit=72)

if not city_data.empty and model_loaded:
    latest = city_data.iloc[0]
    cat, color = get_aqi_category(latest['aqi'])
    
    # Header Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Current AQI", f"{latest['aqi']}", delta=None)
        st.markdown(f"Status: **<span style='color:{color}'>{cat}</span>**", unsafe_allow_html=True)
    
    # Preprocess for Prediction
    processed_row = preprocess_live(city_data)
    # Reorder to match training
    input_vector = processed_row[features]
    
    # Predict
    try:
        input_imputed = imputer.transform(input_vector)
        input_scaled = scaler.transform(input_imputed)
        prediction = model.predict(input_scaled)[0]
        with col2:
            st.metric("Next Hour Forecast", f"{prediction:.1f}", delta=f"{prediction - latest['aqi']:.1f}")
    except Exception as e:
        st.warning("Waiting for 24h of history to enable forecast.")
        prediction = None

    with col3:
        st.metric("PM2.5", f"{latest['pm25']} µg/m³")
    with col4:
        st.metric("Humidity", f"{latest['humidity']}%")

    # Main Layout
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Trends", "🧠 Why this Prediction? (XAI)", "🗺️ National Overview", "🔮 7-Day Forecast"])
    
    with tab1:
        st.subheader(f"72-Hour AQI Trend: {selected_city}")
        fig = px.line(city_data, x='timestamp', y='aqi', title="Historical AQI (Live Ingestion)")
        fig.add_hline(y=150, line_dash="dash", line_color="orange", annotation_text="Moderate Limit")
        fig.add_hline(y=300, line_dash="dash", line_color="red", annotation_text="Poor Limit")
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Environmental Parameters")
        fig2 = px.area(city_data, x='timestamp', y=['temperature', 'wind_speed'], title="Weather Context")
        st.plotly_chart(fig2, use_container_width=True)

    with tab2:
        st.subheader("SHAP Explanation (Reasoning)")
        if prediction:
            explainer = shap.TreeExplainer(model)
            shap_vals = explainer.shap_values(input_scaled)
            
            # Waterfall Plot
            st.write("How features pushed the AQI away from the baseline:")
            fig_shap, ax = plt.subplots(figsize=(10, 4))
            shap.waterfall_plot(shap.Explanation(values=shap_vals[0], 
                                                base_values=explainer.expected_value, 
                                                data=input_vector.iloc[0], 
                                                feature_names=features),
                                show=False)
            st.pyplot(fig_shap)
            
            # Insight
            top_feat = features[np.argmax(np.abs(shap_vals[0]))]
            impact = shap_vals[0][np.argmax(np.abs(shap_vals[0]))]
            st.info(f"**Insight:** The most influential factor right now is **{top_feat}**, which is {'increasing' if impact > 0 else 'decreasing'} the AQI by **{abs(impact):.1f}** points.")
        else:
            st.info("Explanation will be available once 24 hours of data are collected for lag calculation.")

    with tab3:
        st.subheader("Live National Map")
        all_latest = fetch_latest_records(limit=200) # Get many, then group
        if not all_latest.empty:
            map_df = all_latest.sort_values('timestamp', ascending=False).drop_duplicates('city')
            # Add coordinates
            map_df['lat'] = map_df['city'].apply(lambda x: CITIES[x][0])
            map_df['lon'] = map_df['city'].apply(lambda x: CITIES[x][1])
            
            st.map(map_df, latitude='lat', longitude='lon', size='aqi', color='#ff0000')
            st.dataframe(map_df[['city', 'aqi', 'weather_condition', 'timestamp']].sort_values('aqi', ascending=False), use_container_width=True)

    with tab4:
        st.subheader("🔮 7-Day Future Forecast")
        st.markdown("Machine Learning predictions mapped exactly onto Open-Meteo's 168-hour weather forecast.")
        
        with st.spinner("Generating 7-day future predictions..."):
            future_raw = fetch_future_forecast(selected_city)
            if not future_raw.empty:
                future_processed = preprocess_live(future_raw, return_all_future=True)
                
                if not future_processed.empty:
                    input_matrix = future_processed[features]
                    try:
                        preds = model.predict(scaler.transform(imputer.transform(input_matrix)))
                        future_processed['predicted_aqi'] = preds
                        
                        fig_future = px.line(future_processed, x='timestamp', y='predicted_aqi', 
                                            title=f"7-Day Predicted AQI Trend: {selected_city}")
                        fig_future.add_hline(y=150, line_dash="dash", line_color="orange", annotation_text="Moderate Limit")
                        fig_future.add_hline(y=300, line_dash="dash", line_color="red", annotation_text="Poor Limit")
                        st.plotly_chart(fig_future, use_container_width=True)
                        
                        st.dataframe(future_processed[['timestamp', 'predicted_aqi', 'temperature', 'weather_condition']]
                                     .sort_values('timestamp').reset_index(drop=True), use_container_width=True)
                    except Exception as e:
                        st.error(f"Prediction failed: {e}")
                else:
                    st.warning("Not enough past data to compute lags for the forecast.")
            else:
                st.error("Failed to fetch forecast from Open-Meteo.")
else:
    st.info("Select a city to begin or ensure the database has data for this region.")

st.markdown("---")
st.caption("EcoStream ML Pipeline - Phase D Output | Data Source: Open-Meteo | Models: LightGBM + SHAP")
