"""Ingestion, retrieval-threshold, and catalog tests (local provider)."""
from config import settings
from app import catalog
from app.retriever import get_retriever


def test_index_is_built():
    assert (settings.faiss_dir / "index.faiss").exists()


def test_in_domain_query_scores_above_threshold():
    hits = get_retriever().search("grain of the fact_flights table")
    assert hits
    assert hits[0].score >= settings.relevance_threshold


def test_out_of_domain_query_scores_below_threshold():
    hits = get_retriever().search("who won the 2018 world cup")
    assert hits[0].score < settings.relevance_threshold


def test_catalog_table_lookup():
    table = catalog.get_table("fact_flights")
    assert table is not None
    assert len(table["columns"]) >= 5
    assert any("delay" in c["name"] for c in table["columns"])


def test_catalog_column_search():
    rows = catalog.search_columns("customer")
    assert any(r["table"] == "dim_customer" for r in rows)
