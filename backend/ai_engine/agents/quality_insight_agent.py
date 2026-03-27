"""
quality_insight_agent.py — Agent 3: Quality Insight Generator

Translates raw quality metrics (null rates, fill rates, distributions)
into plain-English business impact statements. A 1.85% null rate on
product_category_name becomes: "Missing category data affects revenue
attribution for ~1,850 products per 100K records."

Also implements the "impossible date" detector for the Olist dataset —
a signature data quality issue where delivered_date < purchase_date.
"""

import logging
from ai_engine.state import AgentState
from ai_engine.llm.client import LLMClient
from core.database import get_connection

logger = logging.getLogger(__name__)

_llm = LLMClient()

_QUALITY_SYSTEM = """You are a senior data quality analyst. You will receive
quality metrics for a database table and must return a JSON analysis.

Return exactly:
{
  "plain_english_summary": "2-3 sentences describing the overall data quality",
  "severity": "good" | "warning" | "critical",
  "recommended_actions": ["action 1", "action 2", "action 3"],
  "business_impact": "1-2 sentences on what wrong decisions could be made with this data quality"
}

Severity rules:
- "good":     quality_score >= 90
- "warning":  quality_score 70-89 or any column null_rate > 5%
- "critical": quality_score < 70 or any column null_rate > 20% or impossible dates detected

Respond ONLY with valid JSON."""


def quality_insight_node(state: AgentState) -> AgentState:
    """
    LangGraph node function.
    Reads: state["quality_report"], state["connection_id"]
    Writes: state["quality_insights"], state["current_step"]
    """
    logger.info("Agent 3 — Quality Insight: starting")
    quality_report = state.get("quality_report", [])
    insights       = {}

    if not quality_report:
        return {
            **state,
            "quality_insights": {},
            "current_step": "quality_analyzed",
            "errors": state.get("errors", []) + ["Quality Insight Agent: no quality report available"],
        }

    for table_quality in quality_report:
        table_name = table_quality.get("table_name", "unknown")
        logger.debug(f"  Analyzing quality for: {table_name}")

        # ── Impossible date detection ──────────────────────────────────────
        impossible_date_info = _detect_impossible_dates(
            table_quality, state.get("connection_id", "")
        )

        # ── Build the quality prompt ───────────────────────────────────────
        col_quality_lines = []
        for col_q in table_quality.get("columns", []):
            col_quality_lines.append(
                f"  - {col_q.get('column_name')}: "
                f"null_rate={col_q.get('null_rate', 0):.1f}%, "
                f"fill_rate={col_q.get('fill_rate', 100):.1f}%, "
                f"unique_count={col_q.get('unique_count', 'N/A')}"
            )

        anomalies_section = ""
        if impossible_date_info:
            anomalies_section = (
                f"\nANOMALY DETECTED: {impossible_date_info['count']} rows have "
                f"{impossible_date_info['delivered_col']} BEFORE {impossible_date_info['purchase_col']}. "
                f"This is logically impossible and indicates data corruption."
            )

        user_prompt = f"""Table: {table_name}
Overall quality score: {table_quality.get('quality_score', 0)}/100
Total rows: {table_quality.get('row_count', 0):,}

Column quality breakdown:
{chr(10).join(col_quality_lines) if col_quality_lines else '  No column data available'}
{anomalies_section}

Generate the quality insight JSON now."""

        result = _llm.complete_json(_QUALITY_SYSTEM, user_prompt)

        if "error" in result:
            logger.error(f"Quality insight failed for {table_name}: {result['error']}")
            insights[table_name] = {
                "plain_english_summary": f"Quality analysis unavailable for {table_name}.",
                "severity":              "warning",
                "recommended_actions":   [],
                "business_impact":       "Unable to assess business impact.",
                "generation_error":      result["error"],
            }
        else:
            insights[table_name] = {
                **result,
                "table_name":        table_name,
                "quality_score":     table_quality.get("quality_score", 0),
                "impossible_dates":  impossible_date_info,
            }

    logger.info(f"Agent 3 — Quality Insight: analyzed {len(insights)} tables")
    return {
        **state,
        "quality_insights": insights,
        "current_step":     "quality_analyzed",
    }


def _detect_impossible_dates(
    table_quality: dict,
    connection_id: str,
) -> dict | None:
    """
    Check if a table has timestamp columns that violate chronological order.
    Specific to the Olist dataset: order_purchase_timestamp vs
    order_delivered_customer_date.

    Returns a dict with count and column names if anomalies found, else None.
    """
    # Find candidate column pairs in this table
    columns = [c.get("column_name", "") for c in table_quality.get("columns", [])]

    purchase_candidates  = [c for c in columns if "purchase" in c.lower() and "timestamp" in c.lower()]
    delivered_candidates = [c for c in columns if "delivered" in c.lower() and "date" in c.lower()]

    if not purchase_candidates or not delivered_candidates:
        return None

    purchase_col  = purchase_candidates[0]
    delivered_col = delivered_candidates[0]
    table_name    = table_quality.get("table_name", "")

    try:
        engine = get_connection(connection_id)
        if engine is None:
            return None

        with engine.connect() as conn:
            from sqlalchemy import text
            query = text(
                f"SELECT COUNT(*) as cnt FROM {table_name} "
                f"WHERE {delivered_col} < {purchase_col}"
            )
            result = conn.execute(query)
            count  = result.scalar() or 0

        if count > 0:
            logger.warning(
                f"Impossible dates found in {table_name}: "
                f"{count} rows where {delivered_col} < {purchase_col}"
            )
            return {
                "count":        int(count),
                "purchase_col": purchase_col,
                "delivered_col": delivered_col,
                "table_name":   table_name,
            }
    except Exception as exc:
        logger.warning(f"Impossible date check failed for {table_name}: {exc}")

    return None