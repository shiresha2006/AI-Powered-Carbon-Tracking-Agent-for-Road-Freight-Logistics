# src/model_trainer.py
# ============================================================
# Model Training Pipeline — 3 Models
# 1. XGBoost Emission Estimator (Regression)
# 2. Isolation Forest Anomaly Detector
# 3. Emission Confidence Scorer
# ============================================================

import matplotlib
matplotlib.use("Agg")  # Fix Windows Tkinter crash

import os
import sys
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import shap


from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error,
    r2_score, precision_score, recall_score, f1_score
)
from sklearn.ensemble import IsolationForest
from xgboost import XGBRegressor, XGBClassifier

from tqdm import tqdm

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "clean_shipments.csv")
MODEL_DIR = os.path.join(BASE_DIR, "models")
PLOT_DIR  = os.path.join(BASE_DIR, "data", "plots")

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(PLOT_DIR,  exist_ok=True)


# ─────────────────────────────────────────────
# FEATURE COLUMNS
# ─────────────────────────────────────────────
CATEGORICAL_COLS = [
    "origin", "destination", "vehicle_type",
    "fuel_type", "road_type", "carrier_name",
    "goods_category"
]

FEATURE_COLS = [
    # Numerical
    "distance_km",
    "load_weight_tonnes",
    "load_utilization_pct",
    "vehicle_age_years",
    "capacity_tonnes",
    "num_stops",
    "return_empty",
    "month",
    "quarter",
    "lane_tier",

    # Categorical (label encoded)
    "origin",
    "destination",
    "vehicle_type",
    "fuel_type",
    "road_type",
    "carrier_name",
    "goods_category",

    # CO2-relative features (for anomaly detection)
    "co2_vs_lane_avg",
    "co2_zscore_in_lane",
    "co2_per_km_norm",
]

TARGET_COL = "co2_kg"
ANOMALY_COL = "is_anomaly"
LABEL_COL = "emission_label"


# ─────────────────────────────────────────────
# STEP 1 — LOAD DATA
# ─────────────────────────────────────────────
def load_data() -> pd.DataFrame:
    print("\n📂 Loading dataset...")
    df = pd.read_csv(DATA_PATH)
    print(f"   Shape          : {df.shape}")
    print(f"   Missing cells  : {df.isnull().sum().sum():,}")
    print(f"   Anomalies      : {df['is_anomaly'].sum():,}")
    print(f"   CO₂ range      : {df['co2_kg'].min():.1f} → {df['co2_kg'].max():.1f} kg")
    return df


# ─────────────────────────────────────────────
# STEP 2 — PREPROCESSING
# ─────────────────────────────────────────────
def preprocess(df: pd.DataFrame) -> tuple:
    print("\n🔧 Preprocessing...")
    df = df.copy()

    # ── Impute missing numerics with median ──
    num_cols = [
        "distance_km", "load_weight_tonnes", "load_utilization_pct",
        "vehicle_age_years", "num_stops", "return_empty"
    ]
    for col in num_cols:
        median_val    = df[col].median()
        missing_count = df[col].isnull().sum()
        df[col]       = df[col].fillna(median_val)
        if missing_count > 0:
            print(f"   Imputed {missing_count:,} missing values in '{col}' "
                  f"with median={median_val:.2f}")

    # ── Impute missing categoricals with mode ──
    for col in ["goods_category"]:
        mode_val      = df[col].mode()[0]
        missing_count = df[col].isnull().sum()
        df[col]       = df[col].fillna(mode_val)
        if missing_count > 0:
            print(f"   Imputed {missing_count:,} missing values in '{col}' "
                  f"with mode='{mode_val}'")

    # ── Label encode categoricals ──
    encoders = {}
    for col in CATEGORICAL_COLS:
        le      = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
        encoders[col] = le

    # ── CO2-relative features for better anomaly detection ──
    lane_avg_co2 = df.groupby(
        ["origin", "destination"])["co2_kg"].transform("mean")
    lane_std_co2 = df.groupby(
        ["origin", "destination"])["co2_kg"].transform("std").fillna(1)
    vtype_avg_co2_per_km = df.groupby(
        "vehicle_type")["co2_per_km"].transform("mean") + 0.001

    df["co2_vs_lane_avg"]    = df["co2_kg"] / (lane_avg_co2 + 1)
    df["co2_zscore_in_lane"] = (df["co2_kg"] - lane_avg_co2) / (lane_std_co2 + 1)
    df["co2_per_km_norm"]    = df["co2_per_km"] / vtype_avg_co2_per_km

    # ── Build feature matrix ──
    X         = df[FEATURE_COLS].copy()
    y_reg     = df[TARGET_COL]
    y_anomaly = df[ANOMALY_COL]

    print(f"   Feature matrix : {X.shape}")
    print(f"   Target (co2)   : mean={y_reg.mean():.1f} kg, "
          f"std={y_reg.std():.1f}")

    return X, y_reg, y_anomaly, encoders, df


