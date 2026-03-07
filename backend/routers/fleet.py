# backend/routers/fleet.py
import json
from fastapi import APIRouter
from src.agents.tools import (
    get_fleet_overview,
    get_carrier_performance_ranking,
    get_top_polluting_shipments,
)

router = APIRouter()

@router.get("/overview")
def fleet_overview(year: int = 2024):
    result = get_fleet_overview.invoke({"year": year})
    return json.loads(result)

@router.get("/carriers")
def carrier_ranking(top_n: int = 8):
    result = get_carrier_performance_ranking.invoke({"top_n": top_n})
    return json.loads(result)

@router.get("/top-polluters")
def top_polluters(top_n: int = 10, year: int = 2024):
    result = get_top_polluting_shipments.invoke({
        "top_n": top_n, "year": year
    })
    return json.loads(result)