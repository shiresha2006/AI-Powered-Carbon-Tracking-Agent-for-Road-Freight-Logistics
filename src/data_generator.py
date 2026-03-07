# src/data_generator.py
# ============================================================
# Synthetic Shipment Dataset Generator
# Strategy: Formula-based CO2 calculation + Statistical Noise
# Output: data/raw_shipments.csv (50,000 records)
# ============================================================

import os
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from tqdm import tqdm

# Import our formula engine
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from emission_factors import (
    VEHICLE_TYPES,
    ROAD_TYPE_FACTORS,
    INDIAN_LANES,
    SEASONAL_MULTIPLIERS,
    CARRIER_PROFILES,
    calculate_co2
)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
TOTAL_RECORDS     = 50000
RANDOM_SEED       = 42
MISSING_RATE      = 0.12   # 12% fields randomly missing (real-world messiness)
ANOMALY_RATE      = 0.05   # 5% shipments are anomalies (very high emissions)
START_DATE        = datetime(2022, 1, 1)
END_DATE          = datetime(2024, 12, 31)
OUTPUT_PATH       = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "..", "data", "raw_shipments.csv")

random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)


# ─────────────────────────────────────────────
# HELPER — Random Date weighted by seasonality
# ─────────────────────────────────────────────
def random_date_weighted() -> datetime:
    """Pick a random date, weighted by monthly seasonal demand."""
    total_days = (END_DATE - START_DATE).days
    date = START_DATE + timedelta(days=random.randint(0, total_days))
    month_weight = SEASONAL_MULTIPLIERS[date.month]
    # Accept/reject sampling based on seasonal weight
    if random.random() < month_weight:
        return date
    else:
        # Retry once — keeps distribution realistic without infinite loops
        date = START_DATE + timedelta(days=random.randint(0, total_days))
        return date


