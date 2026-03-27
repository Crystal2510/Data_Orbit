"""
search_routes.py — Semantic Schema Search Endpoints

POST /ai/search — semantic search over embedded schema
POST /ai/embed  — trigger schema embedding into ChromaDB
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ai_engine.rag.retriever import SchemaRetriever
from ai_engine.rag.embedder  import SchemaEmbedder
from core.schema_extractor   import extract_full_schema
from core.database           import get_connection

logger = logging.getLogger(__name__)
router  = APIRouter()

_retriever = SchemaRetriever()
_embedder  = SchemaEmbedder()


class SearchRequest(BaseModel):
    connection_id: str
    query: str
    top_k: int = 5


class EmbedRequest(BaseModel):
    connection_id: str


@router.post("/search")
async def semantic_search(request: SearchRequest) -> dict:
    """
    Semantic search over the embedded schema.
    Returns most relevant tables and columns for the query string.
    """
    logger.info(f"POST /ai/search — query='{request.query}'")

    if not request.query.strip():
        raise HTTPException(status_code=400, detail="query cannot be empty")

    try:
        tables  = _retriever.search_tables(
            query=request.query,
            connection_id=request.connection_id,
            top_k=request.top_k,
        )
        columns = _retriever.search_columns(
            query=request.query,
            connection_id=request.connection_id,
            top_k=request.top_k * 2,  # return more column results
        )

        return {
            "connection_id":  request.connection_id,
            "query":          request.query,
            "tables":         tables,
            "columns":        columns,
            "total_results":  len(tables) + len(columns),
        }

    except Exception as exc:
        logger.error(f"Semantic search failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/embed")
async def embed_schema(request: EmbedRequest) -> dict:
    """
    Trigger schema extraction and embedding into ChromaDB.
    Call this after connecting to a new database before using /ai/search.
    """
    logger.info(f"POST /ai/embed — connection_id={request.connection_id}")

    engine = get_connection(request.connection_id)
    if engine is None:
        raise HTTPException(
            status_code=404,
            detail=f"Connection {request.connection_id} not found. POST /connections first."
        )

    try:
        schema = extract_full_schema(engine)

        # Clear any previous embeddings for this connection before re-embedding
        _embedder.clear_schema(request.connection_id)
        _embedder.embed_schema(schema, request.connection_id)

        table_count  = len(schema.get("tables", []))
        column_count = sum(len(t.get("columns", [])) for t in schema.get("tables", []))

        return {
            "connection_id":  request.connection_id,
            "status":         "embedded",
            "tables_embedded": table_count,
            "columns_embedded": column_count,
        }

    except Exception as exc:
        logger.error(f"Schema embedding failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))