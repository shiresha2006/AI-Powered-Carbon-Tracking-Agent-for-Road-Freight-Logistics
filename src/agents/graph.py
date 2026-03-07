# src/agents/graph.py
# ============================================================
# LangGraph Supervisor — Routes to correct specialist agent
# ============================================================

import os
import sys
from typing import TypedDict, Annotated, Sequence
import operator
from dotenv import load_dotenv

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.agent_nodes import (
    create_anomaly_agent,
    create_trend_agent,
    create_reduction_agent,
    create_fleet_agent,
    create_esg_agent,
)

# ─────────────────────────────────────────────
# GRAPH STATE
# ─────────────────────────────────────────────
class AgentState(TypedDict):
    messages:       Annotated[Sequence[BaseMessage], operator.add]
    query:          str
    next_agent:     str
    agent_response: str
    iterations:     int


# ─────────────────────────────────────────────
# SUPERVISOR NODE
# ─────────────────────────────────────────────
SUPERVISOR_PROMPT = """You are the supervisor of a Carbon Intelligence Platform.
You have 5 specialist agents:

1. anomaly_monitor   — anomalous shipments, root causes, carrier reliability
2. trend_forecaster  — emission trends over time, forecasts, target compliance
3. reduction_advisor — CO2 reduction opportunities, fuel switch, load improvement
4. fleet_summary     — fleet KPIs, carrier rankings, top polluters, fuel mix
5. esg_report        — GHG Protocol Scope 3, science-based targets, ESG disclosure

Respond with ONLY the agent name. Nothing else.

Examples:
"fleet overview" → fleet_summary
"anomalies in October" → anomaly_monitor
"reduce CO2" → reduction_advisor
"emissions trending" → trend_forecaster
"ESG report" → esg_report
"carrier performance" → fleet_summary
"root cause of shipment" → anomaly_monitor
"switch to CNG" → reduction_advisor
"on track for targets" → trend_forecaster
"scope 3 emissions" → esg_report"""

def supervisor_node(state: AgentState) -> AgentState:
    llm = ChatGroq(
        model       = "llama-3.3-70b-versatile",
        temperature = 0,
        api_key     = os.getenv("GROQ_API_KEY"),
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", SUPERVISOR_PROMPT),
        ("human",  "Query: {query}\nAgent name only:")
    ])

    chain    = prompt | llm
    response = chain.invoke({"query": state["query"]})

    response_text = response.content.strip().lower()
    valid_agents  = [
        "anomaly_monitor", "trend_forecaster",
        "reduction_advisor", "fleet_summary", "esg_report"
    ]

    next_agent = "fleet_summary"
    for agent in valid_agents:
        if agent in response_text:
            next_agent = agent
            break

    print(f"\n🎯 Supervisor → Routing to: {next_agent}")

    return {
        **state,
        "next_agent": next_agent,
        "messages":   list(state["messages"]) + [
            AIMessage(content=f"Routing to {next_agent}")
        ]
    }


# ─────────────────────────────────────────────
# AGENT EXECUTION NODES
# ─────────────────────────────────────────────
def _run_agent(state: AgentState, agent_fn) -> AgentState:
    """Generic agent runner — same pattern for all agents."""
    agent  = agent_fn()
    result = agent.invoke({
        "messages": [HumanMessage(content=state["query"])]
    })
    # Extract final text response from last message
    response = result["messages"][-1].content
    return {
        **state,
        "agent_response": response,
        "messages": list(state["messages"]) + [
            AIMessage(content=response)
        ]
    }

def run_anomaly_agent(state: AgentState) -> AgentState:
    return _run_agent(state, create_anomaly_agent)

def run_trend_agent(state: AgentState) -> AgentState:
    return _run_agent(state, create_trend_agent)

def run_reduction_agent(state: AgentState) -> AgentState:
    return _run_agent(state, create_reduction_agent)

def run_fleet_agent(state: AgentState) -> AgentState:
    return _run_agent(state, create_fleet_agent)

def run_esg_agent(state: AgentState) -> AgentState:
    return _run_agent(state, create_esg_agent)


# ─────────────────────────────────────────────
# ROUTING FUNCTION
# ─────────────────────────────────────────────
def route_to_agent(state: AgentState) -> str:
    return state["next_agent"]


# ─────────────────────────────────────────────
# BUILD GRAPH
# ─────────────────────────────────────────────
def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("supervisor",        supervisor_node)
    graph.add_node("anomaly_monitor",   run_anomaly_agent)
    graph.add_node("trend_forecaster",  run_trend_agent)
    graph.add_node("reduction_advisor", run_reduction_agent)
    graph.add_node("fleet_summary",     run_fleet_agent)
    graph.add_node("esg_report",        run_esg_agent)

    graph.set_entry_point("supervisor")

    graph.add_conditional_edges(
        "supervisor",
        route_to_agent,
        {
            "anomaly_monitor":   "anomaly_monitor",
            "trend_forecaster":  "trend_forecaster",
            "reduction_advisor": "reduction_advisor",
            "fleet_summary":     "fleet_summary",
            "esg_report":        "esg_report",
        }
    )

    graph.add_edge("anomaly_monitor",   END)
    graph.add_edge("trend_forecaster",  END)
    graph.add_edge("reduction_advisor", END)
    graph.add_edge("fleet_summary",     END)
    graph.add_edge("esg_report",        END)

    return graph.compile()