# ─────────────────────────────────────────────
# STEP 3 — MODEL 1: XGBOOST EMISSION ESTIMATOR
# ─────────────────────────────────────────────
def train_emission_model(X, y_reg, y_anomaly):
    print("\n" + "=" * 55)
    print("  🤖 MODEL 1 — XGBoost Emission Estimator")
    print("=" * 55)

    # Train only on clean (non-anomaly) shipments
    clean_mask = y_anomaly == 0
    X_clean    = X[clean_mask]
    y_clean    = y_reg[clean_mask]
    print(f"   Training on {len(X_clean):,} clean records (anomalies excluded)")

    X_train, X_test, y_train, y_test = train_test_split(
        X_clean, y_clean, test_size=0.2, random_state=42
    )
    print(f"   Train size : {len(X_train):,}")
    print(f"   Test size  : {len(X_test):,}")

    model = XGBRegressor(
        n_estimators          = 800,
        learning_rate         = 0.03,
        max_depth             = 8,
        min_child_weight      = 2,
        subsample             = 0.85,
        colsample_bytree      = 0.85,
        reg_alpha             = 0.05,
        reg_lambda            = 1.2,
        gamma                 = 0.1,
        random_state          = 42,
        n_jobs                = -1,
        early_stopping_rounds = 40,
        eval_metric           = "rmse",
        verbosity             = 0,
    )

    print("\n   Training...")
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False
    )

    # Evaluate
    y_pred = model.predict(X_test)
    mae    = mean_absolute_error(y_test, y_pred)
    rmse   = np.sqrt(mean_squared_error(y_test, y_pred))
    r2     = r2_score(y_test, y_pred)
    mape   = np.mean(np.abs((y_test - y_pred) / (y_test + 1e-9))) * 100

    print(f"\n   📊 Evaluation Results:")
    print(f"   MAE   : {mae:.2f} kg CO₂")
    print(f"   RMSE  : {rmse:.2f} kg CO₂")
    print(f"   R²    : {r2:.4f}")
    print(f"   MAPE  : {mape:.2f}%")

    # Save model
    model_path = os.path.join(MODEL_DIR, "emission_model.pkl")
    joblib.dump(model, model_path)
    print(f"\n   ✅ Saved → {model_path}")

    # ── SHAP Explainability ──
    print("\n   🔍 Generating SHAP explanations...")
    explainer   = shap.TreeExplainer(model)
    shap_sample = X_test.sample(500, random_state=42)
    shap_values = explainer.shap_values(shap_sample)

    plt.figure(figsize=(10, 7))
    shap.summary_plot(
        shap_values, shap_sample,
        feature_names=FEATURE_COLS,
        show=False, plot_size=(10, 7)
    )
    plt.title("SHAP Feature Importance — Emission Model", fontsize=13)
    plt.tight_layout()
    shap_path = os.path.join(PLOT_DIR, "shap_summary.png")
    plt.savefig(shap_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"   ✅ SHAP plot saved → {shap_path}")

    # ── Feature Importance Plot ──
    feat_imp = pd.Series(
        model.feature_importances_, index=FEATURE_COLS
    ).sort_values(ascending=True).tail(12)

    plt.figure(figsize=(9, 6))
    feat_imp.plot(kind="barh", color="#0d6e6e")
    plt.title("Top 12 Feature Importances — Emission Model", fontsize=13)
    plt.xlabel("Importance Score")
    plt.tight_layout()
    fi_path = os.path.join(PLOT_DIR, "feature_importance.png")
    plt.savefig(fi_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"   ✅ Feature importance plot → {fi_path}")

    # ── Actual vs Predicted Plot ──
    sample_idx = np.random.choice(len(y_test), 1000, replace=False)
    y_test_arr = np.array(y_test)
    plt.figure(figsize=(8, 6))
    plt.scatter(
        y_test_arr[sample_idx],
        y_pred[sample_idx],
        alpha=0.4, color="#0d6e6e", s=15
    )
    max_val = max(y_test_arr.max(), y_pred.max())
    plt.plot([0, max_val], [0, max_val], "r--",
             linewidth=1.5, label="Perfect fit")
    plt.xlabel("Actual CO₂ (kg)")
    plt.ylabel("Predicted CO₂ (kg)")
    plt.title(f"Actual vs Predicted CO₂  |  R²={r2:.4f}", fontsize=13)
    plt.legend()
    plt.tight_layout()
    avp_path = os.path.join(PLOT_DIR, "actual_vs_predicted.png")
    plt.savefig(avp_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"   ✅ Actual vs Predicted plot → {avp_path}")

    return model, {"MAE": mae, "RMSE": rmse, "R2": r2, "MAPE": mape}


