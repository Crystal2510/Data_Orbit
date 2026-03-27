# ============================================================
# backend/models/schemas.py
# ============================================================
# SINGLE SOURCE OF TRUTH for all API data contracts.
#
# Every request body and response body is defined here as a Pydantic v2 model.
# This ensures:
#   - Dev 3 (Frontend) knows the exact JSON shape of every endpoint
#   - Dev 2 (AI Engine) can import these models for validation
#   - FastAPI auto-generates accurate Swagger / OpenAPI documentation
#
# IMPORT PATTERN:
#   from models.schemas import FullSchemaResponse, TableQuality, PIIReportResponse
# ============================================================

from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict


# ─────────────────────────────────────────────────────────────
#  CONNECTION MODELS
# ─────────────────────────────────────────────────────────────

class ConnectionRequest(BaseModel):
    """Request body for POST /connect."""
    model_config = ConfigDict(from_attributes=True)

    connection_string: str = Field(
        ...,
        description=(
            "SQLAlchemy database URL.\n"
            "Examples:\n"
            "  sqlite:///./olist.db\n"
            "  postgresql+psycopg2://user:pass@localhost:5432/mydb\n"
            "  mysql+pymysql://user:pass@localhost:3306/mydb"
        ),
        examples=["sqlite:///./olist.db"],
    )


class ConnectionResponse(BaseModel):
    """Response from POST /connect — includes the session UUID."""
    model_config = ConfigDict(from_attributes=True)

    connection_id: str = Field(
        description="UUID that identifies this DB session. Pass in all subsequent API calls."
    )
    dialect: str = Field(
        description="DB dialect detected from the connection string (sqlite, postgresql, mysql…)"
    )
    message: str = Field(default="Connection established successfully.")


class ConnectionListResponse(BaseModel):
    """Response for GET /connections."""
    model_config = ConfigDict(from_attributes=True)

    active_connections: List[str] = Field(description="All currently active connection UUIDs.")
    count: int = Field(description="Total number of active connections.")


# ─────────────────────────────────────────────────────────────
#  SCHEMA MODELS
# ─────────────────────────────────────────────────────────────

class ForeignKeyRef(BaseModel):
    """One FK reference — the referenced table and column."""
    model_config = ConfigDict(from_attributes=True)

    ref_table: str = Field(description="Table that this FK points to.")
    ref_column: str = Field(description="Column in the referenced table.")


class ColumnSchema(BaseModel):
    """Metadata for a single database column."""
    model_config = ConfigDict(from_attributes=True)

    name: str = Field(description="Column name as it exists in the database.")
    type: str = Field(description="SQL data type, e.g. 'VARCHAR(255)', 'INTEGER', 'TIMESTAMP'.")
    nullable: bool = Field(description="True if the column allows NULL values.")
    default: Optional[str] = Field(default=None, description="Default value expression, if any.")
    primary_key: bool = Field(description="True if this column is part of the primary key.")
    foreign_keys: List[ForeignKeyRef] = Field(
        default_factory=list,
        description="FK references this column makes to other tables."
    )


class IndexInfo(BaseModel):
    """A single database index."""
    model_config = ConfigDict(from_attributes=True)

    name: str
    columns: List[str] = Field(description="Columns included in this index.")
    unique: bool = Field(description="True if this is a unique index.")


class UniqueConstraintInfo(BaseModel):
    """A UNIQUE constraint (distinct from a unique index in some dialects)."""
    model_config = ConfigDict(from_attributes=True)

    name: str
    columns: List[str]


class TableSchema(BaseModel):
    """Full metadata for a single database table."""
    model_config = ConfigDict(from_attributes=True)

    name: str
    row_count: int = Field(description="Approximate row count (-1 if unavailable).")
    columns: List[ColumnSchema]
    indexes: List[IndexInfo] = Field(default_factory=list)
    unique_constraints: List[UniqueConstraintInfo] = Field(default_factory=list)


class FullSchemaResponse(BaseModel):
    """Complete schema for the connected database — returned by GET /schema/{id}."""
    model_config = ConfigDict(from_attributes=True)

    connection_id: str
    dialect: str = Field(description="Database engine dialect.")
    table_count: int = Field(description="Total number of tables in the schema.")
    tables: List[TableSchema]


# ── React Flow Graph Models ────────────────────────────────────────────────────

