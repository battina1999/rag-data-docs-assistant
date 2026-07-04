"""
FastAPI service for the RAG documentation assistant.

Endpoints
    GET  /              -> chat UI (technical + business users)
    GET  /health        -> provider + index status
    POST /ask           -> grounded answer with citations
    GET  /catalog/tables            -> list catalogued tables
    GET  /catalog/table/{name}      -> table + columns + lineage
    GET  /catalog/search?term=...   -> column search (SQL catalog)
Interactive OpenAPI docs at /docs.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from config import PROJECT_ROOT, settings
from app import catalog
from app.providers import active_providers
from app.schemas import AskRequest, AskResponse, Health

app = FastAPI(
    title="RAG Data Documentation Assistant",
    version="1.0.0",
    description="Ask natural-language questions about data pipeline documentation, "
                "schemas, data dictionaries and business rules. Answers are grounded "
                "in the docs with citations, and fall back safely when the answer "
                "isn't documented.",
)

UI_FILE = PROJECT_ROOT / "ui" / "index.html"


def _index_ready() -> bool:
    return (settings.faiss_dir / "index.faiss").exists()


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home() -> str:
    if UI_FILE.exists():
        return UI_FILE.read_text(encoding="utf-8")
    return "<h1>RAG Data Documentation Assistant</h1><p>See <a href='/docs'>/docs</a>.</p>"


@app.get("/health", response_model=Health)
def health() -> Health:
    return Health(
        status="ok",
        providers=active_providers(),
        index_ready=_index_ready(),
        catalog_tables=len(catalog.list_tables()),
    )


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> dict:
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")
    if not _index_ready():
        raise HTTPException(status_code=503,
                            detail="Index not built. Run `python -m app.ingest` first.")
    from app.rag import get_assistant  # lazy: avoids loading the index at import

    return get_assistant().answer(question).to_dict()


@app.get("/catalog/tables")
def catalog_tables() -> list:
    return catalog.list_tables()


@app.get("/catalog/table/{name}")
def catalog_table(name: str) -> dict:
    table = catalog.get_table(name)
    if not table:
        raise HTTPException(status_code=404, detail=f"table '{name}' not found")
    return table


@app.get("/catalog/search")
def catalog_search(term: str) -> list:
    return catalog.search_columns(term)
