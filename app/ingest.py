"""
Ingestion: load documentation -> chunk -> embed -> FAISS index, and build the
SQLite catalog. Run with:  python -m app.ingest

The FAISS index is L2-normalized so Euclidean distance maps to cosine
similarity, giving a stable [0,1] relevance score for the retrieval threshold.
"""
from __future__ import annotations

import shutil

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import settings
from app import catalog
from app.providers import active_providers, get_embeddings

DOC_GLOBS = ("*.md", "*.txt", "*.yaml", "*.yml")


def _title_for(path, text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("_", " ").title()


def load_documents() -> list[Document]:
    docs: list[Document] = []
    for pattern in DOC_GLOBS:
        for path in sorted(settings.kb_dir.rglob(pattern)):
            text = path.read_text(encoding="utf-8", errors="ignore")
            if not text.strip():
                continue
            rel = path.relative_to(settings.kb_dir).as_posix()
            docs.append(Document(
                page_content=text,
                metadata={
                    "source": rel,
                    "title": _title_for(path, text),
                    "category": path.parent.name,
                    "doc_type": path.suffix.lstrip("."),
                },
            ))
    return docs


def chunk_documents(docs: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    for i, ch in enumerate(chunks):
        ch.metadata["chunk_id"] = i
    return chunks


def build_index() -> dict:
    settings.ensure_dirs()
    providers = active_providers()
    if providers["embeddings"] == "local":
        print("[ingest] NOTE: no OPENAI_API_KEY -> using local deterministic "
              "embeddings (set your key for production-quality retrieval).")

    docs = load_documents()
    chunks = chunk_documents(docs)
    print(f"[ingest] documents={len(docs)}  chunks={len(chunks)}  "
          f"embeddings={providers['embeddings']}")

    embeddings = get_embeddings()
    vs = FAISS.from_documents(chunks, embeddings, normalize_L2=True)

    if settings.faiss_dir.exists():
        shutil.rmtree(settings.faiss_dir)
    settings.faiss_dir.mkdir(parents=True, exist_ok=True)
    vs.save_local(str(settings.faiss_dir))
    print(f"[ingest] FAISS index saved -> {settings.faiss_dir}")

    cat = catalog.build_catalog()
    print(f"[ingest] catalog built -> tables={cat['tables']} columns={cat['columns']}")

    return {"documents": len(docs), "chunks": len(chunks), **cat,
            "provider": providers["embeddings"]}


if __name__ == "__main__":
    build_index()
