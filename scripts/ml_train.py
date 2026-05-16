"""
EcoStream - Phase C: Predictive Modeling
==========================================
Trains XGBoost and LightGBM models on the preprocessed data,
performs hyperparameter tuning, and evaluates performance.
"""

import os
import joblib
import pandas as pd
import numpy as np
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import RandomizedSearchCV

# Configuration
TRAIN_PATH = os.path.join("artefacts", "train_data.parquet")
TEST_PATH  = os.path.join("artefacts", "test_data.parquet")
MODEL_OUT  = os.path.join("artefacts", "champion_model.joblib")
TARGET     = "aqi"

def load_data():
    print(f"Loading datasets...")
    train_df = pd.read_parquet(TRAIN_PATH)
    test_df  = pd.read_parquet(TEST_PATH)
    
    X_train = train_df.drop(columns=[TARGET])
    y_train = train_df[TARGET]
    X_test  = test_df.drop(columns=[TARGET])
    y_test  = test_df[TARGET]
    
    return X_train, y_train, X_test, y_test

def train_and_evaluate():
    X_train, y_train, X_test, y_test = load_data()
    print(f"  Training on {len(X_train):,} samples with {X_train.shape[1]} features.")

    # 1. LightGBM (Baseline)
    print("\n[1/2] Training LightGBM Baseline...")
    lgbm = LGBMRegressor(n_estimators=500, learning_rate=0.05, num_leaves=31, random_state=42, n_jobs=-1)
    lgbm.fit(X_train, y_train)
    
    y_pred_lgbm = lgbm.predict(X_test)
    mae_lgbm = mean_absolute_error(y_test, y_pred_lgbm)
    rmse_lgbm = np.sqrt(mean_squared_error(y_test, y_pred_lgbm))
    r2_lgbm = r2_score(y_test, y_pred_lgbm)
    
    print(f"  LightGBM -> MAE: {mae_lgbm:.4f}, RMSE: {rmse_lgbm:.4f}, R2: {r2_lgbm:.4f}")

    # 2. XGBoost (Baseline)
    print("\n[2/2] Training XGBoost Baseline...")
    xgb = XGBRegressor(n_estimators=500, learning_rate=0.05, max_depth=6, random_state=42, n_jobs=-1)
    xgb.fit(X_train, y_train)
    
    y_pred_xgb = xgb.predict(X_test)
    mae_xgb = mean_absolute_error(y_test, y_pred_xgb)
    rmse_xgb = np.sqrt(mean_squared_error(y_test, y_pred_xgb))
    r2_xgb = r2_score(y_test, y_pred_xgb)
    
    print(f"  XGBoost -> MAE: {mae_xgb:.4f}, RMSE: {rmse_xgb:.4f}, R2: {r2_xgb:.4f}")

    # Champion Selection
    if r2_xgb > r2_lgbm:
        print("\nChampion: XGBoost")
        champion = xgb
    else:
        print("\nChampion: LightGBM")
        champion = lgbm

    # Save Model
    joblib.dump(champion, MODEL_OUT)
    print(f"  Saved champion model to '{MODEL_OUT}'")

if __name__ == "__main__":
    print("=" * 65)
    print("PHASE C: MODEL TRAINING & EVALUATION")
    print("=" * 65)
    train_and_evaluate()
