# backend/routers/anomaly.py
import json
from fastapi import APIRouter
from src.agents.tools import (
    scan_fleet_for_anomalies,
    get_shipment_details,
    get_anomaly_root_cause,
    get_carrier_anomaly_history,
)

router = APIRouter()

@router.get("/scan")
def scan_anomalies(month: int = 10, year: int = 2024, top_n: int = 10):
    result = scan_fleet_for_anomalies.invoke({
        "month": month, "year": year, "top_n": top_n
    })
    return json.loads(result)

@router.get("/shipment/{shipment_id}")
def shipment_details(shipment_id: str):
    result = get_shipment_details.invoke({
        "shipment_id": shipment_id
    })
    return json.loads(result)

@router.get("/root-cause/{shipment_id}")
def root_cause(shipment_id: str):
    result = get_anomaly_root_cause.invoke({
        "shipment_id": shipment_id
    })
    return json.loads(result)

@router.get("/carrier/{carrier_name}")
def carrier_history(carrier_name: str):
    result = get_carrier_anomaly_history.invoke({
        "carrier_name": carrier_name
    })
    return json.loads(result)