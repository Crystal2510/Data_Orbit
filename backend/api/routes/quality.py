# ============================================================
# backend/api/routes/quality.py
# ============================================================
# ENDPOINTS:
#   GET /quality/{connection_id}                  — Full quality report
#   GET /quality/{connection_id}/table/{name}     — Single table quality
#   GET /quality/{connection_id}/pii              — PII risk report
# ============================================================

import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from models.schemas import (
    QualityReportResponse, TableQuality, ColumnQuality, AnomalyDetail,
    PIIReportResponse, PIITableResult, PIIColumnResult,
)
from core.database import get_connection, get_cached_schema, set_cached_schema
from core.quality_analyzer import analyze_table_quality, analyze_all_tables
from core.schema_extractor import extract_full_schema
from core.pii_detector import analyze_pii_for_schema

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory quality cache: connection_id → raw quality results
_quality_cache: dict = {}


def _raw_quality_to_model(raw: dict) -> TableQuality:
    """
    Convert the raw dict from quality_analyzer into a typed TableQuality Pydantic model.

    Private helper reused by both /quality/{id} (all tables)
    and /quality/{id}/table/{name} (single table) routes.

    Args:
        raw: Dict from analyze_table_quality() / analyze_all_tables().

    Returns:
        TableQuality Pydantic model.
    """
    columns = [
        ColumnQuality(
            column_name=col["column_name"],
            dtype=col.get("dtype", "object"),
            null_count=col.get("null_count", 0),
            null_rate=col.get("null_rate", 0.0),
            fill_rate=col.get("fill_rate", 100.0),
            unique_count=col.get("unique_count", 0),
            unique_rate=col.get("unique_rate", 0.0),
            min=col.get("min"),
            max=col.get("max"),
            mean=col.get("mean"),
            sample_values=col.get("sample_values", []),
        )
        for col in raw.get("columns", [])
    ]

    anomalies = [
        AnomalyDetail(
            type=a.get("type", "unknown"),
            description=a.get("description", ""),
            affected_rows=a.get("affected_rows", 0),
            columns_involved=a.get("columns_involved", []),
        )
        for a in raw.get("anomalies", [])
    ]

    return TableQuality(
        table_name=raw["table_name"],
        total_rows=raw.get("total_rows", -1),
        total_columns=raw.get("total_columns", 0),
        quality_score=raw.get("quality_score", 0.0),
        freshness_days=raw.get("freshness_days"),
        anomalies=anomalies,
        columns=columns,
        error=raw.get("error"),
    )


@router.get(
    "/quality/{connection_id}",
    response_model=QualityReportResponse,
    tags=["quality"],
    summary="Full data quality report",
    description=(
        "Runs quality analysis on every table. "
        "Returns null rates, fill rates, uniqueness, freshness, anomalies, "
        "and a composite quality score per table."
    ),
)
async def get_full_quality_report(connection_id: str) -> QualityReportResponse:
    """
    Analyze data quality for all tables in the connected database.

    Note: This can be slow for large databases. Use the single-table endpoint
    for targeted, faster analysis during development.
    """
    try:
        engine = get_connection(connection_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    try:
        # Use cache to avoid re-running expensive quality analysis on every visit
        if connection_id in _quality_cache:
            logger.info(f"Quality report: cache hit for {connection_id}")
            raw_results = _quality_cache[connection_id]
        else:
            raw_results = analyze_all_tables(engine)
            _quality_cache[connection_id] = raw_results
    except Exception as e:
        logger.error(f"Full quality analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Quality analysis failed: {str(e)}",
        )

    tables = [_raw_quality_to_model(r) for r in raw_results]
    return QualityReportResponse(
        connection_id=connection_id,
        table_count=len(tables),
        tables=tables,
        generated_at=datetime.utcnow(),
    )


@router.get(
    "/quality/{connection_id}/table/{table_name}",
    response_model=TableQuality,
    tags=["quality"],
    summary="Quality report for a single table",
)
async def get_table_quality(connection_id: str, table_name: str) -> TableQuality:
    """Analyze data quality for a single named table."""
    try:
        engine = get_connection(connection_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    try:
        raw = analyze_table_quality(engine, table_name)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return _raw_quality_to_model(raw)


@router.get(
    "/quality/{connection_id}/pii",
    response_model=PIIReportResponse,
    tags=["quality"],
    summary="PII risk detection report",
    description=(
        "Classifies every column across all tables as High / Low / No PII risk. "
        "Uses heuristic keyword matching + optional GPT reasoning (if OPENAI_API_KEY set)."
    ),
)
async def get_pii_report(connection_id: str) -> PIIReportResponse:
    """Run PII risk detection for all columns in the connected database."""
    try:
        engine = get_connection(connection_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    try:
        # Use cached schema to avoid re-extraction
        raw_schema = get_cached_schema(connection_id)
        if raw_schema is None:
            raw_schema = extract_full_schema(engine, skip_row_counts=True)
            set_cached_schema(connection_id, raw_schema)
        raw_pii = analyze_pii_for_schema(raw_schema, engine)
    except Exception as e:
        logger.error(f"PII analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PII analysis failed: {str(e)}",
        )

    table_results = []
    total_high = 0
    total_low = 0

    for table_pii in raw_pii:
        col_results = [
            PIIColumnResult(
                column_name=col["column_name"],
                risk_level=col.get("risk_level", "None"),
                reasoning=col.get("reasoning", ""),
                detection_method=col.get("detection_method", "heuristic"),
            )
            for col in table_pii.get("columns", [])
        ]
        high = sum(1 for c in col_results if c.risk_level == "High")
        low = sum(1 for c in col_results if c.risk_level == "Low")
        total_high += high
        total_low += low
        table_results.append(PIITableResult(
            table_name=table_pii["table_name"],
            columns=col_results,
            high_risk_count=high,
            low_risk_count=low,
        ))

    return PIIReportResponse(
        connection_id=connection_id,
        tables=table_results,
        total_high_risk_columns=total_high,
        total_low_risk_columns=total_low,
        generated_at=datetime.utcnow(),
    )