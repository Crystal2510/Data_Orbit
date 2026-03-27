# ============================================================
# backend/api/routes/connections.py
# ============================================================
# ENDPOINTS:
#   POST   /connect                      — Register a new DB connection
#   GET    /connections                  — List all active connection IDs
#   DELETE /connections/{connection_id}  — Remove a connection
# ============================================================

import logging
from fastapi import APIRouter, HTTPException, status
from models.schemas import ConnectionRequest, ConnectionResponse, ConnectionListResponse
from core.database import register_connection, list_connections, remove_connection, get_connection

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/connect",
    response_model=ConnectionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["connections"],
    summary="Register a database connection",
    description=(
        "Accepts a SQLAlchemy connection string, validates it with a SELECT 1 test, "
        "and returns a connection_id UUID. Pass this ID in all subsequent API calls."
    ),
)
async def connect_to_database(request: ConnectionRequest) -> ConnectionResponse:
    """
    Register a new database connection.

    Raises:
        400: Connection string is malformed or empty.
        503: Database is unreachable (wrong host, port, credentials).
        500: Unexpected internal error.
    """
    try:
        connection_id = register_connection(request.connection_string)
        engine = get_connection(connection_id)
        dialect = engine.dialect.name
        logger.info(f"New connection: {connection_id} ({dialect})")
        return ConnectionResponse(
            connection_id=connection_id,
            dialect=dialect,
            message=f"Successfully connected to {dialect} database.",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {str(e)}",
        )


@router.get(
    "/connections",
    response_model=ConnectionListResponse,
    tags=["connections"],
    summary="List all active database connections",
)
async def list_active_connections() -> ConnectionListResponse:
    """Return all currently registered connection IDs."""
    ids = list_connections()
    return ConnectionListResponse(active_connections=ids, count=len(ids))


@router.delete(
    "/connections/{connection_id}",
    tags=["connections"],
    summary="Remove a database connection",
)
async def delete_connection(connection_id: str) -> dict:
    """
    Dispose the SQLAlchemy engine and remove the connection from the registry.

    Raises:
        404: Connection ID not found.
    """
    removed = remove_connection(connection_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active connection with ID '{connection_id}'.",
        )
    return {
        "message": f"Connection '{connection_id}' closed and removed.",
        "connection_id": connection_id,
    }