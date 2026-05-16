"""
EcoStream - Phase B: Data Visualization
=========================================
Generates visual insights from the training data:
1. Correlation Heatmap
2. Pollutant Distributions
3. Time-of-Day Trends
4. Wind Impact Analysis
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Load preprocessed training data
TRAIN_PATH = os.path.join("artefacts", "train_data.parquet")
OUTPUT_DIR = os.path.join("artefacts", "viz")

os.makedirs(OUTPUT_DIR, exist_ok=True)

def run_visualizations():
    print("=" * 65)
    print("PHASE B: DATA VISUALIZATION")
    print("=" * 65)

    if not os.path.exists(TRAIN_PATH):
        print(f"[ERROR] Training data not found at {TRAIN_PATH}")
        return

    df = pd.read_parquet(TRAIN_PATH)
    print(f"  Loaded {len(df):,} rows for visualization.")

    # 1. Correlation Heatmap (Selected Features to keep it readable)
    print("  Generating Correlation Heatmap...")
    plt.figure(figsize=(12, 10))
    # Select a subset of features for a cleaner heatmap
    subset = ['aqi', 'pm25', 'pm10', 'o3', 'no2', 'so2', 'co', 'temperature', 
              'humidity', 'pressure', 'wind_speed', 'wind_u', 'wind_v', 
              'precipitation', 'solar_radiation', 'clouds', 'is_weekend', 'city_encoded']
    
    corr = df[subset].corr()
    sns.heatmap(corr, annot=False, cmap='RdBu_r', center=0)
    plt.title("Feature Correlation Heatmap (Key Variables)")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "correlation_heatmap.png"))
    plt.close()

    # 2. Distribution of AQI
    print("  Generating AQI Distribution Plot...")
    plt.figure(figsize=(10, 6))
    sns.histplot(df['aqi'], kde=True, color='teal')
    plt.title("Distribution of Scaled AQI (Training Set)")
    plt.xlabel("Scaled AQI")
    plt.savefig(os.path.join(OUTPUT_DIR, "aqi_distribution.png"))
    plt.close()

    # 3. AQI vs Pollutants Scatter (Sampled)
    print("  Generating Scatter Plots (AQI vs PM2.5/PM10)...")
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    sample_df = df.sample(min(10000, len(df)))
    
    sns.scatterplot(data=sample_df, x='pm25', y='aqi', alpha=0.3, ax=axes[0], color='crimson')
    axes[0].set_title("AQI vs PM2.5 (Scaled)")
    
    sns.scatterplot(data=sample_df, x='pm10', y='aqi', alpha=0.3, ax=axes[1], color='orange')
    axes[1].set_title("AQI vs PM10 (Scaled)")
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "aqi_pollutant_scatter.png"))
    plt.close()

    # 4. Temporal Patterns: Hour Sin/Cos visualization
    print("  Generating Temporal Feature Visualization...")
    plt.figure(figsize=(8, 8))
    plt.scatter(df['hour_sin'].iloc[:24*7], df['hour_cos'].iloc[:24*7], c=range(24*7), cmap='twilight')
    plt.colorbar(label='Hour of Week')
    plt.title("Cyclical Hour Representation (sin vs cos)")
    plt.xlabel("Hour Sin")
    plt.ylabel("Hour Cos")
    plt.savefig(os.path.join(OUTPUT_DIR, "temporal_cyclical.png"))
    plt.close()

    print(f"\n  All visualizations saved to '{OUTPUT_DIR}/'")

if __name__ == "__main__":
    run_visualizations()
