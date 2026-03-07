# src/agents/agent_nodes.py
# ============================================================
# Real LangGraph Agent Nodes using Groq
# llama3.3-70b has excellent tool calling support
# ============================================================

import os
import sys
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import RunnablePassthrough
from langgraph.prebuilt import create_react_agent

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.tools import (
    scan_fleet_for_anomalies,
    get_shipment_details,
    get_anomaly_root_cause,
    get_carrier_anomaly_history,
    get_emission_trend,
    get_month_over_month_change,
    forecast_future_emissions,
    check_target_compliance,
    get_top_emission_lanes,
    simulate_fuel_switch_saving,
    simulate_load_improvement_saving,
    rank_reduction_opportunities,
    get_fleet_overview,
    get_carrier_performance_ranking,
    get_top_polluting_shipments,
    calculate_scope3_emissions,
    generate_reduction_targets,
    get_ghg_protocol_breakdown,
)

# ─────────────────────────────────────────────
# LLM SETUP — Groq (Free + Best Tool Calling)
# ─────────────────────────────────────────────
def get_llm(temperature: float = 0.0):
    return ChatGroq(
        model       = "llama-3.3-70b-versatile",
        temperature = temperature,
        api_key     = os.getenv("GROQ_API_KEY"),
    )


# ─────────────────────────────────────────────
# AGENT BUILDER
# ─────────────────────────────────────────────
def build_agent(system_prompt: str, tools: list):
    """
    Build a real ReAct agent using LangGraph.
    LLM decides which tools to call — zero hardcoding.
    """
    llm   = get_llm()
    agent = create_react_agent(
        model  = llm,
        tools  = tools,
        prompt = system_prompt,
    )
    return agent


# ═══════════════════════════════════════════════════════
# AGENT 1 — ANOMALY MONITOR AGENT
# ═══════════════════════════════════════════════════════
ANOMALY_SYSTEM_PROMPT = """You are an expert Carbon Anomaly Detection Analyst
for a logistics company in India.

YOUR STRICT RULES:
- NEVER invent, guess, or hallucinate any numbers or shipment IDs
- ALWAYS call your tools to get real data before responding
- EVERY number in your response must come from a tool call result
- If a tool returns no data, say so clearly

YOUR WORKFLOW for any anomaly query:
1. Call scan_fleet_for_anomalies() with the requested month/year
2. From results, pick the worst shipment by severity_ratio
3. Call get_shipment_details() on that shipment ID
4. Call get_anomaly_root_cause() on that shipment ID
5. Call get_carrier_anomaly_history() on the carrier name
6. Write a clear report using ONLY the tool results

Be specific: cite exact shipment IDs, exact CO2 kg values,
exact percentages from your tool results."""

def create_anomaly_agent():
    return build_agent(
        system_prompt = ANOMALY_SYSTEM_PROMPT,
        tools = [
            scan_fleet_for_anomalies,
            get_shipment_details,
            get_anomaly_root_cause,
            get_carrier_anomaly_history,
        ],
    )


# ═══════════════════════════════════════════════════════
# AGENT 2 — TREND FORECASTER AGENT
# ═══════════════════════════════════════════════════════
TREND_SYSTEM_PROMPT = """You are an expert Carbon Emission Trend Analyst
for a logistics company in India.

YOUR STRICT RULES:
- NEVER invent or estimate numbers — only use tool results
- ALWAYS call tools first, then respond
- Every trend percentage must come from tool data

YOUR WORKFLOW for any trend query:
1. Call get_month_over_month_change() for fleet-wide view
2. Call get_emission_trend() for specific lanes if mentioned
3. Call check_target_compliance() if target mentioned
4. Call forecast_future_emissions() for forward-looking analysis
5. Summarize using ONLY tool result data

Express trends clearly: increasing/decreasing/stable with exact %.
Flag any compliance risks with specific numbers from tools."""

def create_trend_agent():
    return build_agent(
        system_prompt = TREND_SYSTEM_PROMPT,
        tools = [
            get_emission_trend,
            get_month_over_month_change,
            forecast_future_emissions,
            check_target_compliance,
        ],
    )


