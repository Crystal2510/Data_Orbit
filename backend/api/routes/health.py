# ============================================================
# backend/api/routes/health.py
# ============================================================
from datetime import datetime
from fastapi import APIRouter
from models.schemas import HealthResponse
from core.database import list_connections

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["health"],
    summary="Server health check",
    description="Returns server status, version, UTC timestamp, and active DB connection count.",
)
async def health_check() -> HealthResponse:
    """
    Health probe endpoint.
    Used by load balancers, CI pipelines, and teammates confirming the API is up.
    """
    return HealthResponse(
        status="ok",
        service="Data Dictionary Agent",
        version="1.0.0",
        timestamp=datetime.utcnow(),
        active_connections=len(list_connections()),
    )