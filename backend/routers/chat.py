# backend/routers/chat.py
import os
import sys
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.graph import build_graph

router  = APIRouter()

class ChatRequest(BaseModel):
    query: str

@router.post("/")
def ask_lorri(request: ChatRequest):
    graph  = build_graph()
    result = graph.invoke({
        "query":          request.query,
        "messages":       [HumanMessage(content=request.query)],
        "next_agent":     "",
        "agent_response": "",
        "iterations":     0,
    })
    return {
        "query":      request.query,
        "agent_used": result["next_agent"],
        "response":   result["agent_response"],
    }