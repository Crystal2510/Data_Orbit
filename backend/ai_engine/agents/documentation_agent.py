"""
documentation_agent.py — Agent 2: AI Documentation Generator

Calls the LLM for each table to generate human-readable business documentation.
This is the core "AI value add" — turning raw schema metadata into the kind of
documentation a data analyst would write after weeks of exploration.

Prompt engineering notes:
 - Temperature 0.3 (slightly creative but consistent)
 - System prompt explicitly forbids markdown in the JSON values
 - We pass table_type from the profiler so the LLM generates contextually
   appropriate documentation (fact vs dimension tables have different purposes)
 - Errors are caught per-table so one failing LLM call doesn't kill the batch
"""

import logging
from ai_engine.state import AgentState
from ai_engine.llm.client import LLMClient

logger = logging.getLogger(__name__)

_llm = LLMClient()

_DOCUMENTATION_SYSTEM = """You are a senior data analyst and data documentation expert.
Your job is to generate clear, business-friendly documentation for database tables.

You will be given metadata about a database table and must return a JSON object
with exactly these keys:
{
  "business_summary": "2-3 sentences describing what this table stores and its business purpose",
  "purpose": "1 sentence — why this table exists in the system",
  "key_questions": ["question 1", "question 2", "question 3", "question 4"],
  "recommended_joins": ["table_name_1", "table_name_2"]
}

Rules:
- Use plain business language (avoid SQL jargon)
- key_questions must be questions a business analyst would actually ask
- recommended_joins must be real table names from the schema provided
- No markdown formatting inside JSON string values
- Respond ONLY with the JSON object, nothing else"""


def documentation_node(state: AgentState) -> AgentState:
    """
    LangGraph node function.
    Reads: state["profiled_schema"]
    Writes: state["documentation"], state["current_step"]
    """
    logger.info("Agent 2 — Documentation: starting")
    profiled_schema = state.get("profiled_schema", {})
    documentation   = {}

    if not profiled_schema:
        logger.warning("Documentation Agent: profiled_schema is empty, skipping")
        return {
            **state,
            "documentation": {},
            "current_step":  "documented",
            "errors": state.get("errors", []) + ["Documentation Agent: no profiled schema"],
        }

    all_table_names = list(profiled_schema.keys())

    for table_name, table_info in profiled_schema.items():
        logger.debug(f"  Documenting table: {table_name}")

        col_descriptions = []
        for col in table_info.get("columns", []):
            flags = []
            if col.get("primary_key"):
                flags.append("PK")
            if col.get("foreign_keys"):
                refs = [f"{fk['ref_table']}.{fk['ref_column']}" for fk in col["foreign_keys"]]
                flags.append(f"FK→{', '.join(refs)}")
            flag_str = f" [{', '.join(flags)}]" if flags else ""
            col_descriptions.append(f"{col['name']} ({col.get('type', 'unknown')}){flag_str}")

        user_prompt = f"""Table name: {table_name}
Row count: {table_info['row_count']:,}
Table type classification: {table_info['table_type']}
Quality score: {table_info['quality_score']}/100
Primary key columns: {', '.join(table_info['pk_columns']) or 'none'}
Foreign key columns: {', '.join(table_info['fk_columns']) or 'none'}

Columns:
{chr(10).join(f'  - {c}' for c in col_descriptions)}

Other tables in the schema (for recommended_joins context):
{', '.join(t for t in all_table_names if t != table_name)}

Generate the documentation JSON object now."""

        result = _llm.complete_json(_DOCUMENTATION_SYSTEM, user_prompt)

        if "error" in result:
            
            logger.error(f"Documentation failed for {table_name}: {result['error']}")
            documentation[table_name] = {
                "business_summary":  f"Documentation unavailable for {table_name}.",
                "purpose":           "Could not generate documentation.",
                "key_questions":     [],
                "recommended_joins": [],
                "generation_error":  result["error"],
            }
        else:

            documentation[table_name] = {
                **result,
                "table_name":   table_name,
                "table_type":   table_info["table_type"],
                "row_count":    table_info["row_count"],
                "quality_score": table_info["quality_score"],
            }

    logger.info(f"Agent 2 — Documentation: documented {len(documentation)} tables")
    return {
        **state,
        "documentation": documentation,
        "current_step":  "documented",
    }