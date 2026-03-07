# src/emission_factors.py
# ============================================================
# Emission Factor Lookup Tables
# Standards: GLEC Framework + GHG Protocol WTW + India MoRTH
# ============================================================

import pandas as pd
import numpy as np

# ─────────────────────────────────────────────
# 1. VEHICLE TYPE MASTER TABLE
# ─────────────────────────────────────────────
VEHICLE_TYPES = {
    "LCV_DIESEL": {
        "label": "Light Commercial Vehicle (Diesel)",
        "capacity_tonnes": 2,
        "glec_factor_gco2_per_tkm": 120,
        "morth_multiplier": 1.15,
        "age_degradation_per_year": 0.012,
        "fuel_type": "diesel"
    },
    "MEDIUM_TRUCK_DIESEL": {
        "label": "Medium Truck (Diesel)",
        "capacity_tonnes": 7.5,
        "glec_factor_gco2_per_tkm": 95,
        "morth_multiplier": 1.12,
        "age_degradation_per_year": 0.011,
        "fuel_type": "diesel"
    },
    "HEAVY_TRUCK_DIESEL": {
        "label": "Heavy Truck 10-15T (Diesel)",
        "capacity_tonnes": 15,
        "glec_factor_gco2_per_tkm": 75,
        "morth_multiplier": 1.10,
        "age_degradation_per_year": 0.010,
        "fuel_type": "diesel"
    },
    "MAV_DIESEL": {
        "label": "Multi-Axle Vehicle 20-25T (Diesel)",
        "capacity_tonnes": 25,
        "glec_factor_gco2_per_tkm": 62,
        "morth_multiplier": 1.08,
        "age_degradation_per_year": 0.009,
        "fuel_type": "diesel"
    },
    "TRAILER_40T_DIESEL": {
        "label": "Trailer / 40T (Diesel)",
        "capacity_tonnes": 40,
        "glec_factor_gco2_per_tkm": 55,
        "morth_multiplier": 1.06,
        "age_degradation_per_year": 0.008,
        "fuel_type": "diesel"
    },
    "MEDIUM_TRUCK_CNG": {
        "label": "Medium Truck (CNG)",
        "capacity_tonnes": 7.5,
        "glec_factor_gco2_per_tkm": 58,
        "morth_multiplier": 0.90,
        "age_degradation_per_year": 0.010,
        "fuel_type": "cng"
    },
    "HEAVY_TRUCK_CNG": {
        "label": "Heavy Truck (CNG)",
        "capacity_tonnes": 15,
        "glec_factor_gco2_per_tkm": 52,
        "morth_multiplier": 0.88,
        "age_degradation_per_year": 0.009,
        "fuel_type": "cng"
    },
    "ELECTRIC_TRUCK": {
        "label": "Electric Truck",
        "capacity_tonnes": 5,
        "glec_factor_gco2_per_tkm": 18,
        "morth_multiplier": 0.85,
        "age_degradation_per_year": 0.005,
        "fuel_type": "electric"
    },
    "REEFER_DIESEL": {
        "label": "Refrigerated Truck (Reefer)",
        "capacity_tonnes": 10,
        "glec_factor_gco2_per_tkm": 90,
        "morth_multiplier": 1.25,
        "age_degradation_per_year": 0.013,
        "fuel_type": "diesel"
    },
}


# ─────────────────────────────────────────────
# 2. ROAD TYPE MULTIPLIERS (MoRTH-based)
# ─────────────────────────────────────────────
ROAD_TYPE_FACTORS = {
    "highway":     0.92,   # Best fuel efficiency, smooth surface
    "mixed":       1.00,   # Baseline
    "city":        1.22,   # Stop-start traffic, congestion
    "mountain":    1.35,   # Steep grades, low speed
    "rural":       1.10,   # Unpaved or semi-paved roads
}


