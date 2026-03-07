# src/agents/tools.py
# ============================================================
# Real Tool Functions for LangGraph Agents
# These are actual data operations on clean_shipments.csv
# LLM decides WHEN and HOW to call these — never hardcoded
# ============================================================

import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from langchain.tools import tool

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from predict import CarbonPredictor, generate_reference_stats

# ─────────────────────────────────────────────
# GLOBAL DATA LOADER
# Load once, reuse across all tools
# ─────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
DATA_PATH  = os.path.join(BASE_DIR, "data", "clean_shipments.csv")
STATS_PATH = os.path.join(BASE_DIR, "data", "lane_stats.csv")

_df    = None
_stats = None
_predictor = None

def get_df() -> pd.DataFrame:
    global _df
    if _df is None:
        _df = pd.read_csv(DATA_PATH)
        _df["shipment_date"] = pd.to_datetime(_df["shipment_date"])
    return _df

def get_stats() -> pd.DataFrame:
    global _stats
    if _stats is None:
        _stats = pd.read_csv(STATS_PATH)
    return _stats

def get_predictor() -> CarbonPredictor:
    global _predictor
    if _predictor is None:
        _predictor = CarbonPredictor()
    return _predictor


# ═══════════════════════════════════════════════════════
# ANOMALY MONITOR TOOLS
# ═══════════════════════════════════════════════════════

@tool
def scan_fleet_for_anomalies(month: int, year: int, top_n: int = 10) -> str:
    """
    Scan all shipments in a given month/year and return
    the top anomalous shipments ranked by severity.
    Use this to find which shipments had unusually high emissions.

    Args:
        month: Month number (1-12)
        year:  Year (e.g. 2024)
        top_n: How many top anomalies to return (default 10)
    """
    df = get_df()

    filtered = df[
        (df["shipment_date"].dt.month == month) &
        (df["shipment_date"].dt.year  == year)
    ].copy()

    if filtered.empty:
        return json.dumps({
            "status": "no_data",
            "message": f"No shipments found for {month}/{year}"
        })

    # Get anomalies
    anomalies = filtered[filtered["is_anomaly"] == 1].copy()

    if anomalies.empty:
        return json.dumps({
            "status":           "clean",
            "message":          f"No anomalies found in {month}/{year}",
            "total_shipments":  len(filtered),
            "anomaly_count":    0,
        })

    # Compute severity = how many times above lane average
    stats = get_stats()
    anomalies = anomalies.merge(
        stats[["origin", "destination", "co2_mean"]],
        on=["origin", "destination"], how="left"
    )
    anomalies["severity_ratio"] = (
        anomalies["co2_kg"] / anomalies["co2_mean"].fillna(
            anomalies["co2_kg"].mean())
    ).round(2)

    top = anomalies.nlargest(top_n, "severity_ratio")[[
        "shipment_id", "shipment_date", "origin", "destination",
        "vehicle_type", "carrier_name", "co2_kg",
        "co2_mean", "severity_ratio", "anomaly_reason"
    ]]

    return json.dumps({
        "status":          "anomalies_found",
        "month":           month,
        "year":            year,
        "total_shipments": int(len(filtered)),
        "anomaly_count":   int(len(anomalies)),
        "anomaly_rate_pct": round(len(anomalies) / len(filtered) * 100, 2),
        "top_anomalies":   top.to_dict(orient="records"),
    }, default=str)


@tool
def get_shipment_details(shipment_id: str) -> str:
    """
    Get full details of a specific shipment by its ID.
    Use this after finding anomalies to investigate deeper.

    Args:
        shipment_id: e.g. "SHP004521"
    """
    df  = get_df()
    row = df[df["shipment_id"] == shipment_id]

    if row.empty:
        return json.dumps({
            "status":  "not_found",
            "message": f"Shipment {shipment_id} not found"
        })

    record = row.iloc[0].to_dict()

    # Add lane average for context
    stats = get_stats()
    lane  = stats[
        (stats["origin"]      == record["origin"]) &
        (stats["destination"] == record["destination"])
    ]
    if not lane.empty:
        record["lane_avg_co2_kg"]  = round(float(lane["co2_mean"].values[0]), 2)
        record["lane_std_co2_kg"]  = round(float(lane["co2_std"].values[0]), 2)
        record["co2_vs_lane_pct"]  = round(
            (record["co2_kg"] - record["lane_avg_co2_kg"]) /
            record["lane_avg_co2_kg"] * 100, 1
        )

    return json.dumps({"status": "found", "shipment": record}, default=str)


