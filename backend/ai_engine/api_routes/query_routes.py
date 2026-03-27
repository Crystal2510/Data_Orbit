"""
query_routes.py — NL-to-SQL Query Endpoint

POST /ai/query — accepts a natural language question, returns SQL + explanation
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ai_engine.orchestrator import run_query

logger = logging.getLogger(__name__)
router = APIRouter()


class QueryRequest(BaseModel):
    connection_id: str
    question: str


@router.post("/query")
async def nl_to_sql(request: QueryRequest) -> dict:
    """
    Convert a natural language question to SQL using the LangGraph query agent.
    Uses RAG retrieval to ground the SQL in actual schema context.
    """
    logger.info(f"POST /ai/query — question='{request.question}'")

    if not request.question.strip():
        raise HTTPException(status_code=400, detail="question cannot be empty")

    try:
        final_state = run_query(request.connection_id, request.question)

        # Extract query result from state
        query_result = final_state.get("_query_result", {})

        if final_state.get("errors"):
            # Return errors but still give a 200 with error details
            logger.warning(f"Query completed with errors: {final_state['errors']}")

        return {
            "connection_id": request.connection_id,
            "question":      request.question,
            "sql":           query_result.get("sql", final_state.get("generated_sql", "")),
            "explanation":   query_result.get("explanation", final_state.get("sql_explanation", "")),
            "tables_used":   query_result.get("tables_used", []),
            "confidence":    query_result.get("confidence", 0.0),
            "errors":        final_state.get("errors", []),
        }

    except Exception as exc:
        logger.error(f"NL-to-SQL failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))