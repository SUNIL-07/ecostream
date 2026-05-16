"""
EcoStream - Phase C: XAI (SHAP)
===============================
Generates global and local explanations for the champion model
using SHAP (SHapley Additive exPlanations).
"""

import os
import joblib
import pandas as pd
import numpy as np
import shap
import matplotlib.pyplot as plt

# Configuration
TEST_PATH   = os.path.join("artefacts", "test_data.parquet")
MODEL_PATH  = os.path.join("artefacts", "champion_model.joblib")
OUTPUT_DIR  = os.path.join("artefacts", "viz")
TARGET      = "aqi"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def run_explainability():
    print("=" * 65)
    print("PHASE C: EXPLAINABLE AI (SHAP)")
    print("=" * 65)

    if not os.path.exists(MODEL_PATH):
        print(f"[ERROR] Model not found at {MODEL_PATH}")
        return

    # Load data and model
    print("Loading model and data...")
    model = joblib.load(MODEL_PATH)
    df_test = pd.read_parquet(TEST_PATH)
    
    X_test = df_test.drop(columns=[TARGET])
    
    # We use a sample for SHAP to speed up calculation
    # For Tree models, TreeExplainer is fast, but 165k rows is still a lot
    X_sample = X_test.sample(1000, random_state=42)

    print("Calculating SHAP values (TreeExplainer)...")
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_sample)

    # 1. Summary Plot (Global Importance)
    print("  Generating SHAP Summary Plot...")
    plt.figure(figsize=(10, 8))
    shap.summary_plot(shap_values, X_sample, show=False)
    plt.title("SHAP Feature Importance (Global)")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "shap_summary.png"))
    plt.close()

    # 2. Local Explanation (Waterfall for a high AQI case)
    print("  Generating Local Waterfall Explanation (High AQI Case)...")
    # Find a record with high AQI in the sample
    high_idx = X_sample.index[df_test.loc[X_sample.index, TARGET].argmax()]
    # Get the relative index in X_sample
    rel_idx = X_sample.index.get_loc(high_idx)
    
    plt.figure(figsize=(12, 6))
    shap.waterfall_plot(shap.Explanation(values=shap_values[rel_idx], 
                                        base_values=explainer.expected_value, 
                                        data=X_sample.iloc[rel_idx], 
                                        feature_names=X_sample.columns),
                        show=False)
    plt.title(f"AQI Explanation for High Pollution Event (Index {high_idx})")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "shap_waterfall_high.png"))
    plt.close()

    # 3. Decision Maker Logic (Alert Threshold)
    print("\n[ALERT LOGIC SIMULATION]")
    # If prediction > threshold or delta > threshold
    sample_preds = model.predict(X_sample)
    threshold = 150 # example hazardous threshold
    high_events = np.where(sample_preds > threshold)[0]
    
    if len(high_events) > 0:
        event_idx = high_events[0]
        actual_val = sample_preds[event_idx]
        print(f"  - ALERT TRIGGERED: Predicted AQI {actual_val:.1f} exceeds threshold ({threshold})")
        
        # Extract top 3 drivers for this alert
        sv = shap_values[event_idx]
        top_idx = np.argsort(np.abs(sv))[-3:][::-1]
        print(f"  - Primary Drivers:")
        for idx in top_idx:
            feat = X_sample.columns[idx]
            impact = sv[idx]
            print(f"    * {feat}: {'Increased' if impact > 0 else 'Decreased'} AQI by {impact:.1f}")

    print(f"\nSHAP visualizations saved to '{OUTPUT_DIR}/'")

if __name__ == "__main__":
    run_explainability()