@tool
def get_anomaly_root_cause(shipment_id: str) -> str:
    """
    Analyze a shipment and identify the root causes
    of its high emissions. Returns ranked factors.
    Use this after get_shipment_details to explain WHY.

    Args:
        shipment_id: e.g. "SHP004521"
    """
    df  = get_df()
    row = df[df["shipment_id"] == shipment_id]

    if row.empty:
        return json.dumps({"status": "not_found"})

    r      = row.iloc[0]
    causes = []

    # Check each emission driver
    if r["load_utilization_pct"] < 50:
        causes.append({
            "factor":   "Very low load utilization",
            "value":    f"{r['load_utilization_pct']:.1f}%",
            "impact":   "HIGH",
            "detail":   "Truck running nearly empty wastes fuel per tonne moved"
        })
    elif r["load_utilization_pct"] < 70:
        causes.append({
            "factor":  "Below average load utilization",
            "value":   f"{r['load_utilization_pct']:.1f}%",
            "impact":  "MEDIUM",
            "detail":  "Suboptimal loading increases per-tonne emissions"
        })

    if r["vehicle_age_years"] > 10:
        causes.append({
            "factor":  "Aging vehicle",
            "value":   f"{r['vehicle_age_years']:.0f} years old",
            "impact":  "HIGH",
            "detail":  "Older engines are less fuel efficient"
        })

    if r["road_type"] in ["mountain", "city"]:
        causes.append({
            "factor":  f"Difficult road type: {r['road_type']}",
            "value":   r["road_type"],
            "impact":  "MEDIUM",
            "detail":  "Non-highway roads significantly increase fuel consumption"
        })

    if r["return_empty"] == 1:
        causes.append({
            "factor":  "Empty return leg",
            "value":   "Yes",
            "impact":  "MEDIUM",
            "detail":  "Returning empty adds ~40% to effective emissions"
        })

    if r["fuel_type"] == "diesel":
        causes.append({
            "factor":  "Diesel fuel",
            "value":   "diesel",
            "impact":  "LOW",
            "detail":  "Higher carbon intensity vs CNG or electric"
        })

    anomaly_reason = r.get("anomaly_reason", "none")
    if anomaly_reason != "none":
        causes.insert(0, {
            "factor":  "Injected anomaly type",
            "value":   anomaly_reason,
            "impact":  "CRITICAL",
            "detail":  f"Anomaly pattern detected: {anomaly_reason}"
        })

    return json.dumps({
        "shipment_id":    shipment_id,
        "co2_kg":         float(r["co2_kg"]),
        "root_causes":    causes,
        "total_factors":  len(causes),
    }, default=str)


@tool
def get_carrier_anomaly_history(carrier_name: str) -> str:
    """
    Get anomaly history and emission performance for a specific carrier.
    Use this to evaluate carrier reliability and emission efficiency.

    Args:
        carrier_name: e.g. "QuickHaul Transport"
    """
    df = get_df()

    carrier_df = df[df["carrier_name"] == carrier_name]
    if carrier_df.empty:
        return json.dumps({
            "status":  "not_found",
            "message": f"Carrier '{carrier_name}' not found"
        })

    fleet_anomaly_rate = df["is_anomaly"].mean() * 100

    result = {
        "carrier_name":          carrier_name,
        "total_shipments":       int(len(carrier_df)),
        "anomaly_count":         int(carrier_df["is_anomaly"].sum()),
        "anomaly_rate_pct":      round(
            carrier_df["is_anomaly"].mean() * 100, 2),
        "fleet_avg_anomaly_pct": round(fleet_anomaly_rate, 2),
        "anomaly_vs_fleet":      round(
            carrier_df["is_anomaly"].mean() * 100 -
            fleet_anomaly_rate, 2),
        "avg_co2_kg":            round(
            float(carrier_df["co2_kg"].mean()), 2),
        "avg_load_util_pct":     round(
            float(carrier_df["load_utilization_pct"].mean()), 2),
        "avg_vehicle_age_yrs":   round(
            float(carrier_df["vehicle_age_years"].mean()), 2),
        "top_anomaly_reasons":   carrier_df[
            carrier_df["is_anomaly"] == 1
        ]["anomaly_reason"].value_counts().head(3).to_dict(),
    }

    return json.dumps(result, default=str)


# ═══════════════════════════════════════════════════════
# TREND FORECASTER TOOLS
# ═══════════════════════════════════════════════════════

