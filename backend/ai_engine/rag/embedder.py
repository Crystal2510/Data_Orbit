"""
embedder.py — Schema Embedding into ChromaDB

Converts schema metadata (tables, columns) into vector embeddings stored in
ChromaDB. This enables semantic search: "find columns related to geography"
returns geolocation.city, customers.customer_city, sellers.seller_state
even though none of them contain the word "geography".

Architecture decisions:
 - Two separate ChromaDB collections: schema_tables and schema_columns
   Separation lets us search at different granularities independently.
 - connection_id is stored as metadata on every document so we can filter
   results to only the schema of the currently connected database.
 - ChromaDB's default embedding function (all-MiniLM-L6-v2) runs locally —
   no additional API keys needed for embeddings.
"""

import logging
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from config.settings import settings

logger = logging.getLogger(__name__)


class SchemaEmbedder:
    """Embeds schema metadata into two ChromaDB collections."""

    def __init__(self) -> None:
        self._chroma = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        self._tables_col = self._chroma.get_or_create_collection(
            name="schema_tables",
            metadata={"hnsw:space": "cosine"},
        )
        self._columns_col = self._chroma.get_or_create_collection(
            name="schema_columns",
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            f"SchemaEmbedder ready — persist_dir={settings.CHROMA_PERSIST_DIR}"
        )

    def embed_schema(self, schema: dict, connection_id: str) -> None:
        """
        Iterate the full schema dict (from Dev 1's extract_full_schema)
        and embed every table and column as a separate document.

        Document format matters for retrieval quality:
        - We write natural language descriptions, not raw JSON
        - Include synonyms implicitly (e.g. mentioning "rows" and "records")
        - Column documents include their parent table name for JOIN context
        """
        table_ids: list[str]       = []
        table_documents: list[str] = []
        table_metadatas: list[dict] = []

        col_ids: list[str]       = []
        col_documents: list[str] = []
        col_metadatas: list[dict] = []

        for table in schema.get("tables", []):
            table_name  = table["name"]
            row_count   = table.get("row_count", 0)
            col_names   = [c["name"] for c in table.get("columns", [])]
            pk_cols     = [c["name"] for c in table.get("columns", []) if c.get("primary_key")]
            fk_cols     = [c["name"] for c in table.get("columns", []) if c.get("foreign_keys")]

            
            table_doc = (
                f"Table: {table_name}. "
                f"Contains {row_count} rows (records). "
                f"Columns: {', '.join(col_names)}. "
                f"Primary keys: {', '.join(pk_cols) or 'none'}. "
                f"Foreign keys: {', '.join(fk_cols) or 'none'}."
            )

            
            table_ids.append(f"{connection_id}::{table_name}")
            table_documents.append(table_doc)
            table_metadatas.append({
                "connection_id": connection_id,
                "table_name":    table_name,
                "row_count":     row_count,
                "column_count":  len(col_names),
            })

         
            for col in table.get("columns", []):
                col_name = col["name"]
                dtype    = col.get("type", "unknown")
                is_pk    = col.get("primary_key", False)
                fks      = col.get("foreign_keys", [])

                fk_info = ""
                if fks:
                    refs = [f"{fk['ref_table']}.{fk['ref_column']}" for fk in fks]
                    fk_info = f"References: {', '.join(refs)}."

                col_doc = (
                    f"Column: {col_name} in table {table_name}. "
                    f"Data type: {dtype}. "
                    f"{'Primary key. ' if is_pk else ''}"
                    f"{'Foreign key. ' + fk_info if fks else ''}"
                    f"Nullable: {col.get('nullable', True)}."
                )

                col_ids.append(f"{connection_id}::{table_name}::{col_name}")
                col_documents.append(col_doc)
                col_metadatas.append({
                    "connection_id": connection_id,
                    "table_name":    table_name,
                    "column_name":   col_name,
                    "dtype":         dtype,
                    "is_pk":         is_pk,
                    "has_fk":        bool(fks),
                })

        if table_ids:
            self._tables_col.upsert(
                ids=table_ids,
                documents=table_documents,
                metadatas=table_metadatas,
            )
            logger.info(
                f"Embedded {len(table_ids)} tables for connection {connection_id}"
            )

        if col_ids:
            self._columns_col.upsert(
                ids=col_ids,
                documents=col_documents,
                metadatas=col_metadatas,
            )
            logger.info(
                f"Embedded {len(col_ids)} columns for connection {connection_id}"
            )

    def clear_schema(self, connection_id: str) -> None:
        """
        Remove all embeddings associated with a specific connection_id.
        Called when a connection is deleted or re-initialized.
        """
        try:
            self._tables_col.delete(
                where={"connection_id": {"$eq": connection_id}}
            )
            self._columns_col.delete(
                where={"connection_id": {"$eq": connection_id}}
            )
            logger.info(f"Cleared embeddings for connection {connection_id}")
        except Exception as exc:
            logger.error(f"Failed to clear embeddings: {exc}")