# ============================================================
# backend/core/pii_detector.py
# ============================================================
# PII (Personally Identifiable Information) risk classification.
#
# TWO-TIER DETECTION:
#   TIER 1 — Heuristic keyword matching (always runs, zero cost, zero I/O)
#   TIER 2 — LLM-assisted reasoning via OpenAI GPT (runs if OPENAI_API_KEY set)
#             Only called for borderline "None" results on text columns.
#
# RISK LEVELS:
#   "High" → Direct PII (name, email, phone, SSN, address, password…)
#   "Low"  → Indirect PII risk (free text — reviews, comments, messages)
#   "None" → No PII risk (IDs, timestamps, metrics, status codes)
#
# SECURITY NOTE:
#   Only column NAMES and small sample VALUES are sent to OpenAI.
#   Raw customer data rows are never transmitted.
# ============================================================

import logging
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)

# ── Heuristic keyword lists ────────────────────────────────────────────────────
# Matched against lowercased column names.

HIGH_RISK_KEYWORDS = [
    "email", "e_mail", "mail",
    "phone", "mobile", "telephone", "cell",
    "name", "firstname", "lastname", "fullname", "username",
    "address", "street", "city", "zip", "postal",
    "ssn", "social_security", "national_id", "passport",
    "password", "passwd", "pwd", "secret", "token",
    "credit", "card", "cvv", "iban", "bank",
    "dob", "date_of_birth", "birth_date", "birthday",
    "gender", "sex",
    "ip_address", "ip", "device_id", "mac_address",
    "latitude", "longitude", "location", "gps",
    "salary", "income", "wage",
]

LOW_RISK_KEYWORDS = [
    "message", "comment", "review", "description", "notes", "note",
    "feedback", "text", "content", "body", "summary",
    "subject", "title", "reason", "detail", "details",
]

# Explicit non-PII patterns — override everything else when matched at end of name
NO_RISK_SUFFIXES = [
    "id", "uuid", "key", "code", "status", "type", "category",
    "count", "amount", "total", "price", "rate", "score", "rank",
    "timestamp", "created_at", "updated_at",
    "flag", "active", "enabled", "deleted",
]


def _heuristic_pii_check(column_name: str) -> dict:
    """
    Apply keyword matching rules to classify a column's PII risk.

    Pure function — no I/O, no side effects, runs in microseconds.

    Args:
        column_name: Database column name.

    Returns:
        Dict with risk_level, reasoning, and detection_method="heuristic".
    """
    name_lower = column_name.lower()

    # HIGH RISK — direct personal identifiers
    for keyword in HIGH_RISK_KEYWORDS:
        if keyword in name_lower:
            return {
                "risk_level": "High",
                "reasoning": (
                    f"Column name '{column_name}' contains the keyword '{keyword}', "
                    f"which is strongly associated with directly identifiable personal information."
                ),
                "detection_method": "heuristic",
            }

    # LOW RISK — free text that may incidentally contain PII
    for keyword in LOW_RISK_KEYWORDS:
        if keyword in name_lower:
            return {
                "risk_level": "Low",
                "reasoning": (
                    f"Column '{column_name}' contains keyword '{keyword}', "
                    f"suggesting a free-text field that may incidentally contain PII "
                    f"(e.g. personal names or contact details in messages or reviews)."
                ),
                "detection_method": "heuristic",
            }

    # EXPLICIT NO RISK — system identifiers, metrics, status fields
    for suffix in NO_RISK_SUFFIXES:
        if name_lower.endswith(suffix) or name_lower == suffix:
            return {
                "risk_level": "None",
                "reasoning": (
                    f"Column '{column_name}' matches a known non-PII pattern "
                    f"('{suffix}'). Classified as a system/operational field."
                ),
                "detection_method": "heuristic",
            }

    # DEFAULT — no PII signal detected
    return {
        "risk_level": "None",
        "reasoning": (
            f"Column '{column_name}' does not match any PII-indicator keywords. "
            f"Classified as non-PII based on heuristic analysis."
        ),
        "detection_method": "heuristic",
    }