@tool
def get_emission_trend(origin: str, destination: str,
                       period_days: int = 90) -> str:
    """
    Get CO2 emission trend for a specific lane over recent days.
    Returns monthly averages and direction of trend.

    Args:
        origin:       e.g. "Mumbai"
        destination:  e.g. "Delhi"
        period_days:  lookback window in days (default 90)
    """
    df   = get_df()
    cutoff = df["shipment_date"].max() - timedelta(days=period_days)

    lane_df = df[
        (df["origin"]      == origin) &
        (df["destination"] == destination) &
        (df["shipment_date"] >= cutoff)
    ].copy()

    if lane_df.empty:
        return json.dumps({
            "status":  "no_data",
            "message": f"No data for {origin}→{destination} "
                       f"in last {period_days} days"
        })

    lane_df["month_year"] = lane_df["shipment_date"].dt.to_period("M")
    monthly = lane_df.groupby("month_year").agg(
        avg_co2      = ("co2_kg",             "mean"),
        total_co2    = ("co2_kg",             "sum"),
        shipments    = ("co2_kg",             "count"),
        anomaly_rate = ("is_anomaly",         "mean"),
    ).reset_index()
    monthly["month_year"] = monthly["month_year"].astype(str)

    # Trend direction
    if len(monthly) >= 2:
        first_half = monthly.iloc[:len(monthly)//2]["avg_co2"].mean()
        second_half = monthly.iloc[len(monthly)//2:]["avg_co2"].mean()
        trend_pct  = round(
            (second_half - first_half) / first_half * 100, 2)
        trend_dir  = "INCREASING" if trend_pct > 2 else (
            "DECREASING" if trend_pct < -2 else "STABLE")
    else:
        trend_pct = 0
        trend_dir = "INSUFFICIENT_DATA"

    return json.dumps({
        "lane":          f"{origin}→{destination}",
        "period_days":   period_days,
        "trend":         trend_dir,
        "trend_pct":     trend_pct,
        "monthly_data":  monthly.to_dict(orient="records"),
        "total_co2_kg":  round(float(lane_df["co2_kg"].sum()), 2),
        "avg_co2_kg":    round(float(lane_df["co2_kg"].mean()), 2),
    }, default=str)


@tool
def get_month_over_month_change(year: int = 2024) -> str:
    """
    Get month-over-month emission changes for the entire fleet.
    Shows which months had increasing vs decreasing emissions.

    Args:
        year: Year to analyze (default 2024)
    """
    df = get_df()

    yearly = df[df["shipment_date"].dt.year == year].copy()
    if yearly.empty:
        return json.dumps({
            "status":  "no_data",
            "message": f"No data for year {year}"
        })

    monthly = yearly.groupby(
        yearly["shipment_date"].dt.month
    ).agg(
        total_co2    = ("co2_kg",     "sum"),
        avg_co2      = ("co2_kg",     "mean"),
        shipments    = ("co2_kg",     "count"),
        anomaly_rate = ("is_anomaly", "mean"),
    ).reset_index()
    monthly.columns = [
        "month", "total_co2", "avg_co2",
        "shipments", "anomaly_rate"
    ]

    # Month over month change
    monthly["mom_change_pct"] = (
    monthly["total_co2"].pct_change() * 100
).round(2)

    # Peak and lowest months
    peak_month   = int(monthly.loc[
        monthly["total_co2"].idxmax(), "month"])
    lowest_month = int(monthly.loc[
        monthly["total_co2"].idxmin(), "month"])

    return json.dumps({
        "year":            year,
        "peak_month":      peak_month,
        "lowest_month":    lowest_month,
        "total_year_co2":  round(float(monthly["total_co2"].sum()), 2),
        "monthly_data":    monthly.round(2).to_dict(orient="records"),
    }, default=str)


@tool
def forecast_future_emissions(origin: str,
                               destination: str,
                               days_ahead: int = 30) -> str:
    """
    Forecast future CO2 emissions for a lane using
    historical trend and seasonal patterns.

    Args:
        origin:      e.g. "Mumbai"
        destination: e.g. "Delhi"
        days_ahead:  forecast horizon in days (default 30)
    """
    df = get_df()

    lane_df = df[
        (df["origin"]      == origin) &
        (df["destination"] == destination)
    ].copy()

    if len(lane_df) < 10:
        return json.dumps({
            "status":  "insufficient_data",
            "message": f"Need at least 10 records for {origin}→{destination}"
        })

    # Monthly averages
    lane_df["month"] = lane_df["shipment_date"].dt.month
    monthly_avg = lane_df.groupby("month")["co2_kg"].mean()

    # Seasonal index
    overall_avg   = float(monthly_avg.mean())
    seasonal_idx  = (monthly_avg / overall_avg).to_dict()

    # Recent trend (last 90 days)
    cutoff        = lane_df["shipment_date"].max() - timedelta(days=90)
    recent        = lane_df[lane_df["shipment_date"] >= cutoff]
    recent_avg    = float(recent["co2_kg"].mean())
    historical_avg = float(lane_df["co2_kg"].mean())
    trend_factor  = recent_avg / (historical_avg + 1e-9)

    # Forecast
    future_month  = (datetime.now() +
                     timedelta(days=days_ahead)).month
    season_factor = seasonal_idx.get(future_month, 1.0)
    forecast_avg  = round(recent_avg * trend_factor * season_factor, 2)

    return json.dumps({
        "lane":              f"{origin}→{destination}",
        "days_ahead":        days_ahead,
        "current_avg_co2":   round(recent_avg, 2),
        "forecasted_avg_co2": forecast_avg,
        "trend_factor":      round(trend_factor, 3),
        "seasonal_factor":   round(season_factor, 3),
        "forecast_month":    future_month,
        "change_pct":        round(
            (forecast_avg - recent_avg) / recent_avg * 100, 2),
    }, default=str)


@tool
def check_target_compliance(
        target_annual_co2_tonnes: float,
        year: int = 2024) -> str:
    """
    Check if the fleet is on track to meet annual CO2
    reduction targets. Returns compliance status.

    Args:
        target_annual_co2_tonnes: Annual CO2 target in tonnes
        year: Year to check (default 2024)
    """
    df = get_df()

    yearly = df[df["shipment_date"].dt.year == year]
    if yearly.empty:
        return json.dumps({
            "status":  "no_data",
            "message": f"No data for year {year}"
        })

    actual_tonnes = float(yearly["co2_kg"].sum()) / 1000
    target_kg     = target_annual_co2_tonnes * 1000
    months_done   = yearly["shipment_date"].dt.month.nunique()
    monthly_avg   = actual_tonnes / max(months_done, 1)
    projected     = monthly_avg * 12

    gap_tonnes    = projected - target_annual_co2_tonnes
    on_track      = projected <= target_annual_co2_tonnes

    return json.dumps({
        "year":                       year,
        "target_annual_co2_tonnes":   target_annual_co2_tonnes,
        "actual_co2_tonnes_so_far":   round(actual_tonnes, 2),
        "projected_annual_tonnes":    round(projected, 2),
        "gap_tonnes":                 round(gap_tonnes, 2),
        "on_track":                   on_track,
        "months_analyzed":            months_done,
        "monthly_avg_tonnes":         round(monthly_avg, 2),
        "reduction_needed_pct":       round(
            gap_tonnes / target_annual_co2_tonnes * 100, 2
        ) if not on_track else 0,
    }, default=str)


# ═══════════════════════════════════════════════════════
# REDUCTION ADVISOR TOOLS
# ═══════════════════════════════════════════════════════

@tool
def get_top_emission_lanes(top_n: int = 10) -> str:
    """
    Find the highest CO2 emitting lanes in the fleet.
    Returns lanes ranked by total and average emissions.

    Args:
        top_n: Number of top lanes to return (default 10)
    """
    df = get_df()

    lane_summary = df.groupby(
        ["origin", "destination"]
    ).agg(
        total_co2_kg    = ("co2_kg", "sum"),
        avg_co2_kg      = ("co2_kg", "mean"),
        shipment_count  = ("co2_kg", "count"),
        avg_util_pct    = ("load_utilization_pct", "mean"),
        anomaly_rate    = ("is_anomaly",           "mean"),
        dominant_vehicle= ("vehicle_type", lambda x:
                           x.value_counts().index[0]),
    ).reset_index()

    lane_summary["co2_per_shipment"] = (
        lane_summary["total_co2_kg"] /
        lane_summary["shipment_count"]
    ).round(2)

    top = lane_summary.nlargest(
        top_n, "total_co2_kg"
    ).round(2)

    return json.dumps({
        "top_n":       top_n,
        "top_lanes":   top.to_dict(orient="records"),
        "total_fleet_co2_kg": round(
            float(df["co2_kg"].sum()), 2),
        "top_lanes_share_pct": round(
            float(top["total_co2_kg"].sum()) /
            float(df["co2_kg"].sum()) * 100, 2),
    }, default=str)


@tool
def simulate_fuel_switch_saving(
        origin: str,
        destination: str,
        from_fuel: str,
        to_fuel: str) -> str:
    """
    Simulate CO2 savings if a lane switches from one
    fuel type to another (e.g. diesel → CNG).

    Args:
        origin:      e.g. "Mumbai"
        destination: e.g. "Delhi"
        from_fuel:   current fuel e.g. "diesel"
        to_fuel:     target fuel e.g. "cng"
    """
    df = get_df()

    lane_from = df[
        (df["origin"]      == origin) &
        (df["destination"] == destination) &
        (df["fuel_type"]   == from_fuel)
    ]

    lane_to = df[
        (df["origin"]      == origin) &
        (df["destination"] == destination) &
        (df["fuel_type"]   == to_fuel)
    ]

    if lane_from.empty:
        return json.dumps({
            "status":  "no_data",
            "message": f"No {from_fuel} shipments on {origin}→{destination}"
        })

    current_avg  = float(lane_from["co2_kg"].mean())
    current_total = float(lane_from["co2_kg"].sum())

    # Emission factor ratios from standards
    fuel_factors = {"diesel": 1.0, "cng": 0.72, "electric": 0.22}
    factor_from  = fuel_factors.get(from_fuel, 1.0)
    factor_to    = fuel_factors.get(to_fuel,   1.0)
    saving_ratio = 1 - (factor_to / factor_from)

    if not lane_to.empty:
        # Use actual data if available
        target_avg   = float(lane_to["co2_kg"].mean())
        saving_per_shipment = current_avg - target_avg
    else:
        # Use emission factor ratio
        target_avg   = current_avg * (factor_to / factor_from)
        saving_per_shipment = current_avg - target_avg

    total_saving = saving_per_shipment * len(lane_from)

    return json.dumps({
        "lane":                   f"{origin}→{destination}",
        "from_fuel":              from_fuel,
        "to_fuel":                to_fuel,
        "current_avg_co2_kg":     round(current_avg, 2),
        "projected_avg_co2_kg":   round(target_avg, 2),
        "saving_per_shipment_kg": round(saving_per_shipment, 2),
        "total_annual_saving_kg": round(total_saving, 2),
        "saving_pct":             round(saving_ratio * 100, 2),
        "shipments_affected":     int(len(lane_from)),
    }, default=str)


@tool
def simulate_load_improvement_saving(
        origin: str,
        destination: str,
        target_utilization_pct: float = 85.0) -> str:
    """
    Simulate CO2 savings if load utilization is improved
    on a specific lane to the target percentage.

    Args:
        origin:                  e.g. "Mumbai"
        destination:             e.g. "Delhi"
        target_utilization_pct:  target load util % (default 85)
    """
    df = get_df()

    lane = df[
        (df["origin"]      == origin) &
        (df["destination"] == destination) &
        (df["load_utilization_pct"] < target_utilization_pct)
    ]

    if lane.empty:
        return json.dumps({
            "status":  "already_optimal",
            "message": f"{origin}→{destination} already at "
                       f"{target_utilization_pct}%+ utilization"
        })

    current_avg_util = float(lane["load_utilization_pct"].mean())
    current_avg_co2  = float(lane["co2_kg"].mean())

    # CO2 scales with load factor: 0.7 + 0.3 * util
    current_load_factor = 0.7 + 0.3 * (current_avg_util / 100)
    target_load_factor  = 0.7 + 0.3 * (target_utilization_pct / 100)
    improvement_ratio   = target_load_factor / current_load_factor

    projected_avg_co2    = current_avg_co2 * improvement_ratio
    saving_per_shipment  = current_avg_co2 - projected_avg_co2
    total_saving         = saving_per_shipment * len(lane)

    return json.dumps({
        "lane":                    f"{origin}→{destination}",
        "current_avg_util_pct":    round(current_avg_util, 1),
        "target_util_pct":         target_utilization_pct,
        "current_avg_co2_kg":      round(current_avg_co2, 2),
        "projected_avg_co2_kg":    round(projected_avg_co2, 2),
        "saving_per_shipment_kg":  round(saving_per_shipment, 2),
        "total_saving_kg":         round(total_saving, 2),
        "shipments_below_target":  int(len(lane)),
        "saving_pct":              round(
            saving_per_shipment / current_avg_co2 * 100, 2),
    }, default=str)


@tool
def rank_reduction_opportunities(top_n: int = 5) -> str:
    """
    Scan the entire fleet and rank the top CO2 reduction
    opportunities by potential impact. Returns actionable
    recommendations sorted by highest saving potential.

    Args:
        top_n: Number of top opportunities to return
    """
    df    = get_df()
    opps  = []

    # Opportunity 1 — Underloaded lanes
    underloaded = df[df["load_utilization_pct"] < 70].groupby(
        ["origin", "destination"]
    ).agg(
        count       = ("co2_kg", "count"),
        total_co2   = ("co2_kg", "sum"),
        avg_util    = ("load_utilization_pct", "mean"),
    ).reset_index()

    for _, row in underloaded.iterrows():
        saving = float(row["total_co2"]) * 0.12
        opps.append({
            "type":            "LOAD_OPTIMIZATION",
            "lane":            f"{row['origin']}→{row['destination']}",
            "action":          f"Improve load utilization from "
                               f"{row['avg_util']:.0f}% to 85%",
            "saving_kg":       round(saving, 2),
            "shipments":       int(row["count"]),
            "priority":        "HIGH" if saving > 10000 else "MEDIUM",
        })

    # Opportunity 2 — Empty return lanes
    empty_return = df[df["return_empty"] == 1].groupby(
        ["origin", "destination"]
    ).agg(
        count     = ("co2_kg", "count"),
        total_co2 = ("co2_kg", "sum"),
    ).reset_index()

    for _, row in empty_return.iterrows():
        saving = float(row["total_co2"]) * 0.25
        opps.append({
            "type":      "BACKHAUL_OPTIMIZATION",
            "lane":      f"{row['origin']}→{row['destination']}",
            "action":    "Find backhaul loads to eliminate empty returns",
            "saving_kg": round(saving, 2),
            "shipments": int(row["count"]),
            "priority":  "HIGH" if saving > 15000 else "MEDIUM",
        })

    # Opportunity 3 — Diesel lanes that could switch to CNG
    diesel_lanes = df[df["fuel_type"] == "diesel"].groupby(
        ["origin", "destination"]
    ).agg(
        count     = ("co2_kg", "count"),
        total_co2 = ("co2_kg", "sum"),
    ).reset_index()

    for _, row in diesel_lanes.iterrows():
        saving = float(row["total_co2"]) * 0.28
        opps.append({
            "type":      "FUEL_SWITCH",
            "lane":      f"{row['origin']}→{row['destination']}",
            "action":    "Switch diesel fleet to CNG",
            "saving_kg": round(saving, 2),
            "shipments": int(row["count"]),
            "priority":  "MEDIUM",
        })

    # Sort and return top N
    opps_df = pd.DataFrame(opps)
    top     = opps_df.nlargest(top_n, "saving_kg")

    total_saving = float(top["saving_kg"].sum())
    fleet_co2    = float(df["co2_kg"].sum())

    return json.dumps({
        "top_opportunities":     top.to_dict(orient="records"),
        "total_potential_saving_kg": round(total_saving, 2),
        "fleet_total_co2_kg":    round(fleet_co2, 2),
        "max_reduction_pct":     round(total_saving / fleet_co2 * 100, 2),
    }, default=str)


# ═══════════════════════════════════════════════════════
# FLEET SUMMARY TOOLS
# ═══════════════════════════════════════════════════════

@tool
def get_fleet_overview(year: int = 2024) -> str:
    """
    Get a complete fleet-wide emission overview for a year.
    Returns KPIs, breakdowns, and performance metrics.

    Args:
        year: Year to summarize (default 2024)
    """
    df = get_df()

    yearly = df[df["shipment_date"].dt.year == year]
    if yearly.empty:
        return json.dumps({
            "status":  "no_data",
            "message": f"No data for {year}"
        })

    total_co2   = float(yearly["co2_kg"].sum())
    total_tkm   = float(
        (yearly["load_weight_tonnes"] * yearly["distance_km"]).sum())

    return json.dumps({
        "year":                   year,
        "total_shipments":        int(len(yearly)),
        "total_co2_kg":           round(total_co2, 2),
        "total_co2_tonnes":       round(total_co2 / 1000, 2),
        "avg_co2_per_shipment":   round(total_co2 / len(yearly), 2),
        "carbon_intensity_g_tkm": round(
            total_co2 * 1000 / total_tkm, 4),
        "total_distance_km":      round(
            float(yearly["distance_km"].sum()), 2),
        "avg_load_util_pct":      round(
            float(yearly["load_utilization_pct"].mean()), 2),
        "empty_return_pct":       round(
            float(yearly["return_empty"].mean()) * 100, 2),
        "anomaly_rate_pct":       round(
            float(yearly["is_anomaly"].mean()) * 100, 2),
        "unique_lanes":           int(
            yearly[["origin","destination"]]
            .drop_duplicates().shape[0]),
        "unique_carriers":        int(yearly["carrier_name"].nunique()),
        "fuel_mix": yearly["fuel_type"].value_counts(
            normalize=True).mul(100).round(2).to_dict(),
        "vehicle_mix": yearly["vehicle_type"].value_counts(
            normalize=True).mul(100).round(2).to_dict(),
    }, default=str)


@tool
def get_carrier_performance_ranking(top_n: int = 8) -> str:
    """
    Rank all carriers by their emission efficiency.
    Returns a leaderboard with green vs poor performers.

    Args:
        top_n: Number of carriers to rank
    """
    df = get_df()

    carrier_perf = df.groupby("carrier_name").agg(
        total_shipments = ("co2_kg",             "count"),
        avg_co2_kg      = ("co2_kg",             "mean"),
        total_co2_kg    = ("co2_kg",             "sum"),
        avg_util_pct    = ("load_utilization_pct","mean"),
        anomaly_rate    = ("is_anomaly",          "mean"),
        avg_vehicle_age = ("vehicle_age_years",   "mean"),
        empty_return_pct= ("return_empty",        "mean"),
    ).reset_index()

    carrier_perf["co2_per_km"] = (
        carrier_perf["avg_co2_kg"] /
        df.groupby("carrier_name")["distance_km"].mean().values
    )

    # Rank: lower avg CO2 = better
    carrier_perf["rank"] = carrier_perf["avg_co2_kg"].rank().astype(int)
    carrier_perf = carrier_perf.sort_values("avg_co2_kg")

    # Label performance
    def perf_label(row):
        if row["avg_co2_kg"] < carrier_perf["avg_co2_kg"].quantile(0.33):
            return "GREEN"
        elif row["avg_co2_kg"] < carrier_perf["avg_co2_kg"].quantile(0.66):
            return "AVERAGE"
        else:
            return "POOR"

    carrier_perf["performance"] = carrier_perf.apply(
        perf_label, axis=1)

    return json.dumps({
        "carrier_ranking": carrier_perf.round(2).to_dict(
            orient="records"),
        "fleet_avg_co2_kg": round(float(df["co2_kg"].mean()), 2),
    }, default=str)


@tool
def get_top_polluting_shipments(top_n: int = 10,
                                 year: int = 2024) -> str:
    """
    Find the single highest-emission shipments in the fleet.
    Useful for targeted intervention.

    Args:
        top_n: Number of shipments to return
        year:  Year to search (default 2024)
    """
    df = get_df()

    yearly = df[df["shipment_date"].dt.year == year]
    if yearly.empty:
        return json.dumps({
            "status":  "no_data",
            "message": f"No data for {year}"
        })

    top = yearly.nlargest(top_n, "co2_kg")[[
        "shipment_id", "shipment_date", "origin",
        "destination", "vehicle_type", "carrier_name",
        "co2_kg", "load_utilization_pct",
        "vehicle_age_years", "is_anomaly"
    ]]

    return json.dumps({
        "year":      year,
        "top_n":     top_n,
        "shipments": top.round(2).to_dict(orient="records"),
    }, default=str)


# ═══════════════════════════════════════════════════════
# ESG REPORT TOOLS
# ═══════════════════════════════════════════════════════

@tool
def calculate_scope3_emissions(year: int = 2024) -> str:
    """
    Calculate GHG Protocol Scope 3 Category 4 emissions
    (upstream transportation) for a given year.

    Args:
        year: Reporting year (default 2024)
    """
    df = get_df()

    yearly = df[df["shipment_date"].dt.year == year]
    if yearly.empty:
        return json.dumps({
            "status":  "no_data",
            "message": f"No data for {year}"
        })

    total_co2_kg     = float(yearly["co2_kg"].sum())
    total_co2_tonnes = total_co2_kg / 1000

    # WTW adjustment (GHG Protocol)
    wtw_factor   = 1.18
    wtw_co2      = total_co2_tonnes * wtw_factor

    # By fuel type
    fuel_breakdown = yearly.groupby("fuel_type").agg(
        co2_kg      = ("co2_kg",     "sum"),
        shipments   = ("co2_kg",     "count"),
        total_tkm   = ("co2_kg",     "count"),
    ).reset_index()
    fuel_breakdown["co2_tonnes"] = (
        fuel_breakdown["co2_kg"] / 1000).round(2)

    # Intensity metrics
    total_tkm = float(
        (yearly["load_weight_tonnes"] * yearly["distance_km"]).sum())
    intensity_g_tkm = (total_co2_kg * 1000 / total_tkm)

    return json.dumps({
        "reporting_year":           year,
        "scope":                    "Scope 3 Category 4",
        "standard":                 "GHG Protocol Corporate Standard",
        "total_co2_ttw_tonnes":     round(total_co2_tonnes, 2),
        "total_co2_wtw_tonnes":     round(wtw_co2, 2),
        "wtw_uplift_factor":        wtw_factor,
        "carbon_intensity_g_tkm":   round(intensity_g_tkm, 4),
        "total_tonne_km":           round(total_tkm, 2),
        "fuel_breakdown":           fuel_breakdown.round(
            2).to_dict(orient="records"),
        "shipment_count":           int(len(yearly)),
    }, default=str)


@tool
def generate_reduction_targets(
        baseline_year: int = 2022,
        target_reduction_pct: float = 30.0) -> str:
    """
    Generate science-based CO2 reduction targets
    aligned with net zero commitments.

    Args:
        baseline_year:         Year to use as baseline (default 2022)
        target_reduction_pct:  % reduction target (default 30%)
    """
    df = get_df()

    baseline = df[df["shipment_date"].dt.year == baseline_year]
    if baseline.empty:
        return json.dumps({
            "status":  "no_data",
            "message": f"No baseline data for {baseline_year}"
        })

    baseline_co2 = float(baseline["co2_kg"].sum()) / 1000

    # Annual reduction needed (linear path to 2030)
    years_to_2030     = 2030 - baseline_year
    target_co2        = baseline_co2 * (1 - target_reduction_pct / 100)
    annual_reduction  = (baseline_co2 - target_co2) / years_to_2030

    # Year by year targets
    yearly_targets = []
    for y in range(baseline_year, 2031):
        yrs_from_base = y - baseline_year
        target        = baseline_co2 - (annual_reduction * yrs_from_base)
        actual_df     = df[df["shipment_date"].dt.year == y]
        actual        = float(actual_df["co2_kg"].sum()) / 1000 \
                        if not actual_df.empty else None
        yearly_targets.append({
            "year":           y,
            "target_tonnes":  round(target, 2),
            "actual_tonnes":  round(actual, 2) if actual else None,
            "on_track":       actual <= target
                              if actual is not None else None,
        })

    return json.dumps({
        "baseline_year":          baseline_year,
        "baseline_co2_tonnes":    round(baseline_co2, 2),
        "target_reduction_pct":   target_reduction_pct,
        "target_2030_tonnes":     round(target_co2, 2),
        "annual_reduction_needed":round(annual_reduction, 2),
        "yearly_targets":         yearly_targets,
        "aligned_with":           "Paris Agreement 1.5°C pathway",
    }, default=str)


@tool
def get_ghg_protocol_breakdown(year: int = 2024) -> str:
    """
    Generate a full GHG Protocol compliant emission
    breakdown by vehicle type, fuel, and route tier.

    Args:
        year: Reporting year (default 2024)
    """
    df = get_df()

    yearly = df[df["shipment_date"].dt.year == year]
    if yearly.empty:
        return json.dumps({"status": "no_data"})

    # By vehicle type
    by_vehicle = yearly.groupby("vehicle_type").agg(
        co2_tonnes  = ("co2_kg", lambda x: round(x.sum()/1000, 2)),
        shipments   = ("co2_kg", "count"),
        share_pct   = ("co2_kg", lambda x:
                        round(x.sum()/yearly["co2_kg"].sum()*100, 2)),
    ).reset_index()

    # By fuel type
    by_fuel = yearly.groupby("fuel_type").agg(
        co2_tonnes = ("co2_kg", lambda x: round(x.sum()/1000, 2)),
        shipments  = ("co2_kg", "count"),
        share_pct  = ("co2_kg", lambda x:
                       round(x.sum()/yearly["co2_kg"].sum()*100, 2)),
    ).reset_index()

    # By lane tier
    by_tier = yearly.groupby("lane_tier").agg(
        co2_tonnes = ("co2_kg", lambda x: round(x.sum()/1000, 2)),
        shipments  = ("co2_kg", "count"),
    ).reset_index()

    return json.dumps({
        "year":           year,
        "by_vehicle_type": by_vehicle.to_dict(orient="records"),
        "by_fuel_type":    by_fuel.to_dict(orient="records"),
        "by_lane_tier":    by_tier.to_dict(orient="records"),
        "total_co2_tonnes": round(
            float(yearly["co2_kg"].sum()) / 1000, 2),
    }, default=str)