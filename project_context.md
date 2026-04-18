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
- [x] Extracted a sweeping 10-year historical dataset structurally from Open-Meteo systems across all 20 specific locations automatically.
- [x] Designed Python-mapped alignment bridges formatting attributes precisely against our 18-column structural design natively.
- [x] Upserted uniquely spanning 75,180 timeline arrays directly into Supabase Cloud databases safely.

#### Technical Resolutions & Code Changes (Phase B)
During Phase B Data Engineering, several complex extraction barriers were explicitly resolved within the repository codebase:
- **API Rate Limiting Verification:** The massive 10-year JSON pulls initially triggered `HTTP 429 Too Many Requests` on Open-Meteo's Free tier, silencing the last 15 secondary cities natively. **Resolution:** We built a dedicated secondary extractor (`scripts/fetch_missing_15_cities.py`) intentionally embedding `time.sleep(12)` autonomous wait-times to cleanly bypass backend rate limits securely.
- **Null Target Formatting:** Raw missing dates dynamically loaded into Pandas as floating `np.nan` objects, which aggressively throws TypeErrors or inserts corrupted strings into Postgres. **Resolution:** Formatted a rigorous string enforcement code `df = df.where(pd.notnull(df), None)` internally applied throughout `fetch_data.py` and `upload_historical.py`. This forces all disconnected signals to compile perfectly as strictly native PostgreSQL `NULL` constraints.
- **Batched DB Collision Bypassing:** Injecting 75,000+ history matrices natively invites heavy API timeout failures and massive primary-key overlap crashes natively. **Resolution:** Engineered `upload_historical.py` to route strictly through explicit SQLAlchemy PostgreSQL connections natively iterating inside `chunk_size = 2000` context blocks. Appended an explicit `.on_conflict_do_nothing(index_elements=['city', 'timestamp'])` architecture natively preventing massive duplicate overwrites or UUID failures seamlessly.
- **Terminal Parsing Overloads:** Powershell pipelines crashed registering specific UI checkmarks (`[✓]`) natively invoking `UnicodeEncodeError` exceptions upon concluding the upload matrices. **Resolution:** Manually altered all Python execution completion codes into standard ASCII constraints (`[DONE]`) universally resolving execution workflow warnings perfectly.


### Phase A (Engineering)
- [x] Set up Supabase PostgreSQL project and database schema.
- [x] Develop the Python ingestion script to fetch data from WAQI API and OpenWeatherMap API for the 20 targeted cities.
- [x] Establish connection between Python ingestion script and Supabase to write data.
- [x] Configure GitHub Actions workflow to run the ingestion script automatically every hour.

---

## 5. Future Phases
- **Phase D: Deployment & UI Analytics** - Construct and compile a dynamic Streamlit frontend securely interfacing against Supabase databases natively!
