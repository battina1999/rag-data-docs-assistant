"""
Test fixtures. Forces the deterministic local provider and an isolated temp
index directory, then builds the index once per session — so the suite runs
fast, free, and without an API key.
"""
import os
import tempfile

# Must be set before app modules import config (settings reads env at import).
os.environ.setdefault("EMBEDDINGS_PROVIDER", "local")
os.environ.setdefault("LLM_PROVIDER", "local")
os.environ["INDEX_DIR"] = tempfile.mkdtemp(prefix="rag_test_index_")

import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def built_index():
    from app.ingest import build_index

    build_index()
    yield
