# ============================================================
# backend/api/router.py
# ============================================================
# Central router registry. The ONLY place where route modules are
# imported and attached to the top-level API router.
#
# main.py mounts this router at prefix "/api/v1":
#   /api/v1/health
#   /api/v1/connect
#   /api/v1/connections
#   /api/v1/schema/{connection_id}
#   /api/v1/quality/{connection_id}
# ============================================================

from fastapi import APIRouter
from api.routes import health, connections, schema, quality

api_router = APIRouter()

# Health probe — no sub-prefix
api_router.include_router(health.router)

# Connection management — no sub-prefix
# POST   /api/v1/connect
# GET    /api/v1/connections
# DELETE /api/v1/connections/{connection_id}
api_router.include_router(connections.router)

# Schema extraction
# GET /api/v1/schema/{connection_id}
# GET /api/v1/schema/{connection_id}/graph
# GET /api/v1/schema/{connection_id}/table/{table_name}
api_router.include_router(schema.router)

# Quality analysis + PII
# GET /api/v1/quality/{connection_id}
# GET /api/v1/quality/{connection_id}/table/{table_name}
# GET /api/v1/quality/{connection_id}/pii
api_router.include_router(quality.router)