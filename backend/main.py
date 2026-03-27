from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from config.settings import settings
from api.router import api_router

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME}")
    # Auto-connect to DATABASE_URL if set in .env
    if settings.DATABASE_URL:
        try:
            from core.database import register_connection
            conn_id = register_connection(settings.DATABASE_URL)
            app.state.default_connection_id = conn_id
            logger.info(f"Auto-connected to database. connection_id={conn_id}")
        except Exception as e:
            logger.warning(f"Auto-connect failed: {e}")
            app.state.default_connection_id = None
    else:
        app.state.default_connection_id = None
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Data Dictionary Agent API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def root():
    return {"status": "ok", "service": "Data Dictionary Agent"}


@app.get("/api/v1/default-connection")
def get_default_connection():
    conn_id = getattr(app.state, "default_connection_id", None)
    return {"connection_id": conn_id}