# ─────────────────────────────────────────────
# STEP 4 — MODEL 2: ISOLATION FOREST ANOMALY DETECTOR
# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
# STEP 4 — MODEL 2: ANOMALY DETECTOR (Supervised XGBoost)
# We have labels → use supervised learning, not unsupervised
# ─────────────────────────────────────────────
def train_anomaly_model(X, y_anomaly):
    print("\n" + "=" * 55)
    print("  🚨 MODEL 2 — Anomaly Detector (Supervised XGBoost)")
    print("=" * 55)

    # ── Handle class imbalance (95% normal, 5% anomaly) ──
    # scale_pos_weight = normal_count / anomaly_count
    normal_count  = (y_anomaly == 0).sum()
    anomaly_count = (y_anomaly == 1).sum()
    scale_weight  = normal_count / anomaly_count

    print(f"   Normal shipments  : {normal_count:,}")
    print(f"   Anomaly shipments : {anomaly_count:,}")
    print(f"   Class weight      : {scale_weight:.1f}x")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_anomaly, test_size=0.2,
        random_state=42, stratify=y_anomaly   # keep class balance in split
    )
    print(f"   Train size        : {len(X_train):,}")
    print(f"   Test size         : {len(X_test):,}")

    model = XGBClassifier(
        n_estimators       = 300,
        learning_rate      = 0.05,
        max_depth          = 6,
        min_child_weight   = 3,
        subsample          = 0.85,
        colsample_bytree   = 0.85,
        scale_pos_weight   = scale_weight,   # handles imbalance
        eval_metric        = "logloss",
        early_stopping_rounds = 30,
        random_state       = 42,
        n_jobs             = -1,
        verbosity          = 0,
    )

    print("\n   Training...")
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False
    )

    # Predict
    y_pred      = model.predict(X_test)
    y_pred_prob = model.predict_proba(X_test)[:, 1]

    prec = precision_score(y_test, y_pred, zero_division=0)
    rec  = recall_score(y_test, y_pred, zero_division=0)
    f1   = f1_score(y_test, y_pred, zero_division=0)

    from sklearn.metrics import roc_auc_score, confusion_matrix
    auc = roc_auc_score(y_test, y_pred_prob)
    cm  = confusion_matrix(y_test, y_pred)

    print(f"\n   📊 Evaluation Results:")
    print(f"   Precision  : {prec:.4f}")
    print(f"   Recall     : {rec:.4f}")
    print(f"   F1 Score   : {f1:.4f}")
    print(f"   ROC-AUC    : {auc:.4f}")
    print(f"\n   Confusion Matrix:")
    print(f"   TN={cm[0,0]:,}  FP={cm[0,1]:,}")
    print(f"   FN={cm[1,0]:,}  TP={cm[1,1]:,}")

    # ── Anomaly Probability Distribution Plot ──
    plt.figure(figsize=(9, 5))
    plt.hist(y_pred_prob[y_test == 0], bins=60, alpha=0.7,
             color="#0d6e6e", label="Normal shipments")
    plt.hist(y_pred_prob[y_test == 1], bins=60, alpha=0.7,
             color="#e74c3c", label="Anomalous shipments")
    plt.axvline(x=0.5, color="black", linestyle="--",
                linewidth=1.5, label="Decision threshold (0.5)")
    plt.xlabel("Anomaly Probability Score")
    plt.ylabel("Count")
    plt.title(f"Anomaly Detector — Probability Distribution  |  AUC={auc:.4f}",
              fontsize=13)
    plt.legend()
    plt.tight_layout()
    anom_path = os.path.join(PLOT_DIR, "anomaly_score_distribution.png")
    plt.savefig(anom_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"   ✅ Anomaly distribution plot → {anom_path}")

    # ── Confusion Matrix Heatmap ──
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt=",", cmap="Greens",
                xticklabels=["Normal", "Anomaly"],
                yticklabels=["Normal", "Anomaly"])
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.title("Anomaly Detector — Confusion Matrix", fontsize=13)
    plt.tight_layout()
    cm_path = os.path.join(PLOT_DIR, "anomaly_confusion_matrix.png")
    plt.savefig(cm_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"   ✅ Confusion matrix plot → {cm_path}")

    # Save
    model_path = os.path.join(MODEL_DIR, "anomaly_model.pkl")
    joblib.dump(model, model_path)
    print(f"   ✅ Saved → {model_path}")

    return model, {"Precision": prec, "Recall": rec, "F1": f1, "ROC_AUC": auc}

