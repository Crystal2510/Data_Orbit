# ============================================================
# backend/core/database.py
# ============================================================
# Database connection management layer.
# 
# FUNCTIONS:
#   create_engine_from_url(url)    → Engine  (builds dialect-aware engine)
#   test_connection(engine)        → bool    (SELECT 1 probe)
#   register_connection(url)       → str     (stores engine, returns UUID)
#   get_connection(id)             → Engine  (retrieves stored engine)
#   list_connections()             → list    (all active UUIDs)
#   remove_connection(id)          → bool    (dispose + delete)
#
# WHY IN-MEMORY DICT?
#   Zero-infrastructure for hackathon scope. In production, use Redis or
#   a database table to survive process restarts.
# ============================================================

import uuid
import logging
from typing import Dict

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

# Module-level registry: connection_id (UUID str) → SQLAlchemy Engine
_engine_registry: Dict[str, Engine] = {}

# Schema cache: connection_id → extracted schema dict (avoids re-extracting on every request)
_schema_cache: Dict[str, dict] = {}


def create_engine_from_url(connection_string: str) -> Engine:
    """
    Build a SQLAlchemy Engine with dialect-appropriate settings.

    Supports:
      - SQLite   : sqlite:///./file.db  or  sqlite:///:memory:
      - PostgreSQL: postgresql+psycopg2://user:pass@host:5432/db
      - MySQL    : mysql+pymysql://user:pass@host:3306/db
      - Any other SQLAlchemy-supported dialect (falls back to generic settings)

    Connection pooling strategy:
      - SQLite    : No pool (file/in-memory access is not network-bound)
      - Server DBs: pool_pre_ping=True prevents stale connections;
                    pool_recycle=3600 avoids MySQL's 8-hour timeout

    Args:
        connection_string: A valid SQLAlchemy database URL string.

    Returns:
        Configured SQLAlchemy Engine instance.

    Raises:
        ValueError: If the connection string is empty.
    """
    if not connection_string or not connection_string.strip():
        raise ValueError("Connection string cannot be empty.")

    url_lower = connection_string.lower()

    if url_lower.startswith("sqlite"):
        # SQLite is file-based — disable connection pooling.
        # check_same_thread=False required for FastAPI's multithreaded context.
        engine = create_engine(
            connection_string,
            connect_args={"check_same_thread": False},
            echo=False,
        )
        logger.info(f"SQLite engine created → {connection_string}")

    elif url_lower.startswith("postgresql") or url_lower.startswith("postgres"):
        engine = create_engine(
            connection_string,
            pool_pre_ping=True,   # Validate connection health before checkout
            pool_recycle=3600,    # Recycle connections after 1 hour
            pool_size=5,          # 5 persistent connections in pool
            max_overflow=10,      # 10 additional burst connections
            echo=False,
        )
        logger.info("PostgreSQL engine created.")

    elif url_lower.startswith("mysql"):
        engine = create_engine(
            connection_string,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=5,
            max_overflow=10,
            echo=False,
        )
        logger.info("MySQL engine created.")

    else:
        # Generic fallback — handles Oracle, MSSQL, Snowflake, etc.
        logger.warning("Unrecognised dialect — attempting generic engine creation.")
        engine = create_engine(
            connection_string,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
        )

    return engine


def test_connection(engine: Engine) -> bool:
    """
    Validate that the engine can actually open a database connection.

    SQLAlchemy is LAZY — create_engine() never connects until you run a query.
    This function forces that first connection to catch bad credentials,
    unreachable hosts, or wrong database names immediately.

    Args:
        engine: A SQLAlchemy Engine to test.

    Returns:
        True if SELECT 1 succeeds, False otherwise.
    """
    try:
        with engine.connect() as conn:
            # text() is mandatory in SQLAlchemy 2.0 for raw SQL strings
            conn.execute(text("SELECT 1"))
        logger.info("Connection test passed ✓")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Connection test FAILED: {e}")
        return False


def register_connection(connection_string: str) -> str:
    """
    Create an engine, validate it, and store it under a new UUID.

    This is the primary entry point called by POST /api/v1/connect.

    Args:
        connection_string: Valid SQLAlchemy URL string from the user.

    Returns:
        UUID string (connection_id) — pass this in all subsequent API calls.

    Raises:
        ValueError: If the connection string is empty or malformed.
        ConnectionError: If the database cannot be reached.
    """
    engine = create_engine_from_url(connection_string)

    # Fail fast — don't store an engine we can't use
    if not test_connection(engine):
        engine.dispose()
        raise ConnectionError(
            "Cannot connect to database. "
            "Verify the connection string and that the database server is running."
        )

    connection_id = str(uuid.uuid4())
    _engine_registry[connection_id] = engine
    logger.info(f"Connection registered → ID: {connection_id}")
    return connection_id


def get_connection(connection_id: str) -> Engine:
    """
    Retrieve a previously registered engine by its UUID.

    Args:
        connection_id: The UUID string returned by register_connection().

    Returns:
        The corresponding SQLAlchemy Engine.

    Raises:
        KeyError: If no engine is registered under this ID.
    """
    engine = _engine_registry.get(connection_id)
    if engine is None:
        raise KeyError(
            f"No active connection found for ID '{connection_id}'. "
            f"Please POST /api/v1/connect first."
        )
    return engine


def list_connections() -> list[str]:
    """Return all active connection IDs currently in the registry."""
    return list(_engine_registry.keys())


def remove_connection(connection_id: str) -> bool:
    """
    Dispose and remove a connection from the registry.

    dispose() closes all pooled connections and releases file handles.
    This is critical for SQLite which holds a file lock while open.

    Args:
        connection_id: UUID of the connection to remove.

    Returns:
        True if removed successfully, False if ID was not found.
    """
    engine = _engine_registry.pop(connection_id, None)
    _schema_cache.pop(connection_id, None)  # evict cached schema too
    if engine is not None:
        engine.dispose()
        logger.info(f"Connection {connection_id} disposed and removed.")
        return True
    logger.warning(f"Tried to remove unknown connection: {connection_id}")
    return False


# ── Schema cache helpers ───────────────────────────────────────────────────

def get_cached_schema(connection_id: str) -> dict | None:
    """Return the cached schema for a connection, or None if not cached."""
    return _schema_cache.get(connection_id)


def set_cached_schema(connection_id: str, schema: dict) -> None:
    """Store the extracted schema dict in memory for fast future access."""
    _schema_cache[connection_id] = schema
    logger.info(f"Schema cached for connection {connection_id}")


def invalidate_schema_cache(connection_id: str) -> None:
    """Force the next schema request to re-extract from the database."""
    _schema_cache.pop(connection_id, None)
    logger.info(f"Schema cache invalidated for connection {connection_id}")