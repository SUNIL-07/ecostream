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
- **Phase A Complete:** Successfully built and deployed an 18-attribute Super-Schema via a Python auto-ingestion pipeline securely to GitHub Actions!

---

## 3. Current Phase To-Dos: Phase C (Exploration & Predictive Modeling)
*We now dive into extracting raw patterns systematically to build our core ML engine metrics.*

- [ ] Connect Jupyter Notebooks to Supabase arrays and perform robust EDA natively.
- [ ] Check correlation matrices specifically looking at PM2.5/AQI dependencies against Meteorological features natively.
- [ ] Construct the ML modeling pipeline framework securely (XGBoost vs LightGBM architecture comparisons).
- [ ] Execute TreeSHAP internally to calculate robust Explainable AI intelligence rules. 
- [ ] Save the champion pipeline securely as serialization arrays for Streamlit cloud!

---

## 4. Completed Phases
### Phase B (Empirical Analytics & Deep Extraction)
- [x] Extracted a 10-year pure-hourly historical framework natively fetching exactly 1.5M absolute timelines dynamically bypassing daily averaging structures.
- [x] Re-architected dual-API endpoint strings explicitly connecting simultaneous Daily parameters mathematically broadcasting limits back into exact Hourly constraints identically matching live Webhooks!
- [x] Cleanly processed and successfully uploaded over **616,056 strictly-filtered arrays** securely mapping pure sensors into Supabase completely dropping faulty timelines!

#### Technical Resolutions & Code Changes (Phase B)
During Phase B Data Engineering, massive structural optimizations completely scaled the architecture natively:
- **Pure Hourly Granularity Shift:** The initial extraction models mathematically utilized `.groupby('date')` aggregating metrics cleanly but losing prediction depth. **Resolution:** Dismantled Pandas aggregations comprehensively stringing Open-Meteo models directly to `timestamp` boundaries uniquely boosting schema scale organically from exactly 27,000 dates seamlessly into 1.5 Million nested hourly combinations directly!
- **Dynamic Dual-API Mapping:** Conventional ERA5 hourly sets entirely miss internal `temp_min` and `temp_max` limitations generating database crashes natively. **Resolution:** Hooked exact URL parameters commanding APIs cleanly output both `Daily` limits natively and mapped them structurally onto all 24 parallel `Hourly` integers resolving structural mismatches seamlessly cleanly avoiding secondary API expenses!
- **Strict ML Target Quality Filtering:** Older matrices mathematically returned zero AQI metrics triggering corrupt machine learning baselines natively. **Resolution:** Configured pure structural barriers natively hardcoding `df = df.dropna(subset=['aqi'])` universally purging 64% of obsolete disconnected limits before database integrations natively cleanly stabilizing targets.
- **Extreme Pipeline Array Chunking:** Hooking exactly 616,000 arrays linearly across Postgres API arrays causes internal memory timeout exceptions safely natively. **Resolution:** Vastly upscaled explicit SQLAlchemy upload limitations natively jumping `chunk_size` from 2,000 integers to 10,000 limits dynamically securely tracking 500,000 lines cleanly effectively reducing cloud-load entirely within a strict 3-minute window natively!
- **Infinite Target Bridges:** Earlier execution scripts hardcoded strict end-dates statically paralyzing infinite collection frameworks safely natively. **Resolution:** Reprogrammed timeline models structurally integrating `datetime.now()` natively permanently closing boundaries directly bridging exactly into `fetch_data.py` live GitHub webhooks securely without gaps!


### Phase A (Engineering)
- [x] Set up Supabase PostgreSQL project and database schema.
- [x] Develop the Python ingestion script to fetch data from WAQI API and OpenWeatherMap API for the 20 targeted cities.
- [x] Establish connection between Python ingestion script and Supabase to write data.
- [x] Configure GitHub Actions workflow to run the ingestion script automatically every hour.

---

## 5. Future Phases
- **Phase D: Deployment & UI Analytics** - Construct and compile a dynamic Streamlit frontend securely interfacing against Supabase databases natively!
