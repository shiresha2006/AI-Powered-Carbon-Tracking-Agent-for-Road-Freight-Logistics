# src/predict.py
# ============================================================
# Prediction Engine — Loads all 3 trained models
# Given any shipment → returns:
#   1. CO2 estimate (kg)
#   2. Anomaly flag + probability
#   3. Confidence score
#   4. Emission label + reduction tips
# ============================================================

import os
import sys
import joblib
import numpy as np
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from emission_factors import VEHICLE_TYPES, ROAD_TYPE_FACTORS, CARRIER_PROFILES

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, "models")

# ─────────────────────────────────────────────
# FEATURE COLUMNS (must match model_trainer.py)
# ─────────────────────────────────────────────
FEATURE_COLS = [
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
    "origin",
    "destination",
    "vehicle_type",
    "fuel_type",
    "road_type",
    "carrier_name",
    "goods_category",
    "co2_vs_lane_avg",
    "co2_zscore_in_lane",
    "co2_per_km_norm",
]

CATEGORICAL_COLS = [
    "origin", "destination", "vehicle_type",
    "fuel_type", "road_type", "carrier_name",
    "goods_category"
]

# ─────────────────────────────────────────────
# REFERENCE STAT PATHS
# ─────────────────────────────────────────────
LANE_STATS_PATH  = os.path.join(BASE_DIR, "data", "lane_stats.csv")
VTYPE_STATS_PATH = os.path.join(BASE_DIR, "data", "vtype_stats.csv")

# ─────────────────────────────────────────────
# SMART DEFAULTS
# ─────────────────────────────────────────────
FUEL_MAP = {
    "LCV_DIESEL":           "diesel",
    "MEDIUM_TRUCK_DIESEL":  "diesel",
    "HEAVY_TRUCK_DIESEL":   "diesel",
    "MAV_DIESEL":           "diesel",
    "TRAILER_40T_DIESEL":   "diesel",
    "MEDIUM_TRUCK_CNG":     "cng",
    "HEAVY_TRUCK_CNG":      "cng",
    "ELECTRIC_TRUCK":       "electric",
    "REEFER_DIESEL":        "diesel",
}

TIER_ROAD_MAP = {1: "highway", 2: "mixed", 3: "city"}

SMART_DEFAULTS = {
    "fuel_type":      "diesel",
    "road_type":      "mixed",
    "carrier_name":   "National Roadways Ltd.",
    "goods_category": "FMCG",
    "origin":         "Mumbai",
    "destination":    "Delhi",
    "vehicle_type":   "HEAVY_TRUCK_DIESEL",
}


