# backend/routers/reduction.py
import json
from fastapi import APIRouter
from src.agents.tools import (
    get_top_emission_lanes,
    simulate_fuel_switch_saving,
    simulate_load_improvement_saving,
    rank_reduction_opportunities,
)

router = APIRouter()

@router.get("/opportunities")
def opportunities(top_n: int = 5):
    result = rank_reduction_opportunities.invoke({"top_n": top_n})
    return json.loads(result)

@router.get("/top-lanes")
def top_lanes(top_n: int = 10):
    result = get_top_emission_lanes.invoke({"top_n": top_n})
    return json.loads(result)

@router.get("/fuel-switch")
def fuel_switch(
    origin: str,
    destination: str,
    from_fuel: str = "diesel",
    to_fuel: str = "cng"
):
    result = simulate_fuel_switch_saving.invoke({
        "origin":      origin,
        "destination": destination,
        "from_fuel":   from_fuel,
        "to_fuel":     to_fuel,
    })
    return json.loads(result)

@router.get("/load-improvement")
def load_improvement(
    origin: str,
    destination: str,
    target_utilization_pct: float = 85.0
):
    result = simulate_load_improvement_saving.invoke({
        "origin":                 origin,
        "destination":            destination,
        "target_utilization_pct": target_utilization_pct,
    })
    return json.loads(result)