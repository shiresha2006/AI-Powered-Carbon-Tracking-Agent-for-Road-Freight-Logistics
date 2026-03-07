import json
import math
from fastapi import APIRouter
from src.agents.tools import (
    get_emission_trend,
    get_month_over_month_change,
    forecast_future_emissions,
    check_target_compliance,
)

router = APIRouter()

def clean_nan(obj):
    """Recursively replace NaN/Inf with None for JSON safety."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
    if isinstance(obj, dict):
        return {k: clean_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_nan(i) for i in obj]
    return obj

@router.get("/monthly")
def monthly_trend(year: int = 2024):
    result = get_month_over_month_change.invoke({"year": year})
    data   = json.loads(result)
    return clean_nan(data)

@router.get("/lane")
def lane_trend(origin: str, destination: str, period_days: int = 90):
    result = get_emission_trend.invoke({
        "origin": origin,
        "destination": destination,
        "period_days": period_days,
    })
    data = json.loads(result)
    return clean_nan(data)

@router.get("/forecast")
def forecast(origin: str, destination: str, days_ahead: int = 30):
    result = forecast_future_emissions.invoke({
        "origin":      origin,
        "destination": destination,
        "days_ahead":  days_ahead,
    })
    data = json.loads(result)
    return clean_nan(data)

@router.get("/compliance")
def compliance(target_annual_co2_tonnes: float = 9334.69, year: int = 2024):
    result = check_target_compliance.invoke({
        "target_annual_co2_tonnes": target_annual_co2_tonnes,
        "year": year,
    })
    data = json.loads(result)
    return clean_nan(data)