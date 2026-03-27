"""
state.py — LangGraph AgentState definition

This is the SINGLE shared state object that flows through every node
in the LangGraph pipeline. Think of it as the "baton" passed between
agents. Every agent reads from it and writes its output back into it.

LangGraph requires state to be a TypedDict so it can:
 1. Validate the shape at runtime
 2. Support partial updates (each node only updates the keys it owns)
 3. Enable checkpointing / persistence for long-running pipelines
"""

from typing import TypedDict, Optional


class AgentState(TypedDict):
    """
    Shared state for the Data Dictionary Agent pipeline.

    Lifecycle of each field:
    - connection_id       : set at pipeline entry, never mutated
    - raw_schema          : set at pipeline entry from Dev 1's schema_extractor
    - quality_report      : set at pipeline entry from Dev 1's quality_analyzer
    - profiled_schema     : written by schema_profiler_node (Agent 1)
    - documentation       : written by documentation_node (Agent 2)
    - quality_insights    : written by quality_insight_node (Agent 3)
    - nl_question         : set at pipeline entry for query fast-path
    - generated_sql       : written by query_node (Agent 4)
    - sql_explanation     : written by query_node (Agent 4)
    - search_query        : set externally for direct RAG calls
    - search_results      : written by retriever calls
    - errors              : appended to by any agent that catches an exception
    - current_step        : breadcrumb updated by each agent for observability
    """

    # ── Pipeline entry inputs ──────────────────────────────────────────────
    connection_id: str          # UUID identifying the active DB connection
    raw_schema: dict            # Full output of extract_full_schema()
    quality_report: list        # Full output of analyze_all_tables()

    # ── Agent 1 output (schema_profiler_node) ─────────────────────────────
    profiled_schema: dict       # Enriched schema with table classifications

    # ── Agent 2 output (documentation_node) ──────────────────────────────
    documentation: dict         # keyed by table_name → AI-generated docs

    # ── Agent 3 output (quality_insight_node) ────────────────────────────
    quality_insights: dict      # keyed by table_name → AI quality analysis

    # ── Agent 4 inputs/outputs (query_node — fast path) ───────────────────
    nl_question: str            # natural language question from the user
    generated_sql: str          # final SQL string
    sql_explanation: str        # plain English explanation of the SQL

    # ── RAG / search fields ────────────────────────────────────────────────
    search_query: str           # query string for semantic schema search
    search_results: list        # returned by retriever

    # ── Observability ─────────────────────────────────────────────────────
    errors: list                # list of error strings from any agent
    current_step: str           # human-readable breadcrumb, e.g. "profiled"