# ═══════════════════════════════════════════════
# CARBON PREDICTOR CLASS
# ═══════════════════════════════════════════════
class CarbonPredictor:
    """
    One-stop prediction engine for carbon emissions.
    Loads all models once, predicts instantly for any shipment.
    """

    def __init__(self):
        print("🔄 Loading models...")

        self.emission_model   = joblib.load(
            os.path.join(MODEL_DIR, "emission_model.pkl"))
        self.anomaly_model    = joblib.load(
            os.path.join(MODEL_DIR, "anomaly_model.pkl"))
        confidence_bundle     = joblib.load(
            os.path.join(MODEL_DIR, "confidence_scorer.pkl"))
        self.confidence_model = confidence_bundle["model"]
        self.field_weights    = confidence_bundle["field_weights"]
        self.encoders         = joblib.load(
            os.path.join(MODEL_DIR, "encoders.pkl"))

        # Load reference stats
        self.lane_stats  = pd.read_csv(LANE_STATS_PATH)
        self.vtype_stats = pd.read_csv(VTYPE_STATS_PATH)

        print("✅ All models loaded successfully!\n")

    # ─────────────────────────────────────────
    # CONFIDENCE SCORE
    # ─────────────────────────────────────────
    def _compute_confidence(self, raw_input: dict) -> int:
        """Score 0-100 based on how many fields were provided."""
        score = sum(
            weight
            for field, weight in self.field_weights.items()
            if raw_input.get(field) is not None
        )
        return int(score)

    # ─────────────────────────────────────────
    # SAFE LABEL ENCODE
    # Silent fallback with smart defaults
    # ─────────────────────────────────────────
    def _safe_encode(self, col: str, value: str) -> int:
        le = self.encoders[col]
        if value in le.classes_:
            return int(le.transform([value])[0])
        else:
            # Use smart fallback — no warning printed
            fallback = SMART_DEFAULTS.get(col, le.classes_[0])
            if fallback in le.classes_:
                return int(le.transform([fallback])[0])
            return 0

    # ─────────────────────────────────────────
    # LANE REFERENCE STATS
    # ─────────────────────────────────────────
    def _get_lane_stats(self, origin: str, destination: str) -> tuple:
        """Get average and std CO2 for this lane."""
        row = self.lane_stats[
            (self.lane_stats["origin"] == origin) &
            (self.lane_stats["destination"] == destination)
        ]
        if len(row) > 0:
            return (
                float(row["co2_mean"].values[0]),
                float(row["co2_std"].values[0])
            )
        # Unknown lane — use global average
        return (
            float(self.lane_stats["co2_mean"].mean()),
            float(self.lane_stats["co2_std"].mean())
        )

    def _get_vtype_stats(self, vehicle_type: str) -> float:
        """Get average co2_per_km for this vehicle type."""
        row = self.vtype_stats[
            self.vtype_stats["vehicle_type"] == vehicle_type
        ]
        if len(row) > 0:
            return float(row["co2_per_km_mean"].values[0])
        return float(self.vtype_stats["co2_per_km_mean"].mean())

    # ─────────────────────────────────────────
    # EMISSION LABEL
    # ─────────────────────────────────────────
    def _emission_label(self, co2_per_tonne_km: float) -> str:
        if co2_per_tonne_km < 0.08:    return "LOW"
        elif co2_per_tonne_km < 0.14:  return "MEDIUM"
        elif co2_per_tonne_km < 0.20:  return "HIGH"
        else:                           return "VERY_HIGH"

    # ─────────────────────────────────────────
    # REDUCTION TIPS
    # ─────────────────────────────────────────
    def _get_reduction_tips(self,
                             s: dict,
                             co2_kg: float) -> list:
        tips = []

        # Tip 1 — Low load utilization
        util = s.get("load_utilization_pct", 100)
        if util < 70:
            saving = round(co2_kg * 0.15, 1)
            tips.append({
                "action":    "Improve load utilization",
                "detail":    f"Current utilization is {util:.0f}%. "
                             f"Increasing to 85%+ could save ~{saving} kg CO₂",
                "saving_kg": saving,
                "priority":  "HIGH"
            })

        # Tip 2 — Empty return leg
        if s.get("return_empty", 0) == 1:
            saving = round(co2_kg * 0.25, 1)
            tips.append({
                "action":    "Eliminate empty return leg",
                "detail":    f"Find backhaul load for return journey. "
                             f"Potential saving: ~{saving} kg CO₂",
                "saving_kg": saving,
                "priority":  "HIGH"
            })

        # Tip 3 — Old vehicle
        age = s.get("vehicle_age_years", 0)
        if age > 8:
            saving = round(co2_kg * 0.10, 1)
            tips.append({
                "action":    "Replace aging vehicle",
                "detail":    f"Vehicle is {age:.0f} years old. "
                             f"A newer vehicle could save ~{saving} kg CO₂",
                "saving_kg": saving,
                "priority":  "MEDIUM"
            })

        # Tip 4 — Diesel fuel
        if s.get("fuel_type") == "diesel":
            saving = round(co2_kg * 0.30, 1)
            tips.append({
                "action":    "Switch to CNG or Electric",
                "detail":    f"Switching fuel type could save "
                             f"~{saving} kg CO₂ on this route",
                "saving_kg": saving,
                "priority":  "MEDIUM"
            })

        # Tip 5 — Non-highway road
        if s.get("road_type") in ["city", "mountain"]:
            saving = round(co2_kg * 0.08, 1)
            tips.append({
                "action":    "Optimize route to use more highway",
                "detail":    f"Current road type '{s['road_type']}' increases "
                             f"emissions. Highway routing saves ~{saving} kg CO₂",
                "saving_kg": saving,
                "priority":  "LOW"
            })

        # Sort by saving potential
        tips.sort(key=lambda x: x["saving_kg"], reverse=True)
        return tips

    # ─────────────────────────────────────────
    # APPLY SMART DEFAULTS
    # ─────────────────────────────────────────
    def _apply_defaults(self, shipment: dict) -> dict:
        """Fill missing fields with intelligent defaults."""
        s = shipment.copy()

        # Basic defaults
        s.setdefault("goods_category",    "FMCG")
        s.setdefault("num_stops",         1)
        s.setdefault("lane_tier",         2)
        s.setdefault("vehicle_age_years", 5.0)
        s.setdefault("return_empty",      1)
        s.setdefault("quarter",
                     (s.get("month", 6) - 1) // 3 + 1)

        # Infer fuel type from vehicle type
        s.setdefault("fuel_type",
                     FUEL_MAP.get(s.get("vehicle_type", ""), "diesel"))

        # Infer road type from lane tier
        s.setdefault("road_type",
                     TIER_ROAD_MAP.get(s.get("lane_tier", 2), "mixed"))

        # Default carrier
        s.setdefault("carrier_name", "National Roadways Ltd.")

        return s

    # ─────────────────────────────────────────
    # MAIN PREDICT FUNCTION
    # ─────────────────────────────────────────
    def predict(self, shipment: dict) -> dict:
        """
        Predict CO2 emissions for a single shipment.

        Required fields:
            origin              (str)   e.g. "Mumbai"
            destination         (str)   e.g. "Delhi"
            distance_km         (float) e.g. 1400
            vehicle_type        (str)   e.g. "MAV_DIESEL"
            load_weight_tonnes  (float) e.g. 18.5
            month               (int)   1-12

        Optional (auto-inferred if missing):
            fuel_type           (str)   e.g. "diesel"
            road_type           (str)   e.g. "highway"
            carrier_name        (str)
            vehicle_age_years   (float)
            return_empty        (int)   0 or 1
            goods_category      (str)
            num_stops           (int)
            lane_tier           (int)   1, 2, or 3

        Returns:
            dict with full prediction results
        """

        # ── Compute confidence BEFORE filling defaults ──
        confidence = self._compute_confidence(shipment)

        # ── Apply smart defaults ──
        s = self._apply_defaults(shipment)

        # ── Get vehicle capacity ──
        vehicle_info     = VEHICLE_TYPES.get(s["vehicle_type"], {})
        capacity         = vehicle_info.get("capacity_tonnes", 10)
        s["capacity_tonnes"] = capacity

        # ── Load utilization ──
        s["load_utilization_pct"] = round(
            s["load_weight_tonnes"] / capacity * 100, 1
        )

        # ── Get lane & vehicle reference stats ──
        lane_avg, lane_std   = self._get_lane_stats(
            s["origin"], s["destination"])
        vtype_avg_co2_per_km = self._get_vtype_stats(s["vehicle_type"])

        # ── Rough CO2 estimate for relative features ──
        glec_factor      = vehicle_info.get("glec_factor_gco2_per_tkm", 75)
        rough_co2        = (glec_factor
                            * s["distance_km"]
                            * s["load_weight_tonnes"]) / 1000
        rough_co2_per_km = rough_co2 / max(s["distance_km"], 1)

        s["co2_vs_lane_avg"]    = rough_co2 / (lane_avg + 1)
        s["co2_zscore_in_lane"] = (rough_co2 - lane_avg) / (lane_std + 1)
        s["co2_per_km_norm"]    = rough_co2_per_km / (
            vtype_avg_co2_per_km + 0.001)

        # ── Build feature row ──
        row = {}
        for col in FEATURE_COLS:
            if col in CATEGORICAL_COLS:
                row[col] = self._safe_encode(col, str(s.get(col, "")))
            else:
                row[col] = float(s.get(col, 0))

        X = pd.DataFrame([row])[FEATURE_COLS]

        # ── Predict CO2 ──
        co2_kg = float(self.emission_model.predict(X)[0])
        co2_kg = max(co2_kg, 0.0)

        # ── Derived metrics ──
        co2_per_km = co2_kg / max(s["distance_km"], 1)
        co2_per_tonne_km = co2_kg / max(
            s["load_weight_tonnes"] * s["distance_km"], 1)

        # ── Anomaly detection ──
        anomaly_prob = float(
            self.anomaly_model.predict_proba(X)[0][1])
        is_anomaly   = int(anomaly_prob >= 0.5)

        # ── Emission label ──
        label = self._emission_label(co2_per_tonne_km)

        # ── Reduction tips ──
        tips = self._get_reduction_tips(s, co2_kg)
        total_saving = sum(t["saving_kg"] for t in tips)

        # ── Confidence label ──
        if confidence >= 85:    conf_label = "HIGH"
        elif confidence >= 60:  conf_label = "MEDIUM"
        else:                   conf_label = "LOW"

        # ── vs lane average ──
        vs_lane_pct = round(
            (co2_kg - lane_avg) / (lane_avg + 1) * 100, 1)

        # ── Build result ──
        return {
            # Core prediction
            "co2_kg":              round(co2_kg, 2),
            "co2_per_km":          round(co2_per_km, 4),
            "co2_per_tonne_km":    round(co2_per_tonne_km, 6),
            "emission_label":      label,

            # Anomaly
            "is_anomaly":          is_anomaly,
            "anomaly_probability": round(anomaly_prob * 100, 1),

            # Confidence
            "confidence_score":    confidence,
            "confidence_label":    conf_label,

            # Context
            "load_utilization_pct": s["load_utilization_pct"],
            "lane_avg_co2_kg":      round(lane_avg, 2),
            "co2_vs_lane_avg_pct":  vs_lane_pct,

            # Reduction
            "reduction_tips":           tips,
            "total_possible_saving_kg": round(total_saving, 1),
            "optimized_co2_kg":         round(
                max(co2_kg - total_saving, co2_kg * 0.5), 2),

            # Input echo
            "input": {
                "origin":             s["origin"],
                "destination":        s["destination"],
                "distance_km":        s["distance_km"],
                "vehicle_type":       s["vehicle_type"],
                "load_weight_tonnes": s["load_weight_tonnes"],
                "fuel_type":          s["fuel_type"],
                "road_type":          s["road_type"],
                "carrier_name":       s["carrier_name"],
                "vehicle_age_years":  s["vehicle_age_years"],
                "return_empty":       s["return_empty"],
            }
        }


# ─────────────────────────────────────────────
# GENERATE REFERENCE STATS (run once)
# ─────────────────────────────────────────────
def generate_reference_stats():
    DATA_PATH = os.path.join(BASE_DIR, "data", "clean_shipments.csv")
    print("📊 Generating reference stats from clean data...")
    df = pd.read_csv(DATA_PATH)

    # Lane stats
    lane_stats = df.groupby(["origin", "destination"]).agg(
        co2_mean      = ("co2_kg", "mean"),
        co2_std       = ("co2_kg", "std"),
        co2_median    = ("co2_kg", "median"),
        shipment_count= ("co2_kg", "count")
    ).reset_index()
    lane_stats["co2_std"] = lane_stats["co2_std"].fillna(1)
    lane_stats.to_csv(LANE_STATS_PATH, index=False)
    print(f"   ✅ Lane stats  → {LANE_STATS_PATH} "
          f"({len(lane_stats)} lanes)")

    # Vehicle type stats
    vtype_stats = df.groupby("vehicle_type").agg(
        co2_per_km_mean = ("co2_per_km", "mean"),
        co2_per_km_std  = ("co2_per_km", "std"),
    ).reset_index()
    vtype_stats.to_csv(VTYPE_STATS_PATH, index=False)
    print(f"   ✅ Vtype stats → {VTYPE_STATS_PATH} "
          f"({len(vtype_stats)} types)\n")


# ─────────────────────────────────────────────
# PRETTY PRINT
# ─────────────────────────────────────────────
def print_result(result: dict):
    inp = result["input"]
    print("\n" + "=" * 58)
    print("  🌿 CARBON EMISSION PREDICTION RESULT")
    print("=" * 58)
    print(f"\n  📦 Shipment        : "
          f"{inp['origin']} → {inp['destination']}")
    print(f"  📏 Distance        : {inp['distance_km']} km")
    print(f"  🚛 Vehicle         : {inp['vehicle_type']}")
    print(f"  ⛽ Fuel            : {inp['fuel_type'].upper()}")
    print(f"  🛣️  Road Type       : {inp['road_type'].upper()}")
    print(f"  ⚖️  Load            : {inp['load_weight_tonnes']}T  "
          f"({result['load_utilization_pct']:.0f}% utilization)")
    print(f"  🏢 Carrier         : {inp['carrier_name']}")
    print(f"  📅 Return Empty    : "
          f"{'Yes' if inp['return_empty'] else 'No'}")

    print(f"\n  {'─'*52}")
    print(f"  🌍 CO₂ Emission    : {result['co2_kg']:,.2f} kg")
    print(f"  📊 Per km          : {result['co2_per_km']:.4f} kg/km")
    print(f"  📊 Per tonne-km    : {result['co2_per_tonne_km']:.6f} kg/tkm")
    print(f"  🏷️  Emission Label  : {result['emission_label']}")

    vs = result["co2_vs_lane_avg_pct"]
    direction = "above ⬆️" if vs > 0 else "below ⬇️"
    print(f"  📈 vs Lane Avg     : {abs(vs):.1f}% {direction} "
          f"(avg: {result['lane_avg_co2_kg']:,.0f} kg)")

    print(f"\n  {'─'*52}")
    if result["is_anomaly"]:
        print(f"  🚨 ANOMALY         : DETECTED "
              f"({result['anomaly_probability']:.1f}% probability)")
    else:
        print(f"  ✅ Anomaly Status  : Normal "
              f"({result['anomaly_probability']:.1f}% probability)")

    conf_emoji = {"HIGH": "🟢", "MEDIUM": "🟡", "LOW": "🔴"}
    print(f"  {conf_emoji[result['confidence_label']]} "
          f"Confidence        : {result['confidence_score']}/100 "
          f"({result['confidence_label']})")

    if result["reduction_tips"]:
        print(f"\n  {'─'*52}")
        print(f"  💡 REDUCTION OPPORTUNITIES "
              f"(potential: -{result['total_possible_saving_kg']:.0f} kg CO₂)")
        priority_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
        for i, tip in enumerate(result["reduction_tips"], 1):
            print(f"\n  {i}. {priority_emoji[tip['priority']]} "
                  f"[{tip['priority']}] {tip['action']}")
            print(f"     {tip['detail']}")
        print(f"\n  🎯 Optimized CO₂   : "
              f"{result['optimized_co2_kg']:,.2f} kg "
              f"(from {result['co2_kg']:,.2f} kg)")

    print(f"\n{'='*58}\n")


# ─────────────────────────────────────────────
# MAIN — TEST ALL SCENARIOS
# ─────────────────────────────────────────────
if __name__ == "__main__":

    generate_reference_stats()
    predictor = CarbonPredictor()

    # ── Test 1: Normal high-volume shipment ──
    print("📦 TEST 1 — Normal Shipment (Mumbai → Delhi)")
    print_result(predictor.predict({
        "origin":               "Mumbai",
        "destination":          "Delhi",
        "distance_km":          1400,
        "vehicle_type":         "MAV_DIESEL",
        "load_weight_tonnes":   18.5,
        "vehicle_age_years":    5,
        "road_type":            "highway",
        "fuel_type":            "diesel",
        "return_empty":         1,
        "month":                10,
        "carrier_name":         "National Roadways Ltd.",
        "goods_category":       "FMCG",
        "num_stops":            1,
        "lane_tier":            1,
    }))

    # ── Test 2: Underloaded old truck ──
    print("📦 TEST 2 — Underloaded Old Truck (Chennai → Bangalore)")
    print_result(predictor.predict({
        "origin":               "Chennai",
        "destination":          "Bangalore",
        "distance_km":          350,
        "vehicle_type":         "HEAVY_TRUCK_DIESEL",
        "load_weight_tonnes":   4.5,
        "vehicle_age_years":    12,
        "road_type":            "highway",
        "fuel_type":            "diesel",
        "return_empty":         1,
        "month":                6,
        "carrier_name":         "QuickHaul Transport",
        "goods_category":       "Electronics",
        "num_stops":            2,
        "lane_tier":            2,
    }))

    # ── Test 3: Green CNG shipment ──
    print("📦 TEST 3 — Green Shipment (CNG + Full Load)")
    print_result(predictor.predict({
        "origin":               "Delhi",
        "destination":          "Lucknow",
        "distance_km":          550,
        "vehicle_type":         "MEDIUM_TRUCK_CNG",
        "load_weight_tonnes":   7.0,
        "vehicle_age_years":    2,
        "road_type":            "highway",
        "fuel_type":            "cng",
        "return_empty":         0,
        "month":                3,
        "carrier_name":         "GreenFleet Logistics",
        "goods_category":       "FMCG",
        "num_stops":            1,
        "lane_tier":            1,
    }))

    # ── Test 4: Anomaly shipment ──
    print("📦 TEST 4 — Anomaly Shipment (Very High Emissions)")
    print_result(predictor.predict({
        "origin":               "Mumbai",
        "destination":          "Kolkata",
        "distance_km":          2050,
        "vehicle_type":         "HEAVY_TRUCK_DIESEL",
        "load_weight_tonnes":   14.0,
        "vehicle_age_years":    15,
        "road_type":            "mountain",
        "fuel_type":            "diesel",
        "return_empty":         1,
        "month":                10,
        "carrier_name":         "QuickHaul Transport",
        "goods_category":       "Construction Material",
        "num_stops":            3,
        "lane_tier":            1,
    }))

    # ── Test 5: Minimal input (auto-inference test) ──
    print("📦 TEST 5 — Minimal Input (Auto-Inference)")
    print_result(predictor.predict({
        "origin":               "Hyderabad",
        "destination":          "Chennai",
        "distance_km":          630,
        "vehicle_type":         "HEAVY_TRUCK_DIESEL",
        "load_weight_tonnes":   10.0,
        "month":                8,
        # All other fields auto-inferred — no warnings expected
    }))