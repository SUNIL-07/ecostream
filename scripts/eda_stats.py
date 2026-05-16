"""
EcoStream - Phase B: Numerical Statistical Analysis
=====================================================
Analyzes the preprocessed training data for statistical insights,
correlations, and data quality metrics.
"""

import os
import pandas as pd
import numpy as np

# Load preprocessed training data
TRAIN_PATH = os.path.join("artefacts", "train_data.parquet")

def run_analysis():
    print("=" * 65)
    print("PHASE B: NUMERICAL STATISTICAL ANALYSIS")
    print("=" * 65)

    if not os.path.exists(TRAIN_PATH):
        print(f"[ERROR] Training data not found at {TRAIN_PATH}")
        return

    df = pd.read_parquet(TRAIN_PATH)
    print(f"  Loaded {len(df):,} rows for analysis.")

    # 1. Descriptive Statistics
    print("\n1. DESCRIPTIVE STATISTICS (Sample of Key Features)")
    key_features = ['aqi', 'pm25', 'pm10', 'temperature', 'humidity', 'wind_speed', 'aerosol_optical_depth']
    # Filter to only show these if they exist (they should be scaled, but we want to see the spread)
    stats = df[key_features].describe().T
    print(stats[['mean', 'std', 'min', '50%', 'max']])

    # 2. Correlation Analysis (Target: AQI)
    print("\n2. TOP 15 CORRELATIONS WITH AQI")
    corr = df.corr()[['aqi']].sort_values(by='aqi', ascending=False)
    print(corr.head(16))  # 16 to include aqi itself

    print("\n3. INVERSE CORRELATIONS WITH AQI")
    print(corr.tail(10))

    # 4. Statistical Observations
    print("\n4. KEY OBSERVATIONS")
    
    # Check for features with very low variance (potential candidates for removal)
    low_variance = df.std()[df.std() < 0.01].index.tolist()
    if low_variance:
        print(f"  - Low variance features detected: {low_variance}")
    else:
        print("  - All features show healthy variance (scaled).")

    # High Correlation Redundancy Check
    high_corr_pairs = []
    corr_matrix = df.corr().abs()
    upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    
    for col in upper.columns:
        redundant = upper.index[upper[col] > 0.95].tolist()
        for r in redundant:
            high_corr_pairs.append((col, r, upper.loc[r, col]))

    if high_corr_pairs:
        print("\n  - Potential Redundant Features (>0.95 Correlation):")
        for p1, p2, val in high_corr_pairs:
            print(f"    * {p1} vs {p2}: {val:.4f}")
    
    # AQI Drivers
    top_pollutant = corr.index[1] # index 0 is aqi
    print(f"\n  - Primary AQI Driver: {top_pollutant} (Corr: {corr.loc[top_pollutant, 'aqi']:.4f})")
    
    neg_driver = corr.index[-1]
    print(f"  - Strongest Negative Correlation: {neg_driver} (Corr: {corr.loc[neg_driver, 'aqi']:.4f})")

if __name__ == "__main__":
    run_analysis()