# ─────────────────────────────────────────────
# 3. GHG PROTOCOL WELL-TO-WHEEL (WTW) MULTIPLIERS
# Converts Tank-to-Wheel (TTW) → Well-to-Wheel (WTW)
# Accounts for fuel extraction, refining, and transport
# ─────────────────────────────────────────────
GHG_WTW_MULTIPLIERS = {
    "diesel":   1.18,   # Includes upstream diesel production emissions
    "cng":      1.12,   # Lower upstream than diesel
    "electric": 1.45,   # India grid is coal-heavy (as of 2024)
}


# ─────────────────────────────────────────────
# 4. INDIAN LANE MASTER TABLE
# Real Origin-Destination pairs with road distances
# ─────────────────────────────────────────────
INDIAN_LANES = [
    # Tier 1 — National Corridors
    {"origin": "Mumbai",      "destination": "Delhi",       "distance_km": 1400, "road_type": "highway",  "tier": 1},
    {"origin": "Delhi",       "destination": "Kolkata",     "distance_km": 1500, "road_type": "highway",  "tier": 1},
    {"origin": "Chennai",     "destination": "Mumbai",      "distance_km": 1330, "road_type": "highway",  "tier": 1},
    {"origin": "Bangalore",   "destination": "Delhi",       "distance_km": 2150, "road_type": "mixed",    "tier": 1},
    {"origin": "Hyderabad",   "destination": "Mumbai",      "distance_km": 710,  "road_type": "highway",  "tier": 1},
    {"origin": "Mumbai",      "destination": "Kolkata",     "distance_km": 2050, "road_type": "highway",  "tier": 1},
    {"origin": "Delhi",       "destination": "Chennai",     "distance_km": 2200, "road_type": "highway",  "tier": 1},

    # Tier 2 — Regional Lanes
    {"origin": "Chennai",     "destination": "Bangalore",   "distance_km": 350,  "road_type": "highway",  "tier": 2},
    {"origin": "Hyderabad",   "destination": "Chennai",     "distance_km": 630,  "road_type": "mixed",    "tier": 2},
    {"origin": "Ahmedabad",   "destination": "Mumbai",      "distance_km": 530,  "road_type": "highway",  "tier": 2},
    {"origin": "Pune",        "destination": "Mumbai",      "distance_km": 150,  "road_type": "highway",  "tier": 2},
    {"origin": "Jaipur",      "destination": "Delhi",       "distance_km": 280,  "road_type": "highway",  "tier": 2},
    {"origin": "Lucknow",     "destination": "Delhi",       "distance_km": 550,  "road_type": "highway",  "tier": 2},
    {"origin": "Nagpur",      "destination": "Mumbai",      "distance_km": 830,  "road_type": "mixed",    "tier": 2},
    {"origin": "Coimbatore",  "destination": "Chennai",     "distance_km": 500,  "road_type": "highway",  "tier": 2},
    {"origin": "Ahmedabad",   "destination": "Surat",       "distance_km": 270,  "road_type": "highway",  "tier": 2},
    {"origin": "Kolkata",     "destination": "Bhubaneswar", "distance_km": 440,  "road_type": "mixed",    "tier": 2},
    {"origin": "Delhi",       "destination": "Amritsar",    "distance_km": 450,  "road_type": "highway",  "tier": 2},

    # Tier 3 — Short Haul / Last Mile
    {"origin": "Mumbai",      "destination": "Pune",        "distance_km": 150,  "road_type": "highway",  "tier": 3},
    {"origin": "Delhi",       "destination": "Gurgaon",     "distance_km": 32,   "road_type": "city",     "tier": 3},
    {"origin": "Bangalore",   "destination": "Mysore",      "distance_km": 145,  "road_type": "highway",  "tier": 3},
    {"origin": "Chennai",     "destination": "Pondicherry", "distance_km": 160,  "road_type": "mixed",    "tier": 3},
    {"origin": "Hyderabad",   "destination": "Warangal",    "distance_km": 145,  "road_type": "mixed",    "tier": 3},
    {"origin": "Kolkata",     "destination": "Howrah",      "distance_km": 25,   "road_type": "city",     "tier": 3},
    {"origin": "Mumbai",      "destination": "Thane",       "distance_km": 35,   "road_type": "city",     "tier": 3},

    # Mountain / Difficult Terrain
    {"origin": "Delhi",       "destination": "Shimla",      "distance_km": 370,  "road_type": "mountain", "tier": 2},
    {"origin": "Delhi",       "destination": "Manali",      "distance_km": 540,  "road_type": "mountain", "tier": 2},
    {"origin": "Kolkata",     "destination": "Siliguri",    "distance_km": 600,  "road_type": "mixed",    "tier": 2},
    {"origin": "Guwahati",    "destination": "Shillong",    "distance_km": 100,  "road_type": "mountain", "tier": 3},

    # Rural / Industrial Zones
    {"origin": "Pune",        "destination": "Nashik",      "distance_km": 210,  "road_type": "rural",    "tier": 3},
    {"origin": "Surat",       "destination": "Vadodara",    "distance_km": 130,  "road_type": "highway",  "tier": 3},
    {"origin": "Ludhiana",    "destination": "Delhi",       "distance_km": 310,  "road_type": "highway",  "tier": 2},
    {"origin": "Indore",      "destination": "Bhopal",      "distance_km": 195,  "road_type": "highway",  "tier": 3},
]


