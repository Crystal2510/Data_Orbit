# ============================================================
# backend/core/quality_analyzer.py
# ============================================================
# Computes comprehensive data quality metrics for database tables.
# Uses pandas DataFrames loaded via SQLAlchemy for statistical analysis.
#
# METRICS PER COLUMN:
#   null_count, null_rate (%), fill_rate (%), unique_count, unique_rate (%),
#   min, max, mean (numeric/datetime), sample_values (3 representative values)
#
# TABLE-LEVEL METRICS:
#   total_rows, total_columns, freshness (days since most recent timestamp),
#   anomalies (impossible date combinations), quality_score (0–100)
#
# QUALITY SCORE FORMULA:
#   score = (avg_fill_rate × 0.5) + (avg_uniqueness × 0.3) + (freshness_score × 0.2)
#   Clamped to [0, 100].
#   Rationale: completeness is most critical for data usability.
#
# SAFETY: Tables larger than MAX_ROWS_PER_TABLE are sampled to prevent OOM.
# ============================================================

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import pandas as pd
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

# Timestamp column detection keywords (matched against lowercased column names)
TIMESTAMP_KEYWORDS = [
    "date", "time", "timestamp", "created", "updated", "modified",
    "purchased", "delivered", "approved", "at",
]

# Safety cap: analyse at most this many rows per table to prevent memory issues
MAX_ROWS_PER_TABLE = 100_000


def _is_timestamp_column(col_name: str, dtype) -> bool:
    """
    Heuristically determine if a column holds datetime/timestamp data.

    Checks both:
      1. The column name for date/time keywords
      2. The pandas dtype (already parsed as datetime64 by pandas)

    Args:
        col_name: Column name string.
        dtype: pandas dtype of the column.

    Returns:
        True if the column is likely a datetime column.
    """
    name_lower = col_name.lower()
    name_match = any(kw in name_lower for kw in TIMESTAMP_KEYWORDS)
    dtype_match = pd.api.types.is_datetime64_any_dtype(dtype)
    return name_match or dtype_match


def _compute_freshness(df: pd.DataFrame) -> Optional[float]:
    """
    Find the most recent timestamp value across all datetime-like columns
    and return how many days ago it was relative to UTC now.

    Result interpretation:
      0   → data was updated today
      30  → most recent record is 1 month old
      365 → most recent record is 1 year old
      None → no timestamp column found in this table

    Args:
        df: pandas DataFrame representing a table sample.

    Returns:
        Float days since most recent timestamp, or None.
    """
    most_recent: Optional[datetime] = None

    for col in df.columns:
        if not _is_timestamp_column(col, df[col].dtype):
            continue
        try:
            # pd.to_datetime handles strings, ints (unix epoch), ISO formats
            parsed = pd.to_datetime(df[col], errors="coerce", utc=True)
            col_max = parsed.max()
            if pd.isna(col_max):
                continue
            col_max_dt = col_max.to_pydatetime()
            if most_recent is None or col_max_dt > most_recent:
                most_recent = col_max_dt
        except Exception:
            continue  # Be resilient — skip unparseable columns

    if most_recent is None:
        return None

    now = datetime.now(timezone.utc)
    delta = now - most_recent
    return round(delta.total_seconds() / 86400, 2)  # Convert seconds → days


