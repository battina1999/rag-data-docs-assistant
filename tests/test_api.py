"""API tests via FastAPI TestClient (no running server, no API key)."""
from fastapi.testclient import TestClient

from app.api import app

client = TestClient(app)


def test_health():
    j = client.get("/health").json()
    assert j["status"] == "ok"
    assert j["index_ready"] is True
    assert j["catalog_tables"] >= 5


def test_ask_in_domain_is_grounded_with_citations():
    j = client.post("/ask", json={"question": "What is the grain of fact_flights?"}).json()
    assert j["grounded"] is True
    assert len(j["citations"]) >= 1


def test_ask_out_of_domain_refuses():
    j = client.post("/ask", json={"question": "who won the 2018 world cup"}).json()
    assert j["grounded"] is False
    assert j["citations"] == []


def test_ask_empty_question_returns_400():
    assert client.post("/ask", json={"question": "   "}).status_code == 400


def test_catalog_endpoints():
    assert client.get("/catalog/table/fact_flights").json()["table"] == "fact_flights"
    assert client.get("/catalog/table/does_not_exist").status_code == 404