# ─────────────────────────────────────────────
# 5. SEASONAL DEMAND MULTIPLIERS
# Affects number of shipments per month (not CO2 directly)
# ─────────────────────────────────────────────
SEASONAL_MULTIPLIERS = {
    1:  0.85,   # January   — post-festive slowdown
    2:  0.80,   # February  — lowest demand
    3:  0.95,   # March     — fiscal year end push
    4:  0.90,   # April     — summer slowdown starts
    5:  0.88,   # May       — peak summer
    6:  0.92,   # June      — monsoon begins
    7:  0.90,   # July      — monsoon peak
    8:  0.93,   # August    — slight recovery
    9:  1.05,   # September — pre-festive buildup
    10: 1.25,   # October   — Diwali peak
    11: 1.20,   # November  — post-Diwali surge
    12: 1.10,   # December  — year-end push
}


# ─────────────────────────────────────────────
# 6. CARRIER PERFORMANCE PROFILES
# Some carriers are more efficient than others
# ─────────────────────────────────────────────
CARRIER_PROFILES = {
    "GreenFleet Logistics":     {"efficiency_factor": 0.88, "reliability": 0.95},  # Best in class
    "Bharat Transport Co.":     {"efficiency_factor": 0.95, "reliability": 0.90},  # Above average
    "National Roadways Ltd.":   {"efficiency_factor": 1.00, "reliability": 0.85},  # Baseline
    "FastMove Carriers":        {"efficiency_factor": 1.05, "reliability": 0.88},  # Slightly worse
    "IndiaFreight Services":    {"efficiency_factor": 1.10, "reliability": 0.80},  # Below average
    "QuickHaul Transport":      {"efficiency_factor": 1.15, "reliability": 0.75},  # Poor efficiency
    "Metro Logistics Pvt Ltd":  {"efficiency_factor": 0.92, "reliability": 0.93},  # Good
    "Eastern Cargo Express":    {"efficiency_factor": 1.08, "reliability": 0.78},  # Below average
}


