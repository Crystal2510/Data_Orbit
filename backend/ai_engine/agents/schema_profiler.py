"""
schema_profiler.py — Agent 1: Schema Profiler Node

This is the FIRST node in every LangGraph pipeline run. It is intentionally
free of LLM calls — it is pure, fast Python logic that enriches the raw
schema with structural intelligence before passing it to the LLM agents.

Why separate profiling from documentation?
 - Speed: running 9-table profiling takes <50ms vs. 9 LLM calls
 - Cost: zero API tokens spent on computable facts
 - Quality: gives documentation_node a richer context (table type, FK count)
   leading to better AI summaries

Table classification heuristics (industry-standard patterns):
 - "fact"      : many FKs (≥3), high row count — e.g. orders, order_items
 - "dimension" : few FKs (≤1), moderate columns — e.g. customers, products
 - "bridge"    : exactly 2 FKs, few other columns — e.g. order_items (M:M resolver)
 - "lookup"    : very few columns (≤3), likely PK only — e.g. category translations
"""

import logging
from ai_engine.state import AgentState

logger = logging.getLogger(__name__)


def schema_profiler_node(state: AgentState) -> AgentState:
    """
    LangGraph node function.
    Reads: state["raw_schema"]
    Writes: state["profiled_schema"], state["current_step"]
    """
    logger.info("Agent 1 — Schema Profiler: starting")
    raw_schema = state.get("raw_schema", {})
    tables     = raw_schema.get("tables", [])

    if not tables:
        logger.warning("Schema Profiler: raw_schema is empty")
        return {
            **state,
            "profiled_schema": {},
            "current_step": "profiled",
            "errors": state.get("errors", []) + ["Schema Profiler: no tables found in schema"],
        }

    table_names = {t["name"] for t in tables}

    profiled: dict = {}

    for table in tables:
        name    = table["name"]
        columns = table.get("columns", [])

        pk_columns    = [c for c in columns if c.get("primary_key")]
        fk_columns    = [c for c in columns if c.get("foreign_keys")]
        nullable_cols = [c for c in columns if c.get("nullable", True)]
        row_count     = table.get("row_count", 0)

        incoming_fk_count = 0
        for other_table in tables:
            if other_table["name"] == name:
                continue
            for col in other_table.get("columns", []):
                for fk in col.get("foreign_keys", []):
                    if fk.get("ref_table") == name:
                        incoming_fk_count += 1

        outgoing_fk_count = len(fk_columns)
        total_fk_count    = incoming_fk_count + outgoing_fk_count

        table_type = _classify_table(
            total_columns=len(columns),
            pk_count=len(pk_columns),
            outgoing_fk_count=outgoing_fk_count,
            incoming_fk_count=incoming_fk_count,
            row_count=row_count,
        )

        quality_score = _get_quality_score(state.get("quality_report", []), name)

        profiled[name] = {
            "name":                    name,
            "row_count":               row_count,
            "total_columns":           len(columns),
            "pk_columns":              [c["name"] for c in pk_columns],
            "fk_columns":              [c["name"] for c in fk_columns],
            "nullable_columns":        [c["name"] for c in nullable_cols],
            "outgoing_fk_count":       outgoing_fk_count,
            "incoming_fk_count":       incoming_fk_count,
            "estimated_relationships": total_fk_count,
            "table_type":              table_type,
            "quality_score":           quality_score,

            "columns":                 columns,
        }

        logger.debug(f"  Profiled {name}: type={table_type}, FKs={total_fk_count}")

    logger.info(f"Agent 1 — Schema Profiler: profiled {len(profiled)} tables")

    return {
        **state,
        "profiled_schema": profiled,
        "current_step":    "profiled",
    }


def _classify_table(
    total_columns: int,
    pk_count: int,
    outgoing_fk_count: int,
    incoming_fk_count: int,
    row_count: int,
) -> str:
    """
    Heuristic table type classifier.
    Returns: "fact" | "dimension" | "bridge" | "lookup"
    """

    if outgoing_fk_count == 2 and total_columns <= 6:
        return "bridge"

    if total_columns <= 3 and outgoing_fk_count == 0:
        return "lookup"

    if outgoing_fk_count >= 3 or incoming_fk_count >= 3:
        return "fact"


    return "dimension"


def _get_quality_score(quality_report: list, table_name: str) -> float:
    """Extract quality_score for a specific table from the quality report list."""
    for entry in quality_report:
        if entry.get("table_name") == table_name:
            return entry.get("quality_score", 0.0)
    return 0.0