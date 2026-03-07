# src/data_cleaner.py
# ============================================================
# Fills missing values in raw_shipments.csv intelligently
# Strategy: Smart imputation (not just median/mode)
# Output: data/clean_shipments.csv
# ============================================================

import os
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from tqdm import tqdm

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_PATH  = os.path.join(BASE_DIR, "data", "raw_shipments.csv")
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "clean_shipments.csv")


# ─────────────────────────────────────────────
# LOAD
# ─────────────────────────────────────────────
def load_data() -> pd.DataFrame:
    print("\n📂 Loading raw dataset...")
    df = pd.read_csv(INPUT_PATH)
    print(f"   Shape         : {df.shape}")
    print(f"   Missing cells : {df.isnull().sum().sum():,}")
    print("\n   Missing values per column:")
    missing = df.isnull().sum()
    missing = missing[missing > 0]
    for col, count in missing.items():
        pct = count / len(df) * 100
        print(f"   {col:<30} {count:>6,}  ({pct:.1f}%)")
    return df


# ─────────────────────────────────────────────
# STRATEGY 1 — Domain-Logic Imputation
# Use known relationships in logistics data
# ─────────────────────────────────────────────
def domain_logic_impute(df: pd.DataFrame) -> pd.DataFrame:
    print("\n🔧 Step 1 — Domain Logic Imputation...")
    df = df.copy()

    # ── return_empty: if load_utilization > 85%, less likely to return empty ──
    mask = df["return_empty"].isnull()
    df.loc[mask & (df["load_utilization_pct"] > 85), "return_empty"] = 0
    df.loc[mask & (df["load_utilization_pct"] <= 85), "return_empty"] = 1
    # remaining nulls (where load_util is also null)
    still_null = df["return_empty"].isnull().sum()
    if still_null > 0:
        df["return_empty"] = df["return_empty"].fillna(1)  # default: return empty
    print(f"   ✅ return_empty    → filled using load utilization logic")

    # ── num_stops: fill based on lane_tier ──
    # Tier 1 = 1 stop, Tier 2 = 1-2 stops, Tier 3 = 2-3 stops
    tier_stop_map = {1: 1, 2: 1, 3: 2}
    mask = df["num_stops"].isnull()
    df.loc[mask, "num_stops"] = df.loc[mask, "lane_tier"].map(tier_stop_map)
    df["num_stops"] = df["num_stops"].fillna(1)
    print(f"   ✅ num_stops       → filled using lane tier logic")

    # ── load_weight_tonnes: fill using capacity × median utilization per vehicle ──
    mask = df["load_weight_tonnes"].isnull()
    median_util_by_vehicle = df.groupby("vehicle_type")["load_utilization_pct"].median() / 100
    capacity_by_vehicle    = df.groupby("vehicle_type")["capacity_tonnes"].first()
    for vtype in df.loc[mask, "vehicle_type"].unique():
        util     = median_util_by_vehicle.get(vtype, 0.70)
        capacity = capacity_by_vehicle.get(vtype, 10)
        fill_val = round(capacity * util, 2)
        df.loc[mask & (df["vehicle_type"] == vtype), "load_weight_tonnes"] = fill_val
    print(f"   ✅ load_weight     → filled using vehicle capacity × median utilization")

    # ── load_utilization_pct: recalculate from load_weight / capacity ──
    mask = df["load_utilization_pct"].isnull()
    df.loc[mask, "load_utilization_pct"] = (
        df.loc[mask, "load_weight_tonnes"] /
        df.loc[mask, "capacity_tonnes"] * 100
    ).round(1)
    df["load_utilization_pct"] = df["load_utilization_pct"].clip(0, 100)
    print(f"   ✅ load_util_pct   → recalculated from load_weight / capacity")

    # ── goods_category: fill using most common category per lane ──
    mask = df["goods_category"].isnull()
    lane_mode = df.groupby(["origin", "destination"])["goods_category"].agg(
        lambda x: x.mode()[0] if len(x.dropna()) > 0 else "FMCG"
    )
    df.loc[mask, "goods_category"] = df.loc[mask].apply(
        lambda row: lane_mode.get((row["origin"], row["destination"]), "FMCG"),
        axis=1
    )
    df["goods_category"] = df["goods_category"].fillna("FMCG")
    print(f"   ✅ goods_category  → filled using most common category per lane")

    return df


