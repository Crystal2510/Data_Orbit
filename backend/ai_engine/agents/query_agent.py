"""
query_agent.py — Agent 4: NL-to-SQL Query Intelligence

Three-step pipeline:
  1. RAG retrieval — find the most relevant tables/columns for the question
  2. SQL generation — LLM generates SQL grounded in retrieved schema context
  3. Validation — check that all table names in the SQL actually exist

This grounding step (step 1) is the key architectural difference between
a hallucinating text-to-SQL system and a reliable one.
"""

import logging
from ai_engine.state import AgentState
from ai_engine.llm.client import LLMClient
from ai_engine.rag.retriever import SchemaRetriever

logger = logging.getLogger(__name__)

_llm       = LLMClient()
_retriever = SchemaRetriever()

_SQL_SYSTEM = """You are an expert SQL analyst. You generate precise, optimized SQL queries.

CRITICAL RULES:
1. ONLY use table and column names that appear in the schema context provided
2. NEVER invent or hallucinate table/column names
3. Always use table aliases for readability
4. For aggregations, always include GROUP BY
5. Prefer explicit JOINs over subqueries when possible

Respond ONLY with this JSON structure:
{
  "sql": "SELECT ... FROM ... WHERE ...",
  "explanation": "Plain English explanation of what the query does and why each JOIN is needed",
  "tables_used": ["table1", "table2"],
  "confidence": 0.95
}

confidence rules:
- 1.0: all tables and columns are clearly present in context
- 0.7-0.9: most context found, minor assumptions made
- 0.4-0.6: partial context, some guessing required
- 0.0-0.3: insufficient context, SQL may be incorrect"""


def query_node(state: AgentState) -> AgentState:
    """
    LangGraph node function — fast path for NL-to-SQL.
    Reads: state["nl_question"], state["connection_id"], state["profiled_schema"]
    Writes: state["generated_sql"], state["sql_explanation"], state["current_step"]
    """
    logger.info("Agent 4 — Query: starting NL-to-SQL")
    question      = state.get("nl_question", "").strip()
    connection_id = state.get("connection_id", "")

    if not question:
        return {
            **state,
            "generated_sql":   "",
            "sql_explanation": "No question provided.",
            "current_step":    "query_complete",
            "errors": state.get("errors", []) + ["Query Agent: nl_question is empty"],
        }

    # ── STEP 1: RAG retrieval ──────────────────────────────────────────────
    logger.debug(f"  RAG retrieval for: {question}")
    rag_context = _retriever.get_context_for_question(question, connection_id)
    logger.debug(f"  Retrieved context length: {len(rag_context)} chars")

    # ── STEP 2: SQL generation ─────────────────────────────────────────────
    # Build a concise schema summary from profiled_schema for supplemental context
    profiled_schema  = state.get("profiled_schema", {})
    schema_summary   = _build_schema_summary(profiled_schema)

    user_prompt = f"""Question: {question}

{rag_context}

Full Schema Summary (all tables):
{schema_summary}

Generate the SQL query now."""

    logger.debug("  Calling LLM for SQL generation")
    result = _llm.complete_json(_SQL_SYSTEM, user_prompt)

    if "error" in result:
        logger.error(f"SQL generation failed: {result['error']}")
        return {
            **state,
            "generated_sql":   "",
            "sql_explanation": f"SQL generation failed: {result['error']}",
            "current_step":    "query_complete",
            "errors": state.get("errors", []) + [f"Query Agent: {result['error']}"],
        }

    # ── STEP 3: Validation ─────────────────────────────────────────────────
    generated_sql  = result.get("sql", "")
    tables_used    = result.get("tables_used", [])
    confidence     = result.get("confidence", 0.0)
    explanation    = result.get("explanation", "")

    # Validate that claimed tables actually exist in the schema
    known_tables        = set(profiled_schema.keys())
    unknown_tables      = [t for t in tables_used if t not in known_tables]

    if unknown_tables:
        logger.warning(f"  Validation failed: unknown tables {unknown_tables}")
        confidence  = 0.0
        explanation = (
            f"⚠️ Validation failed: the query references tables that do not exist "
            f"in the schema: {unknown_tables}. "
            f"Original explanation: {explanation}"
        )

    logger.info(
        f"Agent 4 — Query: generated SQL (confidence={confidence}, "
        f"tables={tables_used})"
    )

    return {
        **state,
        "generated_sql":   generated_sql,
        "sql_explanation": explanation,
        "current_step":    "query_complete",
        # Store full result for API response
        "_query_result": {
            "sql":          generated_sql,
            "explanation":  explanation,
            "tables_used":  tables_used,
            "confidence":   confidence,
        },
    }


def _build_schema_summary(profiled_schema: dict) -> str:
    """
    Build a compact schema summary for the LLM's supplemental context.
    Format: "table_name (type): col1, col2, col3 | PKs: pk1 | FKs: fk1"
    """
    lines = []
    for name, info in profiled_schema.items():
        cols = [c["name"] for c in info.get("columns", [])]
        lines.append(
            f"  {name} ({info.get('table_type', '?')}, {info.get('row_count', 0):,} rows): "
            f"{', '.join(cols[:8])}{'...' if len(cols) > 8 else ''}"
        )
    return "\n".join(lines) if lines else "No schema available."