"""
ai_router.py — Master AI Router

Aggregates all AI sub-routers into a single router that Dev 1 includes
in their main FastAPI app with one line.
"""

from fastapi import APIRouter
from ai_engine.api_routes.dictionary_routes import router as dict_router
from ai_engine.api_routes.query_routes      import router as query_router
from ai_engine.api_routes.search_routes     import router as search_router

# Parent router for all AI endpoints — prefix /ai applied here
ai_router = APIRouter(prefix="/ai", tags=["AI Engine"])

# Mount each sub-router under /ai
ai_router.include_router(dict_router)
ai_router.include_router(query_router)
ai_router.include_router(search_router)