# ─────────────────────────────────────────────
# STRATEGY 2 — Statistical Imputation
# Use lane/vehicle group statistics
# ─────────────────────────────────────────────
def statistical_impute(df: pd.DataFrame) -> pd.DataFrame:
    print("\n🔧 Step 2 — Statistical Group Imputation...")
    df = df.copy()

    # ── vehicle_age_years: fill using median age per carrier ──
    # Carriers tend to have similar fleet ages
    mask = df["vehicle_age_years"].isnull()
    carrier_median_age = df.groupby("carrier_name")["vehicle_age_years"].median()
    df.loc[mask, "vehicle_age_years"] = df.loc[mask, "carrier_name"].map(carrier_median_age)

    # Fallback: global median for any remaining nulls
    global_median_age = df["vehicle_age_years"].median()
    df["vehicle_age_years"] = df["vehicle_age_years"].fillna(global_median_age)
    print(f"   ✅ vehicle_age     → filled using carrier fleet median age")

    return df


# ─────────────────────────────────────────────
# STRATEGY 3 — ML-Based Imputation
# Train a small model to predict missing values
# ─────────────────────────────────────────────
def ml_impute(df: pd.DataFrame) -> pd.DataFrame:
    print("\n🔧 Step 3 — ML-Based Imputation (if any remaining)...")
    df = df.copy()

    # Check what's still missing
    still_missing = df.isnull().sum()
    still_missing = still_missing[still_missing > 0]

    if len(still_missing) == 0:
        print("   ✅ No remaining missing values — skipping ML imputation")
        return df

    print(f"   Found {len(still_missing)} columns still with missing values:")
    for col, count in still_missing.items():
        print(f"   → {col}: {count:,} missing")

    # Use these as predictor features (always available)
    base_features = [
        "distance_km", "capacity_tonnes", "month",
        "quarter", "lane_tier", "year"
    ]

    for col in still_missing.index:
        print(f"\n   Training imputer for '{col}'...")

        # Rows where col is present (training data)
        train_mask = df[col].notna()
        pred_mask  = df[col].isnull()

        if train_mask.sum() < 100:
            # Not enough data — use global median/mode
            if df[col].dtype in ["float64", "int64"]:
                df[col] = df[col].fillna(df[col].median())
            else:
                df[col] = df[col].fillna(df[col].mode()[0])
            continue

        # Encode categoricals for features
        X_base = pd.get_dummies(
            df[base_features], drop_first=True
        ).fillna(0)

        X_train = X_base[train_mask]
        y_train = df.loc[train_mask, col]
        X_pred  = X_base[pred_mask]

        # Choose model based on column type
        if df[col].dtype in ["float64", "int64"]:
            imputer = RandomForestRegressor(
                n_estimators=50, random_state=42, n_jobs=-1
            )
        else:
            imputer = RandomForestClassifier(
                n_estimators=50, random_state=42, n_jobs=-1
            )

        imputer.fit(X_train, y_train)
        df.loc[pred_mask, col] = imputer.predict(X_pred)
        print(f"   ✅ '{col}' imputed using RandomForest")

    return df


# ─────────────────────────────────────────────
# VERIFY & SAVE
# ─────────────────────────────────────────────
def verify_and_save(df: pd.DataFrame):
    remaining = df.isnull().sum().sum()

    print("\n" + "=" * 55)
    print("  ✅ CLEANING COMPLETE")
    print("=" * 55)
    print(f"   Remaining missing values : {remaining}")

    if remaining > 0:
        print("   ⚠️  Still missing (filling with fallback):")
        for col in df.columns[df.isnull().any()]:
            count = df[col].isnull().sum()
            print(f"   → {col}: {count:,}")
            if df[col].dtype in ["float64", "int64"]:
                df[col] = df[col].fillna(df[col].median())
            else:
                df[col] = df[col].fillna(df[col].mode()[0])

    # Final verification
    assert df.isnull().sum().sum() == 0, "Still have missing values!"

    # Save
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"\n   💾 Clean dataset saved → {OUTPUT_PATH}")
    print(f"   Shape                  : {df.shape}")

    # Summary stats
    print(f"\n   📊 CO₂ Statistics (clean data):")
    print(f"   Min    : {df['co2_kg'].min():,.2f} kg")
    print(f"   Max    : {df['co2_kg'].max():,.2f} kg")
    print(f"   Mean   : {df['co2_kg'].mean():,.2f} kg")
    print(f"   Median : {df['co2_kg'].median():,.2f} kg")

    print(f"\n   📋 Sample of clean data (5 rows):")
    print(df[[
        "shipment_id", "origin", "destination",
        "vehicle_type", "load_weight_tonnes",
        "vehicle_age_years", "co2_kg"
    ]].head().to_string(index=False))

    print(f"\n{'='*55}")
    print(f"  🚀 Ready to retrain models on clean data!")
    print(f"{'='*55}\n")

    return df


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    df = load_data()
    df = domain_logic_impute(df)
    df = statistical_impute(df)
    df = ml_impute(df)
    df = verify_and_save(df)