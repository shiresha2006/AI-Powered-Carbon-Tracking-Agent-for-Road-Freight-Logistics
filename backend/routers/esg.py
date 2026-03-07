# backend/routers/esg.py
import json
from fastapi import APIRouter
from src.agents.tools import (
    calculate_scope3_emissions,
    generate_reduction_targets,
    get_ghg_protocol_breakdown,
)

router = APIRouter()

@router.get("/scope3")
def scope3(year: int = 2024):
    result = calculate_scope3_emissions.invoke({"year": year})
    return json.loads(result)

@router.get("/breakdown")
def breakdown(year: int = 2024):
    result = get_ghg_protocol_breakdown.invoke({"year": year})
    return json.loads(result)

@router.get("/targets")
def targets(baseline_year: int = 2022, target_reduction_pct: float = 30.0):
    result = generate_reduction_targets.invoke({
        "baseline_year":        baseline_year,
        "target_reduction_pct": target_reduction_pct,
    })
    return json.loads(result)