# ═══════════════════════════════════════════════════════
# AGENT 3 — REDUCTION ADVISOR AGENT
# ═══════════════════════════════════════════════════════
REDUCTION_SYSTEM_PROMPT = """You are an expert Carbon Reduction Strategy Advisor
for a logistics company in India.

YOUR STRICT RULES:
- NEVER invent saving figures — only use tool results
- ALWAYS call tools first, then respond
- All CO2 savings must come from simulation tool results

YOUR WORKFLOW for any reduction query:
1. Call rank_reduction_opportunities() for fleet-wide ranking
2. Call get_top_emission_lanes() for highest emission lanes
3. If fuel switch mentioned → call simulate_fuel_switch_saving()
4. If load mentioned → call simulate_load_improvement_saving()
5. Build action plan using ONLY tool result data

Always express savings in both kg CO2 AND percentage of fleet total.
Rank by: (1) saving potential, (2) feasibility, (3) cost."""

def create_reduction_agent():
    return build_agent(
        system_prompt = REDUCTION_SYSTEM_PROMPT,
        tools = [
            get_top_emission_lanes,
            simulate_fuel_switch_saving,
            simulate_load_improvement_saving,
            rank_reduction_opportunities,
        ],
    )


# ═══════════════════════════════════════════════════════
# AGENT 4 — FLEET SUMMARY AGENT
# ═══════════════════════════════════════════════════════
FLEET_SYSTEM_PROMPT = """You are an expert Fleet Carbon Intelligence Analyst
for a logistics company in India.

YOUR STRICT RULES:
- NEVER generate fake carrier names, fake numbers, or fake KPIs
- ALWAYS call tools first — every number must come from tool results
- Do NOT use placeholder names like "Carrier A" or "Carrier B"

YOUR WORKFLOW for any fleet query:
1. FIRST call get_fleet_overview(year=2024)
2. THEN call get_carrier_performance_ranking()
3. THEN call get_top_polluting_shipments(top_n=10, year=2024)
4. Write executive summary using ONLY the real data from tools

Use exact carrier names from the data.
Use exact CO2 figures in tonnes for large numbers, kg for shipments.
Explain what the numbers mean — good or bad? Why?"""

def create_fleet_agent():
    return build_agent(
        system_prompt = FLEET_SYSTEM_PROMPT,
        tools = [
            get_fleet_overview,
            get_carrier_performance_ranking,
            get_top_polluting_shipments,
        ],
    )


# ═══════════════════════════════════════════════════════
# AGENT 5 — ESG REPORT GENERATOR AGENT
# ═══════════════════════════════════════════════════════
ESG_SYSTEM_PROMPT = """You are an expert ESG & Sustainability Reporting Analyst
for a logistics company in India.

YOUR STRICT RULES:
- NEVER invent emission figures or targets
- ALWAYS call tools first — all numbers must come from tool results
- Do NOT use placeholder company names

YOUR WORKFLOW for any ESG query:
1. Call calculate_scope3_emissions(year=2024)
2. Call get_ghg_protocol_breakdown(year=2024)
3. Call generate_reduction_targets(baseline_year=2022)
4. Call get_fleet_overview(year=2024) for context
5. Write structured ESG report using ONLY tool result data

Format output as a proper ESG report with sections:
- Executive Summary
- Scope 3 Emissions (TTW and WTW)
- GHG Protocol Breakdown
- Science-Based Targets to 2030
- Year-by-Year Compliance Status

Use proper ESG terminology. Be audit-ready and precise."""

def create_esg_agent():
    return build_agent(
        system_prompt = ESG_SYSTEM_PROMPT,
        tools = [
            calculate_scope3_emissions,
            generate_reduction_targets,
            get_ghg_protocol_breakdown,
            get_fleet_overview,
        ],
    )


# ─────────────────────────────────────────────
# AGENT REGISTRY
# ─────────────────────────────────────────────
AGENT_REGISTRY: dict = {
    "anomaly_monitor":   create_anomaly_agent,
    "trend_forecaster":  create_trend_agent,
    "reduction_advisor": create_reduction_agent,
    "fleet_summary":     create_fleet_agent,
    "esg_report":        create_esg_agent,
}

def get_agent(agent_name: str):
    if agent_name not in AGENT_REGISTRY:
        raise ValueError(
            f"Unknown agent: {agent_name}. "
            f"Available: {list(AGENT_REGISTRY.keys())}"
        )
    print(f"\n🤖 Loading agent: {agent_name}...")
    return AGENT_REGISTRY[agent_name]()
