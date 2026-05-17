"""
EcoStream ML Retraining Pipeline
================================
Automated script for weekly model retraining.
1. Executes ml_preprocess.py to pull the latest live + historical data from Supabase.
2. Loads the refreshed train/test datasets.
3. Performs RandomizedSearchCV to find the optimal LightGBM hyperparameters.
4. Saves the new champion model for immediate use in the Streamlit dashboard.
"""

import os
import sys
import subprocess
import joblib
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import RandomizedSearchCV
from sklearn.metrics import mean_absolute_error, r2_score

# Configuration
TRAIN_PATH = os.path.join("artefacts", "train_data.parquet")
TEST_PATH = os.path.join("artefacts", "test_data.parquet")
MODEL_OUT = os.path.join("artefacts", "champion_model.joblib")
TARGET = "aqi"

def run_preprocessing():
    print("=" * 65)
    print("STEP 1 — Triggering Data Refresh (ml_preprocess.py)")
    print("=" * 65)
    try:
        subprocess.run([sys.executable, "scripts/ml_preprocess.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Preprocessing failed. Aborting retrain.")
        sys.exit(1)

def retrain_model():
    print("\n" + "=" * 65)
    print("STEP 2 — Hyperparameter Tuning & Retraining (LightGBM)")
    print("=" * 65)
    
    print("Loading refreshed datasets...")
    train_df = pd.read_parquet(TRAIN_PATH)
    test_df = pd.read_parquet(TEST_PATH)
    
    X_train = train_df.drop(columns=[TARGET])
    y_train = train_df[TARGET]
    X_test = test_df.drop(columns=[TARGET])
    y_test = test_df[TARGET]
    
    print(f"  Training on {len(X_train):,} samples with {len(X_train.columns)} features.")
    
    # Define hyperparameter grid for LightGBM
    param_dist = {
        'learning_rate': [0.01, 0.05, 0.1, 0.2],
        'num_leaves': [31, 50, 70, 100],
        'max_depth': [-1, 7, 10, 15],
        'min_child_samples': [10, 20, 50, 100],
        'subsample': [0.8, 0.9, 1.0],
        'colsample_bytree': [0.8, 0.9, 1.0]
    }
    
    base_lgbm = lgb.LGBMRegressor(
        n_estimators=100, 
        random_state=42, 
        n_jobs=-1,
        verbose=-1
    )
    
    print("\nStarting RandomizedSearchCV (3 folds, 10 iterations)...")
    random_search = RandomizedSearchCV(
        estimator=base_lgbm,
        param_distributions=param_dist,
        n_iter=10,
        scoring='r2',
        cv=3,
        random_state=42,
        n_jobs=-1,
        verbose=1
    )
    
    random_search.fit(X_train, y_train)
    
    best_model = random_search.best_estimator_
    print(f"\n[BEST HYPERPARAMETERS] {random_search.best_params_}")
    
    print("\nEvaluating Tuned Champion Model on Test Set...")
    y_pred = best_model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    print(f"  -> MAE: {mae:.4f}")
    print(f"  -> R2:  {r2:.4f}")
    
    print(f"\nSaving new champion model to {MODEL_OUT}...")
    joblib.dump(best_model, MODEL_OUT)
    print("Retraining completed successfully!")

if __name__ == "__main__":
    run_preprocessing()
    retrain_model()
