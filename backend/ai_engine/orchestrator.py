"""
orchestrator.py — LangGraph State Machine

The master controller. Defines the agent graph topology:

    START
      │
      ▼
  [profile]  ← always runs first (fast, no LLM)
      │
      ├── has nl_question? ──► [query] ──► END  (fast path)
      │
      ▼
  [document] ──► [quality_insight] ──► END  (full analysis path)

LangGraph compiles this graph into an executable runnable with
built-in state passing, error handling, and optional checkpointing.
"""

import logging
from typing import Literal

from langgraph.graph import StateGraph, START, END

from ai_engine.state import AgentState
from ai_engine.agents.schema_profiler    import schema_profiler_node
from ai_engine.agents.documentation_agent import documentation_node
from ai_engine.agents.quality_insight_agent import quality_insight_node
from ai_engine.agents.query_agent        import query_node

from core.schema_extractor import extract_full_schema
from core.quality_analyzer import analyze_all_tables
from core.database         import get_connection

logger = logging.getLogger(__name__)

# ── Build the graph ────────────────────────────────────────────────────────

def _route_after_profile(
    state: AgentState,
) -> Literal["query", "document"]:
    """
    Conditional edge function.
    LangGraph calls this after the "profile" node to decide the next node.
    Returns the string name of the next node to execute.
    """
    if state.get("nl_question", "").strip():
        # Fast path: user asked a question — skip documentation
        logger.debug("Orchestrator: routing to query (fast path)")
        return "query"
    # Full path: no question — run full documentation + quality analysis
    logger.debug("Orchestrator: routing to document (full analysis)")
    return "document"


def _build_graph() -> StateGraph:
    """Construct and compile the LangGraph state machine."""
    workflow = StateGraph(AgentState)

    # Register nodes — each is a Python function (state) -> state
    workflow.add_node("profile",        schema_profiler_node)
    workflow.add_node("document",       documentation_node)
    workflow.add_node("quality_insight", quality_insight_node)
    workflow.add_node("query",          query_node)

    # START always goes to profile first
    workflow.add_edge(START, "profile")

    # After profiling: conditional branch
    workflow.add_conditional_edges(
        "profile",
        _route_after_profile,
        {
            "query":    "query",    # fast path
            "document": "document", # full analysis path
        },
    )

    # Full analysis path: document → quality_insight → END
    workflow.add_edge("document",        "quality_insight")
    workflow.add_edge("quality_insight", END)

    # Fast path: query → END directly
    workflow.add_edge("query", END)

    return workflow.compile()


# Compile once at module import — graph is reusable across requests
_graph = _build_graph()
logger.info("LangGraph orchestrator compiled successfully")


# ── Public API ────────────────────────────────────────────────────────────

def run_full_analysis(connection_id: str) -> AgentState:
    """
    Execute the full agent pipeline for a connected database.
    Runs: profile → document → quality_insight

    This is the expensive path (multiple LLM calls) — trigger once per
    database connection, cache the result.
    """
    logger.info(f"Orchestrator: run_full_analysis for connection {connection_id}")

    engine = get_connection(connection_id)
    if engine is None:
        return AgentState(
            connection_id=connection_id,
            raw_schema={},
            quality_report=[],
            profiled_schema={},
            documentation={},
            quality_insights={},
            nl_question="",
            generated_sql="",
            sql_explanation="",
            search_query="",
            search_results=[],
            errors=[f"Connection {connection_id} not found"],
            current_step="error",
        )

    # Load raw data from Dev 1's modules
    raw_schema     = extract_full_schema(engine)
    quality_report = analyze_all_tables(engine)

    initial_state: AgentState = {
        "connection_id":   connection_id,
        "raw_schema":      raw_schema,
        "quality_report":  quality_report,
        "profiled_schema": {},
        "documentation":   {},
        "quality_insights": {},
        "nl_question":     "",   # empty = full analysis path
        "generated_sql":   "",
        "sql_explanation": "",
        "search_query":    "",
        "search_results":  [],
        "errors":          [],
        "current_step":    "initializing",
    }

    final_state = _graph.invoke(initial_state)
    logger.info(f"Orchestrator: full analysis complete for {connection_id}")
    return final_state


def run_query(connection_id: str, question: str) -> AgentState:
    """
    Execute the fast-path pipeline for a single NL-to-SQL query.
    Runs: profile → query

    Requires that the schema has already been loaded (either from cache
    or by running run_full_analysis first).
    """
    logger.info(f"Orchestrator: run_query for '{question}'")

    engine = get_connection(connection_id)
    if engine is None:
        return AgentState(
            connection_id=connection_id,
            raw_schema={},
            quality_report=[],
            profiled_schema={},
            documentation={},
            quality_insights={},
            nl_question=question,
            generated_sql="",
            sql_explanation="Connection not found.",
            search_query="",
            search_results=[],
            errors=[f"Connection {connection_id} not found"],
            current_step="error",
        )

    raw_schema = extract_full_schema(engine)

    initial_state: AgentState = {
        "connection_id":    connection_id,
        "raw_schema":       raw_schema,
        "quality_report":   [],          # not needed for query fast path
        "profiled_schema":  {},
        "documentation":    {},
        "quality_insights": {},
        "nl_question":      question,    # ← this triggers the fast path
        "generated_sql":    "",
        "sql_explanation":  "",
        "search_query":     "",
        "search_results":   [],
        "errors":           [],
        "current_step":     "initializing",
    }

    final_state = _graph.invoke(initial_state)
    logger.info(f"Orchestrator: query complete, SQL generated")
    return final_state