def _detect_anomalies(df: pd.DataFrame, table_name: str) -> list[dict]:
    """
    Detect logical data anomalies using business-rule heuristics.

    RULE 1 — Impossible delivery dates:
      Flags rows where delivered_date < purchase_date.
      (Common in e-commerce datasets like Olist.)

    RULE 2 — Negative monetary values:
      Flags rows where price/amount/value columns are negative.

    Args:
        df: Table DataFrame.
        table_name: Name of the table (for log messages).

    Returns:
        List of anomaly dicts with type, description, affected_rows, columns_involved.
    """
    anomalies = []

    # ── Rule 1: Delivery before purchase ─────────────────────────────────────
    purchase_cols = [c for c in df.columns if "purchase" in c.lower()]
    delivery_cols = [
        c for c in df.columns
        if "delivered" in c.lower() or "delivery" in c.lower()
    ]

    if purchase_cols and delivery_cols:
        try:
            purchase_ts = pd.to_datetime(df[purchase_cols[0]], errors="coerce")
            delivery_ts = pd.to_datetime(df[delivery_cols[0]], errors="coerce")
            bad_mask = delivery_ts < purchase_ts
            bad_count = int(bad_mask.sum())
            if bad_count > 0:
                anomalies.append({
                    "type": "impossible_date_order",
                    "description": (
                        f"{bad_count} rows where '{delivery_cols[0]}' is BEFORE "
                        f"'{purchase_cols[0]}'. This is logically impossible and "
                        f"indicates data entry errors or ETL bugs."
                    ),
                    "affected_rows": bad_count,
                    "columns_involved": [purchase_cols[0], delivery_cols[0]],
                })
        except Exception as e:
            logger.debug(f"Anomaly rule 1 skipped for {table_name}: {e}")

    # ── Rule 2: Negative monetary values ─────────────────────────────────────
    money_keywords = ["price", "value", "amount", "revenue", "cost", "freight"]
    money_cols = [
        c for c in df.columns
        if any(kw in c.lower() for kw in money_keywords)
    ]
    for mc in money_cols:
        try:
            numeric = pd.to_numeric(df[mc], errors="coerce")
            neg_count = int((numeric < 0).sum())
            if neg_count > 0:
                anomalies.append({
                    "type": "negative_monetary_value",
                    "description": (
                        f"{neg_count} rows with negative values in '{mc}'. "
                        f"Monetary columns should be >= 0."
                    ),
                    "affected_rows": neg_count,
                    "columns_involved": [mc],
                })
        except Exception:
            continue

    return anomalies


