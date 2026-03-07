# backend/main.py
# ============================================================
# FastAPI Backend — Wraps all agents + tools as REST API
# ============================================================

import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.routers import fleet, anomaly, trends, reduction, esg, chat

app = FastAPI(
    title       = "LORRI Carbon Intelligence API",
    description = "Carbon tracking agent API for road freight",
    version     = "1.0.0",
)

# Allow React frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["http://localhost:5173"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# Register all routers
app.include_router(fleet,     prefix="/api/fleet",     tags=["Fleet"])
app.include_router(anomaly,   prefix="/api/anomaly",   tags=["Anomaly"])
app.include_router(trends,    prefix="/api/trends",    tags=["Trends"])
app.include_router(reduction, prefix="/api/reduction", tags=["Reduction"])
app.include_router(esg,       prefix="/api/esg",       tags=["ESG"])
app.include_router(chat,      prefix="/api/chat",      tags=["Chat"])

@app.get("/")
def root():
    return {"status": "LORRI Carbon Intelligence API is running"}