# ─────────────────────────────────────────────
# 7. CORE EMISSION CALCULATION FUNCTION
# ─────────────────────────────────────────────
def calculate_co2(
    distance_km: float,
    load_weight_tonnes: float,
    vehicle_type: str,
    vehicle_age_years: float,
    road_type: str,
    return_empty: bool,
    carrier_name: str = None
) -> dict:
    """
    Calculate CO₂ emissions for a single shipment.

    Combines:
    - GLEC Framework base emission factors
    - MoRTH India road condition multipliers
    - GHG Protocol Well-to-Wheel (WTW) multipliers
    - Vehicle age degradation
    - Load utilization adjustment
    - Empty return leg addition
    - Carrier efficiency factor

    Returns:
        dict with co2_kg, breakdown, and confidence score
    """

    vehicle = VEHICLE_TYPES[vehicle_type]
    capacity = vehicle["capacity_tonnes"]
    glec_factor = vehicle["glec_factor_gco2_per_tkm"]
    morth_mult = vehicle["morth_multiplier"]
    age_degr = vehicle["age_degradation_per_year"]
    fuel = vehicle["fuel_type"]

    # Load utilization factor (penalize underloaded trucks)
    load_util = load_weight_tonnes / capacity
    load_util = min(load_util, 1.0)  # cap at 100%
    load_factor = 0.7 + (0.3 * load_util)  # range: 0.7 (empty) to 1.0 (full)

    # Vehicle age degradation
    age_factor = 1 + (age_degr * vehicle_age_years)

    # Road type factor
    road_factor = ROAD_TYPE_FACTORS.get(road_type, 1.0)

    # GHG WTW multiplier
    wtw_factor = GHG_WTW_MULTIPLIERS.get(fuel, 1.18)

    # Carrier efficiency
    carrier_factor = 1.0
    if carrier_name and carrier_name in CARRIER_PROFILES:
        carrier_factor = CARRIER_PROFILES[carrier_name]["efficiency_factor"]

    # Base CO₂ calculation (grams)
    base_co2_grams = (
        glec_factor
        * distance_km
        * load_weight_tonnes
    )

    # Adjusted CO₂ (grams) with all multipliers
    adjusted_co2_grams = (
        base_co2_grams
        * morth_mult
        * age_factor
        * road_factor
        * wtw_factor
        * load_factor
        * carrier_factor
    )

    # Convert to kg
    adjusted_co2_kg = adjusted_co2_grams / 1000

    # Empty return leg adds ~40% of one-way emissions
    return_co2_kg = 0
    if return_empty:
        return_co2_kg = adjusted_co2_kg * 0.40

    total_co2_kg = adjusted_co2_kg + return_co2_kg

    return {
        "co2_kg": round(total_co2_kg, 2),
        "co2_kg_loaded_leg": round(adjusted_co2_kg, 2),
        "co2_kg_return_leg": round(return_co2_kg, 2),
        "load_utilization_pct": round(load_util * 100, 1),
        "breakdown": {
            "base_co2_kg": round(base_co2_grams / 1000, 2),
            "morth_multiplier": morth_mult,
            "age_factor": round(age_factor, 3),
            "road_factor": road_factor,
            "wtw_factor": wtw_factor,
            "load_factor": round(load_factor, 3),
            "carrier_factor": carrier_factor,
        }
    }


# ─────────────────────────────────────────────
# 8. EXPORT LOOKUP TABLES AS DATAFRAMES
# ─────────────────────────────────────────────
def get_vehicle_table() -> pd.DataFrame:
    rows = []
    for code, v in VEHICLE_TYPES.items():
        rows.append({"vehicle_code": code, **v})
    return pd.DataFrame(rows)


def get_lane_table() -> pd.DataFrame:
    return pd.DataFrame(INDIAN_LANES)


def get_carrier_table() -> pd.DataFrame:
    rows = []
    for name, p in CARRIER_PROFILES.items():
        rows.append({"carrier_name": name, **p})
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────
# QUICK TEST
# ─────────────────────────────────────────────
if __name__ == "__main__":
    result = calculate_co2(
        distance_km=1400,
        load_weight_tonnes=18,
        vehicle_type="MAV_DIESEL",
        vehicle_age_years=5,
        road_type="highway",
        return_empty=True,
        carrier_name="National Roadways Ltd."
    )
    print("\n✅ Test Emission Calculation — Mumbai → Delhi")
    print(f"   Total CO₂     : {result['co2_kg']} kg")
    print(f"   Loaded leg    : {result['co2_kg_loaded_leg']} kg")
    print(f"   Return leg    : {result['co2_kg_return_leg']} kg")
    print(f"   Load util     : {result['load_utilization_pct']}%")
    print(f"\n   Breakdown     : {result['breakdown']}")

    print("\n📋 Vehicle Types Available:")
    print(get_vehicle_table()[["vehicle_code", "capacity_tonnes",
                                "glec_factor_gco2_per_tkm", "fuel_type"]])

    print("\n🗺️  Lanes Available:", len(get_lane_table()))
    print(get_lane_table()[["origin", "destination",
                             "distance_km", "road_type", "tier"]].head(8))