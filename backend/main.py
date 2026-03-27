from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import our secure settings and router
from config.settings import settings
from api.router import api_router

# Setup logging using the safe setting variables
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info(f"  {settings.APP_NAME} — API Server Starting")
    logger.info(f"  Debug mode : {settings.DEBUG}")
    logger.info(f"  Log level  : {settings.LOG_LEVEL}")
    
    # Example of securely checking if an API key exists without printing it
    if settings.OPENAI_API_KEY:
        logger.info("  OpenAI Key : LOADED SECURELY")
    else:
        logger.warning("  OpenAI Key : MISSING!")

    logger.info("=" * 60)
    yield
    logger.info("Data Dictionary Agent API shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description=(
        "Production-grade REST API for automated relational database analysis. "
        "Provides schema extraction, data quality metrics, PII risk detection, "
        "and relationship mapping for any SQL database."
    ),
    openapi_tags=[
        {"name": "health",      "description": "Server health probe"},
        {"name": "connections", "description": "Register and manage DB connections"},
        {"name": "schema",      "description": "Extract and inspect database schema"},
        {"name": "quality",     "description": "Data quality analysis and PII detection"},
    ],
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include your API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["health"], summary="Root probe")
async def root() -> dict:
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
    }