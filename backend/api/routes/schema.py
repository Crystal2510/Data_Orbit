# ============================================================
# backend/api/routes/schema.py
# ============================================================
# ENDPOINTS:
#   GET /schema/{connection_id}                    — Full schema
#   GET /schema/{connection_id}/graph              — React Flow nodes + edges
#   GET /schema/{connection_id}/table/{table_name} — Single table schema
# ============================================================

import logging
from fastapi import APIRouter, HTTPException, status
from models.schemas import (
    FullSchemaResponse, SchemaGraphResponse, TableSchema,
    GraphNode, RelationshipEdge, ColumnSchema, ForeignKeyRef,
    IndexInfo, UniqueConstraintInfo,
)
from core.database import get_connection, get_cached_schema, set_cached_schema
from core.schema_extractor import extract_full_schema, build_relationship_map, get_single_table_schema

logger = logging.getLogger(__name__)
router = APIRouter()


def _raw_table_to_model(raw: dict) -> TableSchema:
    """
    Convert the raw dict from schema_extractor into a typed TableSchema Pydantic model.

    Kept as a private helper so both /schema and /schema/table/{name} can reuse it
    without code duplication.

    Args:
        raw: Single table dict from extract_full_schema()["tables"].

    Returns:
        Fully validated TableSchema model.
    """
    columns = []
    for col in raw.get("columns", []):
        fk_refs = [
            ForeignKeyRef(ref_table=fk["ref_table"], ref_column=fk["ref_column"])
            for fk in col.get("foreign_keys", [])
        ]
        columns.append(ColumnSchema(
            name=col["name"],
            type=col["type"],
            nullable=col["nullable"],
            default=col.get("default"),
            primary_key=col["primary_key"],
            foreign_keys=fk_refs,
        ))

    indexes = [
        IndexInfo(name=idx.get("name", ""), columns=idx.get("columns", []), unique=idx.get("unique", False))
        for idx in raw.get("indexes", [])
    ]
    unique_constraints = [
        UniqueConstraintInfo(name=uc.get("name", ""), columns=uc.get("columns", []))
        for uc in raw.get("unique_constraints", [])
    ]

    return TableSchema(
        name=raw["name"],
        row_count=raw.get("row_count", -1),
        columns=columns,
        indexes=indexes,
        unique_constraints=unique_constraints,
    )


@router.get(
    "/schema/{connection_id}",
    response_model=FullSchemaResponse,
    tags=["schema"],
    summary="Get full database schema",
    description="Introspects the database and returns metadata for all tables — "
                "columns, types, PKs, FKs, indexes, and row counts.",
)
async def get_full_schema(connection_id: str) -> FullSchemaResponse:
    """Extract and return the complete database schema."""
    try:
        engine = get_connection(connection_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    try:
        # Use cache so row counts are only fetched once per connection
        raw_schema = get_cached_schema(connection_id)
        if raw_schema is None:
            raw_schema = extract_full_schema(engine)
            set_cached_schema(connection_id, raw_schema)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    tables = [_raw_table_to_model(t) for t in raw_schema.get("tables", [])]
    return FullSchemaResponse(
        connection_id=connection_id,
        dialect=raw_schema.get("dialect", "unknown"),
        table_count=len(tables),
        tables=tables,
    )


@router.get(
    "/schema/{connection_id}/graph",
    response_model=SchemaGraphResponse,
    tags=["schema"],
    summary="Get schema as React Flow graph",
    description="Returns nodes (tables) and edges (FK relationships) for React Flow ER diagrams.",
)
async def get_schema_graph(connection_id: str) -> SchemaGraphResponse:
    """Build and return a React Flow-compatible graph of the schema."""
    try:
        engine = get_connection(connection_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    try:
        # Skip row counts for the ER diagram — pure structural reflection is fast
        raw_schema = extract_full_schema(engine, skip_row_counts=True)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    # Build nodes (one per table)
    nodes = []
    for table in raw_schema.get("tables", []):
        col_names = [c["name"] for c in table.get("columns", [])]
        nodes.append(GraphNode(
            id=table["name"],
            label=table["name"],
            row_count=table.get("row_count", -1),
            columns=col_names,
            data={"row_count": table.get("row_count", -1), "column_count": len(col_names)},
        ))

    # Build edges (one per FK relationship)
    edges = [
        RelationshipEdge(
            edge_id=e["edge_id"],
            from_table=e["from_table"],
            from_col=e["from_col"],
            to_table=e["to_table"],
            to_col=e["to_col"],
            label=f"{e['from_col']} → {e['to_col']}",
        )
        for e in build_relationship_map(raw_schema)
    ]

    return SchemaGraphResponse(connection_id=connection_id, nodes=nodes, edges=edges)


@router.get(
    "/schema/{connection_id}/table/{table_name}",
    response_model=TableSchema,
    tags=["schema"],
    summary="Get schema for a single table",
)
async def get_table_schema(connection_id: str, table_name: str) -> TableSchema:
    """Return column metadata, indexes, and constraints for one specific table."""
    try:
        engine = get_connection(connection_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    try:
        raw_table = get_single_table_schema(engine, table_name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return _raw_table_to_model(raw_table)