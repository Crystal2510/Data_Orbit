# ============================================================
# backend/core/schema_extractor.py
# ============================================================
# Database schema introspection using SQLAlchemy's reflection API.
#
# KEY DESIGN DECISION — SQLAlchemy inspect():
#   inspect(engine) returns an Inspector that provides dialect-agnostic
#   access to: table names, column metadata (name, type, nullable, default),
#   primary key columns, foreign key constraints, indexes, unique constraints.
#   Works identically for SQLite, PostgreSQL, MySQL, MSSQL, Oracle.
#
# INTEGRATION NOTE FOR DEV 2 (AI Engine):
#   from core.schema_extractor import extract_full_schema, build_relationship_map
#   The schema dict is the "knowledge graph" you feed into ChromaDB / the LLM.
#
# INTEGRATION NOTE FOR DEV 3 (Frontend):
#   GET /api/v1/schema/{connection_id}        → FullSchemaResponse
#   GET /api/v1/schema/{connection_id}/graph  → SchemaGraphResponse (React Flow)
# ============================================================

import logging
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


def _get_row_count(engine: Engine, table_name: str) -> int:
    """
    Execute COUNT(*) on a table and return the integer row count.

    Uses double-quoted table names to handle reserved words and mixed case.
    Falls back to -1 on any error (permissions, views, etc.).

    Args:
        engine: Active SQLAlchemy Engine.
        table_name: Name of the table to count.

    Returns:
        Integer row count, or -1 if the query fails.
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
            return result.scalar() or 0
    except SQLAlchemyError:
        logger.warning(f"COUNT(*) failed for table '{table_name}'. Returning -1.")
        return -1


def extract_full_schema(engine: Engine, skip_row_counts: bool = False) -> dict[str, Any]:
    """
    Introspect the connected database and return a complete schema dictionary.

    Args:
        engine: Active, tested SQLAlchemy Engine.
        skip_row_counts: If True, skip COUNT(*) per table (much faster for remote DBs).
                         Row counts will be set to -1. Use for ER diagrams / query paths.

    Returns:
        dict with "dialect" and "tables" keys.

    Raises:
        RuntimeError: If schema inspection fails.
    """
    try:
        inspector = inspect(engine)
        dialect_name = engine.dialect.name
        table_names = inspector.get_table_names()

        logger.info(
            f"Inspecting schema — dialect: {dialect_name}, "
            f"tables found: {len(table_names)}"
        )

        tables_data = []

        for table_name in table_names:
            # ── Columns ───────────────────────────────────────────────────────
            raw_columns = inspector.get_columns(table_name)

            # get_pk_constraint returns {"constrained_columns": [...], "name": ...}
            pk_constraint = inspector.get_pk_constraint(table_name)
            pk_columns: list[str] = pk_constraint.get("constrained_columns", [])

            # Build FK lookup: local_col_name → list of {ref_table, ref_column}
            # A column can have multiple FKs (composite FK, rare but valid)
            raw_fks = inspector.get_foreign_keys(table_name)
            fk_lookup: dict[str, list[dict]] = {}
            for fk in raw_fks:
                for local_col, ref_col in zip(
                    fk.get("constrained_columns", []),
                    fk.get("referred_columns", [])
                ):
                    fk_lookup.setdefault(local_col, []).append({
                        "ref_table": fk.get("referred_table", ""),
                        "ref_column": ref_col,
                    })

            # Build the column metadata list
            columns_data = []
            for col in raw_columns:
                col_name = col["name"]
                columns_data.append({
                    "name": col_name,
                    # str() converts SQLAlchemy type objects to human-readable strings
                    # e.g. VARCHAR(255), INTEGER, TIMESTAMP WITHOUT TIME ZONE
                    "type": str(col.get("type", "UNKNOWN")),
                    "nullable": col.get("nullable", True),
                    "default": str(col["default"]) if col.get("default") is not None else None,
                    "primary_key": col_name in pk_columns,
                    "foreign_keys": fk_lookup.get(col_name, []),
                })

            # ── Indexes ───────────────────────────────────────────────────────
            raw_indexes = inspector.get_indexes(table_name)
            indexes_data = [
                {
                    "name": idx.get("name", ""),
                    "columns": idx.get("column_names", []),
                    "unique": idx.get("unique", False),
                }
                for idx in raw_indexes
            ]

            # ── Unique Constraints ────────────────────────────────────────────
            # Distinct from unique indexes — these are declarative SQL constraints.
            # Some older SQLite versions don't support this call, hence try/except.
            try:
                raw_unique = inspector.get_unique_constraints(table_name)
                unique_constraints_data = [
                    {
                        "name": uc.get("name", ""),
                        "columns": uc.get("column_names", []),
                    }
                    for uc in raw_unique
                ]
            except NotImplementedError:
                unique_constraints_data = []

            # ── Row Count ─────────────────────────────────────────────────────
            row_count = -1 if skip_row_counts else _get_row_count(engine, table_name)

            tables_data.append({
                "name": table_name,
                "row_count": row_count,
                "columns": columns_data,
                "indexes": indexes_data,
                "unique_constraints": unique_constraints_data,
            })

        schema = {"dialect": dialect_name, "tables": tables_data}
        logger.info(f"Schema extraction complete: {len(tables_data)} tables processed.")
        return schema

    except SQLAlchemyError as e:
        logger.error(f"Schema extraction failed: {e}")
        raise RuntimeError(f"Failed to extract schema: {str(e)}") from e


def build_relationship_map(schema: dict[str, Any]) -> list[dict[str, str]]:
    """
    Derive a flat list of FK relationships from the extracted schema dict.

    Used to generate the EDGE LIST for React Flow (ER diagram).
    Dev 3 (Frontend) calls GET /schema/{id}/graph which wraps these edges.

    Args:
        schema: Dict returned by extract_full_schema().

    Returns:
        List of relationship dicts:
        [
            {
                "from_table": "orders",
                "from_col": "customer_id",
                "to_table": "customers",
                "to_col": "customer_id",
                "edge_id": "orders.customer_id->customers.customer_id"
            },
            ...
        ]
    """
    relationships = []

    for table in schema.get("tables", []):
        from_table = table["name"]
        for col in table.get("columns", []):
            for fk in col.get("foreign_keys", []):
                from_col = col["name"]
                to_table = fk["ref_table"]
                to_col = fk["ref_column"]
                relationships.append({
                    "from_table": from_table,
                    "from_col": from_col,
                    "to_table": to_table,
                    "to_col": to_col,
                    # Unique edge_id used as React Flow's `id` prop
                    "edge_id": f"{from_table}.{from_col}->{to_table}.{to_col}",
                })

    logger.info(f"Relationship map: {len(relationships)} FK edges found.")
    return relationships


def get_single_table_schema(engine: Engine, table_name: str) -> dict[str, Any]:
    """
    Extract schema for a single named table.

    Faster than extract_full_schema() when you only need one table.

    Args:
        engine: Active SQLAlchemy Engine.
        table_name: Exact name of the table to inspect.

    Returns:
        Single table dict in the same format as extract_full_schema()["tables"][i].

    Raises:
        ValueError: If the table does not exist in the database.
        RuntimeError: On SQLAlchemy inspection failure.
    """
    inspector = inspect(engine)
    available_tables = inspector.get_table_names()

    if table_name not in available_tables:
        raise ValueError(
            f"Table '{table_name}' not found. "
            f"Available tables: {available_tables}"
        )

    # Extract only this table (skip all others, skip row counts for speed)
    full_schema = extract_full_schema(engine, skip_row_counts=False)
    for table in full_schema["tables"]:
        if table["name"] == table_name:
            return table

    raise RuntimeError(
        f"Unexpected error: '{table_name}' was present during inspection "
        f"but disappeared during extraction."
    )