def _llm_pii_check(
    column_name: str,
    sample_values: list,
    dtype: str,
    table_name: str = "",
) -> Optional[dict]:
    """
    Use OpenAI GPT to reason about PII risk with full context.

    Only called when:
      1. settings.OPENAI_API_KEY is configured
      2. The heuristic result returned "None" for a text-type column
         (LLM handles the ambiguous edge cases heuristics miss)

    Args:
        column_name: Database column name.
        sample_values: Up to 3 non-null sample values as strings.
        dtype: Pandas dtype string (e.g. "object", "int64").
        table_name: Parent table name (provides context for the LLM).

    Returns:
        Dict with risk_level, reasoning, detection_method="llm",
        or None if the API call fails (caller falls back to heuristic).
    """
    if not settings.OPENAI_API_KEY:
        return None

    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        # Truncate sample values — never send more than 100 chars per value to OpenAI
        safe_samples = [str(v)[:100] for v in sample_values[:3]]

        prompt = f"""You are a data privacy expert. Classify the PII risk of a database column.

Table: {table_name or "unknown"}
Column name: {column_name}
Data type: {dtype}
Sample values: {safe_samples}

Respond ONLY with a JSON object in this exact format:
{{
  "risk_level": "None" | "Low" | "High",
  "reasoning": "One sentence explanation."
}}

Risk level definitions:
- High: Column directly identifies a person (name, email, phone, address, SSN, etc.)
- Low: Free-text field that may incidentally contain PII (reviews, comments, support messages)
- None: System fields, IDs, metrics, timestamps, codes, flags"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Fast and cheap for classification tasks
            messages=[{"role": "user", "content": prompt}],
            temperature=0,        # Deterministic output for consistent results
            max_tokens=150,
        )

        import json
        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if the model wraps the JSON
        raw = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)

        return {
            "risk_level": parsed.get("risk_level", "None"),
            "reasoning": parsed.get("reasoning", "LLM classification completed."),
            "detection_method": "llm",
        }

    except Exception as e:
        logger.warning(f"LLM PII check failed for '{column_name}': {e}")
        return None  # Caller handles fallback


def detect_pii_risk(
    column_name: str,
    sample_values: list,
    dtype: str,
    table_name: str = "",
) -> dict:
    """
    Primary PII detection function for a single column.

    Decision tree:
      1. Run heuristic check (always)
      2. If High or Low → high confidence, return immediately
      3. If None AND column is text type AND LLM key exists → try LLM
      4. Return best available result

    Args:
        column_name: Database column name.
        sample_values: Up to 3 non-null representative values.
        dtype: Column data type string.
        table_name: Parent table name (optional context for LLM).

    Returns:
        Dict with column_name, risk_level, reasoning, detection_method.
    """
    heuristic_result = _heuristic_pii_check(column_name)

    # High confidence results don't need LLM confirmation
    if heuristic_result["risk_level"] in ("High", "Low"):
        return {"column_name": column_name, **heuristic_result}

    # LLM tier: only for text columns where heuristic returned "None"
    # (numeric and boolean columns can't meaningfully hold PII text)
    is_text_column = any(t in dtype.lower() for t in ["object", "str", "varchar", "text", "char"])
    if is_text_column and settings.OPENAI_API_KEY:
        llm_result = _llm_pii_check(column_name, sample_values, dtype, table_name)
        if llm_result is not None:
            return {"column_name": column_name, **llm_result}

    # Fallback to heuristic result
    return {"column_name": column_name, **heuristic_result}


def analyze_pii_for_schema(schema: dict, engine) -> list[dict]:
    """
    Run PII detection across ALL columns of ALL tables in the schema.

    Process:
      1. Iterate every table in the schema dict
      2. Fetch a small sample DataFrame for context
      3. Run detect_pii_risk() on every column
      4. Aggregate into a per-table result list

    Args:
        schema: Full schema dict from extract_full_schema().
        engine: Active SQLAlchemy Engine (for fetching sample values).

    Returns:
        List of per-table PII results:
        [
            {
                "table_name": "order_reviews",
                "columns": [
                    {
                        "column_name": "review_comment_message",
                        "risk_level": "High",
                        "reasoning": "...",
                        "detection_method": "llm"
                    }
                ]
            }
        ]
    """
    import pandas as pd

    results = []

    for table in schema.get("tables", []):
        table_name = table["name"]
        table_result = {"table_name": table_name, "columns": []}

        # Fetch sample rows for this table (used for LLM context)
        sample_df = None
        try:
            with engine.connect() as conn:
                sample_df = pd.read_sql(
                    f'SELECT * FROM "{table_name}" LIMIT 3', conn
                )
        except Exception as e:
            logger.warning(f"Could not fetch samples for PII of '{table_name}': {e}")

        for col in table.get("columns", []):
            col_name = col["name"]
            col_dtype = col.get("type", "VARCHAR")

            # Extract sample values from the fetched DataFrame if available
            sample_vals = []
            if sample_df is not None and col_name in sample_df.columns:
                sample_vals = (
                    sample_df[col_name]
                    .dropna()
                    .astype(str)
                    .head(3)
                    .tolist()
                )

            pii_result = detect_pii_risk(
                column_name=col_name,
                sample_values=sample_vals,
                dtype=col_dtype,
                table_name=table_name,
            )
            table_result["columns"].append(pii_result)

        results.append(table_result)
        logger.info(
            f"PII analysis done — '{table_name}': "
            f"{len(table_result['columns'])} columns assessed."
        )

    return results