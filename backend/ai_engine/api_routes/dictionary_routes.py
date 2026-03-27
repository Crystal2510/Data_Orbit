"""
dictionary_routes.py — AI Data Dictionary Endpoints

POST /ai/generate-dictionary  — triggers full LangGraph analysis pipeline
GET  /ai/dictionary/{id}      — returns cached documentation
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ai_engine.orchestrator import run_full_analysis
from ai_engine.rag.embedder import SchemaEmbedder

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory cache: connection_id → final AgentState
# In production, replace with Redis
_analysis_cache: dict = {}

_embedder = SchemaEmbedder()


class GenerateDictionaryRequest(BaseModel):
    connection_id: str


@router.post("/generate-dictionary")
async def generate_dictionary(request: GenerateDictionaryRequest) -> dict:
    """
    Run the full LangGraph agent pipeline and return AI-generated documentation.
    This is the most expensive endpoint — it makes multiple LLM calls.
    Expected duration: 20-60 seconds depending on table count and LLM provider.
    """
    connection_id = request.connection_id
    logger.info(f"POST /ai/generate-dictionary — connection_id={connection_id}")

    try:
        # Run full analysis pipeline
        final_state = run_full_analysis(connection_id)

        # Cache result for subsequent GET calls
        _analysis_cache[connection_id] = final_state

        # Also embed the schema into ChromaDB for search endpoints
        if final_state.get("raw_schema"):
            logger.info("Embedding schema into ChromaDB after analysis")
            _embedder.embed_schema(final_state["raw_schema"], connection_id)

        return {
            "connection_id":     connection_id,
            "documentation":     final_state.get("documentation", {}),
            "quality_insights":  final_state.get("quality_insights", {}),
            "profiled_schema":   {
                k: {
                    "table_type":              v.get("table_type"),
                    "row_count":               v.get("row_count"),
                    "total_columns":           v.get("total_columns"),
                    "estimated_relationships": v.get("estimated_relationships"),
                    "quality_score":           v.get("quality_score"),
                }
                for k, v in final_state.get("profiled_schema", {}).items()
            },
            "errors":            final_state.get("errors", []),
            "status":            "complete",
        }

    except Exception as exc:
        logger.error(f"Dictionary generation failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/dictionary/{connection_id}")
async def get_dictionary(connection_id: str) -> dict:
    """Return cached documentation if available. Returns 404 if not yet generated."""
    if connection_id not in _analysis_cache:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No analysis found for connection {connection_id}. "
                "Run POST /ai/generate-dictionary first."
            ),
        )

    state = _analysis_cache[connection_id]
    return {
        "connection_id":    connection_id,
        "documentation":    state.get("documentation", {}),
        "quality_insights": state.get("quality_insights", {}),
        "status":           "cached",
    }