# ─────────────────────────────────────────────
# HELPER — Generate one shipment record
# ─────────────────────────────────────────────
def generate_shipment(shipment_id: int, is_anomaly: bool = False) -> dict:
    """
    Generate a single synthetic shipment with:
    - Formula-based CO2 ground truth
    - Realistic statistical noise
    - Optional anomaly injection
    """

    # ── Pick a random lane ──
    lane = random.choice(INDIAN_LANES)
    origin           = lane["origin"]
    destination      = lane["destination"]
    base_distance    = lane["distance_km"]
    road_type        = lane["road_type"]
    tier             = lane["tier"]

    # ── Add route distance noise ±8% (traffic detours, route variation) ──
    distance_km = base_distance * np.random.uniform(0.92, 1.08)
    distance_km = round(distance_km, 1)

    # ── Pick vehicle type (weighted — heavy trucks dominate Indian freight) ──
    vehicle_weights = {
        "LCV_DIESEL":           0.08,
        "MEDIUM_TRUCK_DIESEL":  0.15,
        "HEAVY_TRUCK_DIESEL":   0.28,
        "MAV_DIESEL":           0.25,
        "TRAILER_40T_DIESEL":   0.12,
        "MEDIUM_TRUCK_CNG":     0.05,
        "HEAVY_TRUCK_CNG":      0.04,
        "ELECTRIC_TRUCK":       0.01,   # rare in India currently
        "REEFER_DIESEL":        0.02,
    }
    vehicle_type = random.choices(
        list(vehicle_weights.keys()),
        weights=list(vehicle_weights.values())
    )[0]

    capacity_tonnes = VEHICLE_TYPES[vehicle_type]["capacity_tonnes"]

    # ── Load weight — realistic utilization 40%–95% ──
    load_utilization = np.random.beta(a=5, b=2)        # skewed toward higher utilization
    load_utilization = np.clip(load_utilization, 0.40, 0.95)
    load_weight_tonnes = round(capacity_tonnes * load_utilization, 2)

    # ── Vehicle age — Indian fleet skews older (3–12 years) ──
    vehicle_age_years = round(np.random.gamma(shape=3.0, scale=2.5), 1)
    vehicle_age_years = float(np.clip(vehicle_age_years, 0.5, 20.0))

    # ── Carrier ──
    carrier_name = random.choice(list(CARRIER_PROFILES.keys()))

    # ── Return trip empty? (60% of trucks return empty in India) ──
    return_empty = random.random() < 0.60

    # ── Shipment date ──
    shipment_date = random_date_weighted()

    # ── Goods category ──
    goods_categories = [
        "FMCG", "Automotive Parts", "Pharmaceuticals",
        "Electronics", "Textiles", "Agriculture",
        "Construction Material", "Industrial Machinery",
        "Cold Chain / Food", "E-commerce"
    ]
    goods_category = random.choice(goods_categories)

    # ── Number of stops (multi-drop adds emission overhead) ──
    if tier == 3:
        num_stops = random.randint(1, 4)
    elif tier == 2:
        num_stops = random.randint(1, 2)
    else:
        num_stops = 1
    multi_stop_factor = 1 + (num_stops - 1) * 0.04   # 4% overhead per extra stop

    # ─────────────────────────────────────────
    # CORE CO2 CALCULATION (formula engine)
    # ─────────────────────────────────────────
    co2_result = calculate_co2(
        distance_km        = distance_km,
        load_weight_tonnes = load_weight_tonnes,
        vehicle_type       = vehicle_type,
        vehicle_age_years  = vehicle_age_years,
        road_type          = road_type,
        return_empty       = return_empty,
        carrier_name       = carrier_name
    )

    co2_kg = co2_result["co2_kg"] * multi_stop_factor

    # ─────────────────────────────────────────
    # ADD STATISTICAL NOISE (±6% real-world variance)
    # Simulates: driver behavior, traffic, weather, load shifts
    # ─────────────────────────────────────────
    noise_factor = np.random.normal(loc=1.0, scale=0.06)
    noise_factor = np.clip(noise_factor, 0.85, 1.20)
    co2_kg = co2_kg * noise_factor

    # ─────────────────────────────────────────
    # ANOMALY INJECTION
    # Simulate extreme emission events:
    # - breakdown causing idle fuel burn
    # - overloading beyond legal limits
    # - severe route deviation
    # - engine malfunction
    # ─────────────────────────────────────────
    is_anomaly_flag = 0
    anomaly_reason  = None

    if is_anomaly:
        anomaly_type = random.choice([
            "engine_malfunction",
            "route_deviation",
            "overloading",
            "idle_breakdown",
        ])
        anomaly_multipliers = {
            "engine_malfunction": np.random.uniform(1.8, 2.5),
            "route_deviation":    np.random.uniform(1.4, 1.9),
            "overloading":        np.random.uniform(1.3, 1.6),
            "idle_breakdown":     np.random.uniform(1.5, 2.2),
        }
        co2_kg = co2_kg * anomaly_multipliers[anomaly_type]
        is_anomaly_flag = 1
        anomaly_reason  = anomaly_type

    co2_kg = round(co2_kg, 2)

    # ─────────────────────────────────────────
    # DERIVED FIELDS
    # ─────────────────────────────────────────
    fuel_type           = VEHICLE_TYPES[vehicle_type]["fuel_type"]
    co2_per_km          = round(co2_kg / distance_km, 4)
    co2_per_tonne_km    = round(co2_kg / (load_weight_tonnes * distance_km), 6)
    load_util_pct       = round(load_utilization * 100, 1)

    # Emission intensity label (for classification tasks)
    if co2_per_tonne_km < 0.08:
        emission_label = "LOW"
    elif co2_per_tonne_km < 0.14:
        emission_label = "MEDIUM"
    elif co2_per_tonne_km < 0.20:
        emission_label = "HIGH"
    else:
        emission_label = "VERY_HIGH"

    # ─────────────────────────────────────────
    # BUILD RECORD
    # ─────────────────────────────────────────
    record = {
        # Identifiers
        "shipment_id":          f"SHP{shipment_id:06d}",
        "shipment_date":        shipment_date.strftime("%Y-%m-%d"),
        "month":                shipment_date.month,
        "quarter":              (shipment_date.month - 1) // 3 + 1,
        "year":                 shipment_date.year,

        # Route
        "origin":               origin,
        "destination":          destination,
        "distance_km":          distance_km,
        "road_type":            road_type,
        "lane_tier":            tier,
        "num_stops":            num_stops,

        # Vehicle
        "vehicle_type":         vehicle_type,
        "vehicle_age_years":    vehicle_age_years,
        "fuel_type":            fuel_type,
        "capacity_tonnes":      capacity_tonnes,

        # Load
        "load_weight_tonnes":   load_weight_tonnes,
        "load_utilization_pct": load_util_pct,
        "return_empty":         int(return_empty),

        # Carrier & Goods
        "carrier_name":         carrier_name,
        "goods_category":       goods_category,

        # Targets (what the model will learn to predict)
        "co2_kg":               co2_kg,
        "co2_per_km":           co2_per_km,
        "co2_per_tonne_km":     co2_per_tonne_km,
        "emission_label":       emission_label,

        # Anomaly flags (for anomaly detection model)
        "is_anomaly":           is_anomaly_flag,
        "anomaly_reason":       anomaly_reason if anomaly_reason else "none",
    }

    return record


