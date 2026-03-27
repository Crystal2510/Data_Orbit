# ============================================================
# backend/tests/test_schema_extractor.py
# ============================================================
# Unit tests for schema extraction and database modules.
# Uses in-memory SQLite — no external database needed.
#
# RUN: cd backend && pytest tests/ -v
# ============================================================

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from core.database import (
    create_engine_from_url, test_connection,
    register_connection, get_connection, remove_connection,
)
from core.schema_extractor import (
    extract_full_schema, build_relationship_map, get_single_table_schema,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sqlite_engine() -> Engine:
    """
    In-memory SQLite engine with a minimal 2-table Olist-style schema:
      customers(customer_id PK, name, email)
      orders(order_id PK, customer_id FK, total, created_at)
    Pre-populated with 2 customers and 3 orders.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE customers (
                customer_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE orders (
                order_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                total REAL,
                created_at TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
            )
        """))
        conn.execute(text(
            "INSERT INTO customers VALUES ('c1','Alice','alice@example.com'),('c2','Bob','bob@example.com')"
        ))
        conn.execute(text(
            "INSERT INTO orders VALUES ('o1','c1',99.99,'2024-01-15'),('o2','c1',49.50,'2024-02-01'),('o3','c2',200.00,'2024-03-10')"
        ))
        conn.commit()
    return engine


# ── Database Module Tests ──────────────────────────────────────────────────────

class TestDatabaseModule:

    def test_create_sqlite_engine(self):
        engine = create_engine_from_url("sqlite:///:memory:")
        assert engine is not None
        assert engine.dialect.name == "sqlite"
        engine.dispose()

    def test_connection_test_passes(self, sqlite_engine):
        assert test_connection(sqlite_engine) is True

    def test_register_and_get_connection(self):
        conn_id = register_connection("sqlite:///:memory:")
        assert len(conn_id) == 36  # UUID4 format
        engine = get_connection(conn_id)
        assert engine.dialect.name == "sqlite"
        remove_connection(conn_id)

    def test_get_connection_raises_for_unknown_id(self):
        with pytest.raises(KeyError):
            get_connection("00000000-0000-0000-0000-000000000000")

    def test_remove_connection_returns_true(self):
        conn_id = register_connection("sqlite:///:memory:")
        assert remove_connection(conn_id) is True

    def test_remove_connection_returns_false_when_missing(self):
        assert remove_connection("does-not-exist") is False


# ── Schema Extractor Tests ─────────────────────────────────────────────────────

class TestSchemaExtractor:

    def test_returns_dict_with_required_keys(self, sqlite_engine):
        schema = extract_full_schema(sqlite_engine)
        assert "dialect" in schema
        assert "tables" in schema

    def test_dialect_is_sqlite(self, sqlite_engine):
        assert extract_full_schema(sqlite_engine)["dialect"] == "sqlite"

    def test_finds_both_tables(self, sqlite_engine):
        names = [t["name"] for t in extract_full_schema(sqlite_engine)["tables"]]
        assert "customers" in names
        assert "orders" in names

    def test_customers_has_three_columns(self, sqlite_engine):
        schema = extract_full_schema(sqlite_engine)
        customers = next(t for t in schema["tables"] if t["name"] == "customers")
        assert len(customers["columns"]) == 3

    def test_primary_key_detected(self, sqlite_engine):
        schema = extract_full_schema(sqlite_engine)
        customers = next(t for t in schema["tables"] if t["name"] == "customers")
        pk_cols = [c["name"] for c in customers["columns"] if c["primary_key"]]
        assert "customer_id" in pk_cols

    def test_foreign_key_detected(self, sqlite_engine):
        schema = extract_full_schema(sqlite_engine)
        orders = next(t for t in schema["tables"] if t["name"] == "orders")
        cid_col = next(c for c in orders["columns"] if c["name"] == "customer_id")
        assert len(cid_col["foreign_keys"]) > 0
        assert cid_col["foreign_keys"][0]["ref_table"] == "customers"
        assert cid_col["foreign_keys"][0]["ref_column"] == "customer_id"

    def test_row_counts_match_inserted_data(self, sqlite_engine):
        schema = extract_full_schema(sqlite_engine)
        customers = next(t for t in schema["tables"] if t["name"] == "customers")
        orders = next(t for t in schema["tables"] if t["name"] == "orders")
        assert customers["row_count"] == 2
        assert orders["row_count"] == 3

    def test_get_single_table_schema(self, sqlite_engine):
        table = get_single_table_schema(sqlite_engine, "customers")
        assert table["name"] == "customers"
        assert len(table["columns"]) == 3

    def test_get_single_table_raises_for_unknown(self, sqlite_engine):
        with pytest.raises(ValueError, match="not found"):
            get_single_table_schema(sqlite_engine, "does_not_exist")


# ── Relationship Map Tests ─────────────────────────────────────────────────────

class TestRelationshipMap:

    def test_fk_edge_exists(self, sqlite_engine):
        schema = extract_full_schema(sqlite_engine)
        rels = build_relationship_map(schema)
        edge = next(
            (r for r in rels if r["from_table"] == "orders" and r["to_table"] == "customers"),
            None
        )
        assert edge is not None
        assert edge["from_col"] == "customer_id"
        assert edge["to_col"] == "customer_id"

    def test_edge_id_format(self, sqlite_engine):
        schema = extract_full_schema(sqlite_engine)
        for rel in build_relationship_map(schema):
            assert "->" in rel["edge_id"]
            assert rel["from_table"] in rel["edge_id"]

    def test_empty_schema_gives_no_edges(self):
        assert build_relationship_map({"dialect": "sqlite", "tables": []}) == []