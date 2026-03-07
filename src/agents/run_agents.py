# src/agents/run_agents.py
# ============================================================
# Entry point — Run any agent query through the graph
# ============================================================

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import HumanMessage
from agents.graph import build_graph

def run_query(query: str) -> str:
    """Run any query through the multi-agent graph."""

    print("\n" + "="*60)
    print(f"  🌿 CARBON INTELLIGENCE AGENT")
    print(f"  Query: {query}")
    print("="*60)

    graph  = build_graph()
    result = graph.invoke({
        "query":          query,
        "messages":       [HumanMessage(content=query)],
        "next_agent":     "",
        "agent_response": "",
        "iterations":     0,
    })

    print("\n" + "="*60)
    print("  📊 FINAL RESPONSE")
    print("="*60)
    print(result["agent_response"])
    return result["agent_response"]


if __name__ == "__main__":

    # Test 1 — Fleet Summary
    run_query("Give me a complete fleet emission overview for 2024")

    # Test 2 — Anomaly Detection
    run_query(
        "Find all anomalous shipments in October 2024 "
        "and explain the root cause of the worst one"
    )

    # Test 3 — Reduction
    run_query(
        "What are the top CO2 reduction opportunities "
        "in our fleet? Simulate switching Mumbai to Delhi to CNG"
    )

    # Test 4 — Trend
    run_query(
        "Are our emissions increasing or decreasing? "
        "Are we on track to meet a 30% reduction target?"
    )

    # Test 5 — ESG
    run_query(
        "Generate our Scope 3 ESG report for 2024 "
        "with science-based reduction targets to 2030"
    )