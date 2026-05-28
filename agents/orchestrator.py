"""
agents/orchestrator.py
LangGraph state machine orchestrating the full 4-agent pipeline.
State flows: ingestion → insight → career → report
Each node is a LangGraph node wrapping the corresponding agent.
"""

from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END

from agents import ingestion_agent, insight_agent, career_agent, report_agent


# ── State schema ─────────────────────────────────────────────────────────────

class StudentState(TypedDict):
    raw_student_data: dict
    ingestion_result: Optional[dict]
    insight_result: Optional[dict]
    career_result: Optional[dict]
    report_result: Optional[dict]
    current_agent: str
    errors: list[str]


# ── Node functions ────────────────────────────────────────────────────────────

def node_ingestion(state: StudentState) -> StudentState:
    state["current_agent"] = "ingestion"
    try:
        result = ingestion_agent.run(state["raw_student_data"])
        state["ingestion_result"] = result
        if not result.get("valid", True):
            state["errors"].append(f"Ingestion validation failed: {result.get('flags', [])}")
    except Exception as e:
        state["errors"].append(f"Ingestion agent error: {e}")
        state["ingestion_result"] = {"valid": False, "normalized_data": state["raw_student_data"], "flags": [str(e)]}
    return state


def node_insight(state: StudentState) -> StudentState:
    state["current_agent"] = "insight"
    try:
        result = insight_agent.run(state["ingestion_result"])
        state["insight_result"] = result
    except Exception as e:
        state["errors"].append(f"Insight agent error: {e}")
        state["insight_result"] = {"_valid": False, "key_observation": str(e)}
    return state


def node_career(state: StudentState) -> StudentState:
    state["current_agent"] = "career"
    try:
        result = career_agent.run(state["ingestion_result"], state["insight_result"])
        state["career_result"] = result
    except Exception as e:
        state["errors"].append(f"Career agent error: {e}")
        state["career_result"] = {"_valid": False, "career_recommendations": []}
    return state


def node_report(state: StudentState) -> StudentState:
    state["current_agent"] = "report"
    try:
        result = report_agent.run(
            state["ingestion_result"],
            state["insight_result"],
            state["career_result"],
        )
        state["report_result"] = result
    except Exception as e:
        state["errors"].append(f"Report agent error: {e}")
        state["report_result"] = {"_valid": False, "executive_summary": str(e)}
    return state


def should_continue_to_insight(state: StudentState) -> str:
    """Only proceed if ingestion succeeded."""
    if state["ingestion_result"] and state["ingestion_result"].get("valid", True):
        return "insight"
    return END


# ── Graph construction ────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(StudentState)

    graph.add_node("ingestion", node_ingestion)
    graph.add_node("insight", node_insight)
    graph.add_node("career", node_career)
    graph.add_node("report", node_report)

    graph.set_entry_point("ingestion")

    graph.add_conditional_edges(
        "ingestion",
        should_continue_to_insight,
        {"insight": "insight", END: END},
    )
    graph.add_edge("insight", "career")
    graph.add_edge("career", "report")
    graph.add_edge("report", END)

    return graph.compile()


# Singleton compiled graph
_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def run_pipeline(student_data: dict) -> StudentState:
    """
    Run the full 4-agent pipeline for a single student.
    Returns the final state with all agent results.
    """
    initial_state: StudentState = {
        "raw_student_data": student_data,
        "ingestion_result": None,
        "insight_result": None,
        "career_result": None,
        "report_result": None,
        "current_agent": "starting",
        "errors": [],
    }

    graph = get_graph()
    final_state = graph.invoke(initial_state)
    return final_state