# ─────────────────────────────────────────────
# STEP 5 — MODEL 3: CONFIDENCE SCORER
# ─────────────────────────────────────────────
def train_confidence_model(df_processed: pd.DataFrame):
    print("\n" + "=" * 55)
    print("  📊 MODEL 3 — Emission Confidence Scorer")
    print("=" * 55)

    # Reload original data to detect missing fields
    df_orig = pd.read_csv(DATA_PATH)

    field_weights = {
        "distance_km":          25,
        "load_weight_tonnes":   20,
        "vehicle_type":         15,
        "vehicle_age_years":    10,
        "road_type":            10,
        "fuel_type":             8,
        "return_empty":          7,
        "goods_category":        3,
        "num_stops":             2,
    }

    # Build confidence score per record
    confidence_scores = []
    for _, row in tqdm(df_orig.iterrows(),
                       total=len(df_orig),
                       desc="   Scoring confidence",
                       unit="rec"):
        score = sum(
            weight for field, weight in field_weights.items()
            if pd.notna(row.get(field))
        )
        confidence_scores.append(score)

    df_orig["confidence_score"] = confidence_scores

    # Features = missingness indicators
    X_conf = pd.DataFrame({
        f"has_{field}": df_orig[field].notna().astype(int)
        for field in field_weights.keys()
    })
    y_conf = df_orig["confidence_score"]

    X_train, X_test, y_train, y_test = train_test_split(
        X_conf, y_conf, test_size=0.2, random_state=42
    )

    model = XGBRegressor(
        n_estimators  = 100,
        max_depth     = 4,
        learning_rate = 0.1,
        random_state  = 42,
        verbosity     = 0,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mae    = mean_absolute_error(y_test, y_pred)
    r2     = r2_score(y_test, y_pred)

    print(f"\n   📊 Evaluation Results:")
    print(f"   MAE : {mae:.2f} confidence points")
    print(f"   R²  : {r2:.4f}")

    # ── Confidence Distribution Plot ──
    plt.figure(figsize=(9, 5))
    plt.hist(confidence_scores, bins=30, color="#0d6e6e",
             edgecolor="white", alpha=0.85)
    plt.axvline(x=np.mean(confidence_scores), color="red",
                linestyle="--",
                label=f"Mean = {np.mean(confidence_scores):.1f}")
    plt.xlabel("Confidence Score (0–100)")
    plt.ylabel("Number of Shipments")
    plt.title("Emission Estimate Confidence Score Distribution", fontsize=13)
    plt.legend()
    plt.tight_layout()
    conf_path = os.path.join(PLOT_DIR, "confidence_distribution.png")
    plt.savefig(conf_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"   ✅ Confidence distribution plot → {conf_path}")

    # Save
    model_path = os.path.join(MODEL_DIR, "confidence_scorer.pkl")
    joblib.dump({"model": model, "field_weights": field_weights}, model_path)
    print(f"   ✅ Saved → {model_path}")

    return model, {"MAE": mae, "R2": r2}


# ─────────────────────────────────────────────
# STEP 6 — SAVE ENCODERS
# ─────────────────────────────────────────────
def save_encoders(encoders: dict):
    enc_path = os.path.join(MODEL_DIR, "encoders.pkl")
    joblib.dump(encoders, enc_path)
    print(f"\n   ✅ Encoders saved → {enc_path}")


# ─────────────────────────────────────────────
# STEP 7 — FINAL SUMMARY
# ─────────────────────────────────────────────
def print_final_summary(metrics: dict):
    print("\n" + "=" * 55)
    print("  🎯 TRAINING COMPLETE — FINAL SUMMARY")
    print("=" * 55)

    print(f"\n  Model 1 — Emission Estimator (XGBoost)")
    for k, v in metrics["emission"].items():
        print(f"    {k:<8}: {v:.4f}")

    print(f"\n  Model 2 — Anomaly Detector (Isolation Forest)")
    for k, v in metrics["anomaly"].items():
        print(f"    {k:<12}: {v:.4f}")

    print(f"\n  Model 3 — Confidence Scorer (XGBoost)")
    for k, v in metrics["confidence"].items():
        print(f"    {k:<8}: {v:.4f}")

    print(f"\n  📁 Saved Models:")
    for f in os.listdir(MODEL_DIR):
        fpath = os.path.join(MODEL_DIR, f)
        size  = os.path.getsize(fpath) / 1024
        print(f"    {f:<35} {size:.1f} KB")

    print(f"\n  📊 Saved Plots:")
    for f in os.listdir(PLOT_DIR):
        print(f"    {f}")

    print(f"\n{'='*55}")
    print("  ✅ Ready for Dashboard + Agent Layer!")
    print(f"{'='*55}\n")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    # Load
    df = load_data()

    # Preprocess
    X, y_reg, y_anomaly, encoders, df_processed = preprocess(df)

    # Train all 3 models
    emission_model,   emission_metrics   = train_emission_model(X, y_reg, y_anomaly)
    anomaly_model,    anomaly_metrics    = train_anomaly_model(X, y_anomaly)
    confidence_model, confidence_metrics = train_confidence_model(df_processed)

    # Save encoders
    save_encoders(encoders)

    # Final summary
    print_final_summary({
        "emission":   emission_metrics,
        "anomaly":    anomaly_metrics,
        "confidence": confidence_metrics,
    })