def analyze_table_quality(engine: Engine, table_name: str) -> dict[str, Any]:
    """
    Load a table into pandas and compute comprehensive quality metrics.

    This is the core analysis function. Its output maps directly to the
    TableQuality Pydantic model defined in models/schemas.py.

    Args:
        engine: Active SQLAlchemy Engine.
        table_name: Name of the table to analyze.

    Returns:
        Dict with table-level and column-level quality metrics.

    Raises:
        RuntimeError: If the table cannot be loaded or analyzed.
    """
    logger.info(f"Analyzing quality for table: '{table_name}'")

    try:
        with engine.connect() as conn:
            # LIMIT prevents OOM on massive tables.
            # For a production system, you'd use statistical sampling instead.
            df = pd.read_sql(
                f'SELECT * FROM "{table_name}" LIMIT {MAX_ROWS_PER_TABLE}',
                conn
            )
    except SQLAlchemyError as e:
        logger.error(f"Failed to load '{table_name}': {e}")
        raise RuntimeError(f"Could not read table '{table_name}': {str(e)}") from e

    total_rows = len(df)
    total_columns = len(df.columns)

    # Handle empty tables gracefully
    if total_rows == 0:
        logger.warning(f"Table '{table_name}' is empty.")
        return {
            "table_name": table_name,
            "total_rows": 0,
            "total_columns": total_columns,
            "quality_score": 0.0,
            "freshness_days": None,
            "anomalies": [],
            "columns": [],
        }

    # ── Per-column metrics ────────────────────────────────────────────────────
    columns_quality = []
    fill_rates = []        # Used to compute overall quality_score
    uniqueness_scores = [] # Used to compute overall quality_score

    for col_name in df.columns:
        series = df[col_name]

        # NULL statistics
        null_count = int(series.isna().sum())
        null_rate = round((null_count / total_rows) * 100, 2)
        fill_rate = round(100.0 - null_rate, 2)
        fill_rates.append(fill_rate)

        # Uniqueness statistics
        non_null_series = series.dropna()
        non_null_count = len(non_null_series)
        unique_count = int(series.nunique(dropna=True))
        unique_rate = round((unique_count / non_null_count) * 100, 2) if non_null_count > 0 else 0.0
        uniqueness_scores.append(unique_rate)

        # Numeric statistics (min, max, mean)
        min_val: Optional[Any] = None
        max_val: Optional[Any] = None
        mean_val: Optional[float] = None

        if pd.api.types.is_numeric_dtype(series):
            numeric = pd.to_numeric(series, errors="coerce").dropna()
            if len(numeric) > 0:
                min_val = float(numeric.min())
                max_val = float(numeric.max())
                mean_val = round(float(numeric.mean()), 4)
        elif _is_timestamp_column(col_name, series.dtype):
            # For datetime columns, report min/max as ISO strings
            try:
                parsed = pd.to_datetime(series, errors="coerce").dropna()
                if len(parsed) > 0:
                    min_val = str(parsed.min())
                    max_val = str(parsed.max())
            except Exception:
                pass

        # Sample values — up to 3 distinct non-null values for the UI
        sample_values = (
            non_null_series
            .drop_duplicates()
            .head(3)
            .apply(str)
            .tolist()
        )

        columns_quality.append({
            "column_name": col_name,
            "dtype": str(series.dtype),
            "null_count": null_count,
            "null_rate": null_rate,
            "fill_rate": fill_rate,
            "unique_count": unique_count,
            "unique_rate": unique_rate,
            "min": min_val,
            "max": max_val,
            "mean": mean_val,
            "sample_values": sample_values,
        })

    # ── Freshness ─────────────────────────────────────────────────────────────
    freshness_days = _compute_freshness(df)

    # Convert freshness (days) to a 0–100 score:
    #   <= 1 day old  → 100 (perfectly fresh)
    #   >= 365 days   → 0   (stale)
    #   No timestamps → 50  (neutral, no evidence either way)
    if freshness_days is None:
        freshness_score = 50.0
    elif freshness_days <= 1:
        freshness_score = 100.0
    elif freshness_days >= 365:
        freshness_score = 0.0
    else:
        freshness_score = round(100.0 * (1 - freshness_days / 365), 2)

    # ── Anomaly detection ─────────────────────────────────────────────────────
    anomalies = _detect_anomalies(df, table_name)

    # ── Composite quality score ───────────────────────────────────────────────
    avg_fill = sum(fill_rates) / len(fill_rates) if fill_rates else 0.0
    avg_unique = sum(uniqueness_scores) / len(uniqueness_scores) if uniqueness_scores else 0.0

    # Weighted formula: completeness (50%) + uniqueness (30%) + freshness (20%)
    raw_score = (avg_fill * 0.5) + (avg_unique * 0.3) + (freshness_score * 0.2)
    quality_score = round(max(0.0, min(100.0, raw_score)), 2)

    logger.info(
        f"Quality done — '{table_name}': score={quality_score}, "
        f"rows={total_rows}, anomalies={len(anomalies)}"
    )

    return {
        "table_name": table_name,
        "total_rows": total_rows,
        "total_columns": total_columns,
        "quality_score": quality_score,
        "freshness_days": freshness_days,
        "anomalies": anomalies,
        "columns": columns_quality,
    }


def analyze_all_tables(engine: Engine) -> list[dict[str, Any]]:
    """
    Run quality analysis on every table in the database.

    Tables that fail to analyze are skipped with an error entry rather than
    crashing the whole report. This resilience is critical for heterogeneous
    databases with restricted views or permission-limited tables.

    Args:
        engine: Active SQLAlchemy Engine.

    Returns:
        List of table quality dicts (same structure as analyze_table_quality()).
    """
    inspector = sa_inspect(engine)
    table_names = inspector.get_table_names()
    logger.info(f"Starting quality analysis for {len(table_names)} tables...")

    results = []
    for table_name in table_names:
        try:
            results.append(analyze_table_quality(engine, table_name))
        except Exception as e:
            logger.error(f"Failed to analyze table '{table_name}': {e}")
            # Include a partial error record so the frontend knows this table failed
            results.append({
                "table_name": table_name,
                "total_rows": -1,
                "total_columns": -1,
                "quality_score": 0.0,
                "freshness_days": None,
                "anomalies": [],
                "columns": [],
                "error": str(e),
            })

    logger.info(f"Quality analysis complete: {len(results)} tables processed.")
    return results