class GraphNode(BaseModel):
    """A node in the React Flow ER diagram. Represents one table."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Unique node ID (= table name).")
    label: str = Field(description="Display label for the node.")
    row_count: int
    columns: List[str] = Field(description="Column names shown in the node body.")
    data: dict = Field(default_factory=dict, description="Additional React Flow node metadata.")


class RelationshipEdge(BaseModel):
    """An edge in the React Flow graph — represents one FK relationship."""
    model_config = ConfigDict(from_attributes=True)

    edge_id: str = Field(description="Unique edge ID.")
    from_table: str
    from_col: str = Field(description="Source column (the FK column).")
    to_table: str
    to_col: str = Field(description="Target column (the PK being referenced).")
    label: str = Field(description="Human-readable label: 'from_col → to_col'.")


class SchemaGraphResponse(BaseModel):
    """React Flow ER diagram data — returned by GET /schema/{id}/graph."""
    model_config = ConfigDict(from_attributes=True)

    connection_id: str
    nodes: List[GraphNode] = Field(description="One node per database table.")
    edges: List[RelationshipEdge] = Field(description="One edge per FK relationship.")


# ─────────────────────────────────────────────────────────────
#  QUALITY MODELS
# ─────────────────────────────────────────────────────────────

class AnomalyDetail(BaseModel):
    """A single detected data anomaly."""
    model_config = ConfigDict(from_attributes=True)

    type: str = Field(description="Anomaly category, e.g. 'impossible_date_order'.")
    description: str
    affected_rows: int
    columns_involved: List[str]


class ColumnQuality(BaseModel):
    """Quality metrics for a single column."""
    model_config = ConfigDict(from_attributes=True)

    column_name: str
    dtype: str = Field(description="Pandas dtype string.")
    null_count: int
    null_rate: float = Field(description="% rows that are NULL (0–100).")
    fill_rate: float = Field(description="% rows that are non-NULL (0–100).")
    unique_count: int
    unique_rate: float = Field(description="Unique values as % of non-null count.")
    min: Optional[Any] = Field(default=None)
    max: Optional[Any] = Field(default=None)
    mean: Optional[float] = Field(default=None)
    sample_values: List[str] = Field(default_factory=list)


class TableQuality(BaseModel):
    """Quality report for an entire table."""
    model_config = ConfigDict(from_attributes=True)

    table_name: str
    total_rows: int
    total_columns: int
    quality_score: float = Field(
        description="Composite quality score 0–100. "
                    "Formula: fill_rate×0.5 + uniqueness×0.3 + freshness×0.2"
    )
    freshness_days: Optional[float] = Field(
        default=None,
        description="Days since most recent timestamp value. None if no timestamp column."
    )
    anomalies: List[AnomalyDetail] = Field(default_factory=list)
    columns: List[ColumnQuality]
    error: Optional[str] = Field(default=None, description="Error if this table failed to analyze.")


class QualityReportResponse(BaseModel):
    """Full quality report for all tables — returned by GET /quality/{id}."""
    model_config = ConfigDict(from_attributes=True)

    connection_id: str
    table_count: int
    tables: List[TableQuality]
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────────────────────────
#  PII MODELS
# ─────────────────────────────────────────────────────────────

class PIIColumnResult(BaseModel):
    """PII risk assessment for a single column."""
    model_config = ConfigDict(from_attributes=True)

    column_name: str
    risk_level: str = Field(description="'None', 'Low', or 'High'.")
    reasoning: str = Field(description="Explanation of why this risk level was assigned.")
    detection_method: str = Field(description="'heuristic' or 'llm'.")


class PIITableResult(BaseModel):
    """PII assessment for all columns in one table."""
    model_config = ConfigDict(from_attributes=True)

    table_name: str
    columns: List[PIIColumnResult]
    high_risk_count: int
    low_risk_count: int


class PIIReportResponse(BaseModel):
    """Full PII report — returned by GET /quality/{id}/pii."""
    model_config = ConfigDict(from_attributes=True)

    connection_id: str
    tables: List[PIITableResult]
    total_high_risk_columns: int
    total_low_risk_columns: int
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────────────────────────
#  HEALTH MODEL
# ─────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    """Response for GET /health."""
    model_config = ConfigDict(from_attributes=True)

    status: str = Field(default="ok")
    service: str = Field(default="Data Dictionary Agent")
    version: str = Field(default="1.0.0")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    active_connections: int