# ─────────────────────────────────────────────
# INJECT MISSING VALUES (simulate real-world data gaps)
# ─────────────────────────────────────────────
NULLABLE_FIELDS = [
    "vehicle_age_years",
    "load_weight_tonnes",
    "load_utilization_pct",
    "num_stops",
    "goods_category",
    "return_empty",
]

def inject_missing(df: pd.DataFrame, missing_rate: float) -> pd.DataFrame:
    """Randomly null out fields to simulate real-world missing data."""
    df = df.copy()
    n_rows = len(df)
    for col in NULLABLE_FIELDS:
        missing_mask = np.random.random(n_rows) < missing_rate
        df.loc[missing_mask, col] = np.nan
    return df


# ─────────────────────────────────────────────
# MAIN GENERATION LOOP
# ─────────────────────────────────────────────
def generate_dataset(n: int = TOTAL_RECORDS) -> pd.DataFrame:
    print(f"\n🚛 Generating {n:,} synthetic shipment records...")
    print(f"   Anomaly rate  : {ANOMALY_RATE*100:.0f}%")
    print(f"   Missing rate  : {MISSING_RATE*100:.0f}%")
    print(f"   Date range    : {START_DATE.date()} → {END_DATE.date()}")
    print(f"   Lanes         : {len(INDIAN_LANES)} Indian O-D pairs\n")

    records    = []
    n_anomaly  = int(n * ANOMALY_RATE)
    anomaly_ids = set(random.sample(range(n), n_anomaly))

    for i in tqdm(range(n), desc="Generating shipments", unit="rec"):
        is_anomaly = i in anomaly_ids
        record = generate_shipment(shipment_id=i + 1, is_anomaly=is_anomaly)
        records.append(record)

    df = pd.DataFrame(records)

    # ── Inject missing values ──
    print("\n🔧 Injecting missing values for realism...")
    df = inject_missing(df, MISSING_RATE)

    return df


# ─────────────────────────────────────────────
# SAVE & SUMMARY
# ─────────────────────────────────────────────
def save_and_summarize(df: pd.DataFrame):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"\n✅ Dataset saved → {OUTPUT_PATH}")
    print(f"\n{'='*55}")
    print(f"  📊 DATASET SUMMARY")
    print(f"{'='*55}")
    print(f"  Total records       : {len(df):,}")
    print(f"  Total columns       : {len(df.columns)}")
    print(f"  Date range          : {df['shipment_date'].min()} → {df['shipment_date'].max()}")
    print(f"  Unique lanes        : {df[['origin','destination']].drop_duplicates().shape[0]}")
    print(f"  Unique carriers     : {df['carrier_name'].nunique()}")
    print(f"  Anomalies injected  : {df['is_anomaly'].sum():,} ({df['is_anomaly'].mean()*100:.1f}%)")
    print(f"  Missing values      : {df.isnull().sum().sum():,} cells")
    print(f"\n  CO₂ Statistics (kg):")
    print(f"  Min     : {df['co2_kg'].min():,.2f}")
    print(f"  Max     : {df['co2_kg'].max():,.2f}")
    print(f"  Mean    : {df['co2_kg'].mean():,.2f}")
    print(f"  Median  : {df['co2_kg'].median():,.2f}")
    print(f"\n  Emission Label Distribution:")
    print(df['emission_label'].value_counts().to_string())
    print(f"\n  Vehicle Type Distribution:")
    print(df['vehicle_type'].value_counts().to_string())
    print(f"\n  Top 5 Lanes by Volume:")
    top_lanes = df.groupby(['origin','destination']).size().sort_values(ascending=False).head(5)
    print(top_lanes.to_string())
    print(f"{'='*55}\n")


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    df = generate_dataset(TOTAL_RECORDS)
    save_and_summarize(df)