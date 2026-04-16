# EcoStream: Project Context & Progress

## 1. Project Context
**Project:** EcoStream - A Real-Time Scalable Air Quality Analytics & Forecasting Platform.

**Objective:** Build an automated cloud-based data ingestion pipeline, train ML models for predicting a 24-hour window of Air Quality Index (AQI), explain predictions with XAI (SHAP), and visualize everything in an interactive Streamlit dashboard. Focused on 20 major cities across India.

**Tech Stack:**
- **Data APIs:** WAQI (World Air Quality Index), OpenWeatherMap
- **Database:** Supabase (Cloud PostgreSQL)
- **Ingestion:** GitHub Actions (Running Python scripts hourly)
- **Data processing & EDA:** pandas, numpy, sqlalchemy, plotly, seaborn
- **ML & XAI:** scikit-learn, xgboost, lightgbm, shap (TreeSHAP)
- **UI & Deployment:** Streamlit, Streamlit Community Cloud

---

## 2. Progress So Far
- **Project Initiation:** Finalized project scope and problem statement.
- **Goal Setting:** Defined S.M.A.R.T objectives and a structured Phased Methodology.
- **Architecture Finalization:** Clarified technical infrastructure choices (Supabase for DB, GitHub Actions for orchestration, WAQI/OpenWeatherMap for data).
- **Documentation:** Created the core `Project_Document.md` detailing the objectives, stack, and modeling strategy.

---

## 3. Current Phase To-Dos: Phase A (Engineering)
*The Foundation phase involves setting up the data pipeline.*

- [ ] Set up Supabase PostgreSQL project and database schema.
- [ ] Develop the Python ingestion script to fetch data from WAQI API and OpenWeatherMap API for the 20 targeted cities.
- [ ] Establish connection between Python ingestion script and Supabase to write data.
- [ ] Configure GitHub Actions workflow to run the ingestion script automatically every hour.

---

## 4. Future Phases
- **Phase B: Empirical Analytics (EDA)** - Extract data, perform geospatial/temporal analysis, analyze lag features.
- **Phase C: Predictive Intelligence & XAI** - Build feature pipelines, train champion ML models (XGBoost/LightGBM/RF), apply TreeSHAP for explainability.
- **Phase D: Deployment & Communication** - Build and deploy Streamlit application connected to Supabase and serialized ML model.
