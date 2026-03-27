"""
retriever.py — Semantic Schema Search

Queries ChromaDB to find the most relevant tables and columns for a given
natural language question. This is the RAG "Retrieval" step.

Why RAG for SQL generation?
 - Large schemas (100+ tables) exceed LLM context windows
 - Retrieving only the 5 most relevant tables gives the LLM focused context
 - Grounds the SQL generation in REAL column names, preventing hallucination
"""

import logging

import chromadb
from chromadb.config import Settings as ChromaSettings

from config.settings import settings

logger = logging.getLogger(__name__)


class SchemaRetriever:
    """Semantic search over embedded schema collections."""

    def __init__(self) -> None:
       
        self._chroma = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._tables_col  = self._chroma.get_or_create_collection("schema_tables")
        self._columns_col = self._chroma.get_or_create_collection("schema_columns")

    def search_tables(
        self,
        query: str,
        connection_id: str,
        top_k: int = 5,
    ) -> list[dict]:
        """
        Return the top_k most semantically relevant tables for a query.

        ChromaDB's query() takes a natural language string, embeds it with
        the same model used at insert time, then returns cosine-nearest docs.
        We filter by connection_id so we only search THIS database's schema.
        """
        try:
            results = self._tables_col.query(
                query_texts=[query],
                n_results=min(top_k, self._tables_col.count()),
                where={"connection_id": {"$eq": connection_id}},
                include=["documents", "metadatas", "distances"],
            )

            tables = []
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                tables.append({
                    "document":     doc,
                    "table_name":   meta.get("table_name"),
                    "row_count":    meta.get("row_count"),
                    "column_count": meta.get("column_count"),
                    
                    "relevance":    round(1 - dist, 4),
                })
            return tables

        except Exception as exc:
            logger.error(f"search_tables failed: {exc}")
            return []

    def search_columns(
        self,
        query: str,
        connection_id: str,
        top_k: int = 10,
    ) -> list[dict]:
        """Return the top_k most relevant columns for a query."""
        try:
            results = self._columns_col.query(
                query_texts=[query],
                n_results=min(top_k, self._columns_col.count()),
                where={"connection_id": {"$eq": connection_id}},
                include=["documents", "metadatas", "distances"],
            )

            columns = []
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                columns.append({
                    "document":    doc,
                    "table_name":  meta.get("table_name"),
                    "column_name": meta.get("column_name"),
                    "dtype":       meta.get("dtype"),
                    "is_pk":       meta.get("is_pk"),
                    "has_fk":      meta.get("has_fk"),
                    "relevance":   round(1 - dist, 4),
                })
            return columns

        except Exception as exc:
            logger.error(f"search_columns failed: {exc}")
            return []

    def get_context_for_question(
        self,
        question: str,
        connection_id: str,
    ) -> str:
        """
        Assemble a formatted context string for LLM prompt injection.

        This is what gets pasted into the SQL generation prompt.
        Format is designed to be human-readable (LLMs parse structured
        natural language better than raw JSON in this context).
        """
        tables  = self.search_tables(query=question, connection_id=connection_id, top_k=5)
        columns = self.search_columns(query=question, connection_id=connection_id, top_k=10)

        if not tables and not columns:
            return "No schema context available. Schema may not be embedded yet."

        lines = ["=== RELEVANT SCHEMA CONTEXT ===\n"]

        lines.append("--- Most Relevant Tables ---")
        for t in tables:
            lines.append(
                f"  TABLE: {t['table_name']} "
                f"({t['row_count']} rows, {t['column_count']} columns) "
                f"[relevance: {t['relevance']}]"
            )
            lines.append(f"    {t['document']}")

        lines.append("\n--- Most Relevant Columns ---")
        by_table: dict[str, list] = {}
        for c in columns:
            by_table.setdefault(c["table_name"], []).append(c)

        for table_name, cols in by_table.items():
            lines.append(f"  Table: {table_name}")
            for c in cols:
                pk_flag = " [PK]" if c["is_pk"] else ""
                fk_flag = " [FK]" if c["has_fk"] else ""
                lines.append(
                    f"    - {c['column_name']} ({c['dtype']}){pk_flag}{fk_flag}"
                    f"  [relevance: {c['relevance']}]"
                )

        return "\n".join(lines)