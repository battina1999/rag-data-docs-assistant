"""
Retrieval over the FAISS index.

Converts FAISS's squared-L2 distance (on L2-normalized vectors) into a cosine
relevance score in [0, 1], which the RAG layer thresholds to decide whether the
documentation actually contains an answer (the anti-hallucination gate).
"""
from __future__ import annotations

from dataclasses import dataclass

from langchain_community.vectorstores import FAISS

from config import settings
from app.providers import get_embeddings


@dataclass
class Hit:
    source: str
    title: str
    text: str
    score: float  # cosine relevance in [0, 1]


class Retriever:
    def __init__(self):
        self._vs = None

    @property
    def vs(self) -> FAISS:
        if self._vs is None:
            if not (settings.faiss_dir / "index.faiss").exists():
                raise FileNotFoundError(
                    f"No index at {settings.faiss_dir}. Run `python -m app.ingest` first."
                )
            self._vs = FAISS.load_local(
                str(settings.faiss_dir), get_embeddings(),
                allow_dangerous_deserialization=True,
            )
        return self._vs

    def search(self, query: str, k: int | None = None) -> list[Hit]:
        k = k or settings.top_k
        results = self.vs.similarity_search_with_score(query, k=k)
        hits = []
        for doc, sq_l2 in results:
            # squared-L2 on normalized vectors -> cosine = 1 - d^2/2
            relevance = max(0.0, min(1.0, 1.0 - float(sq_l2) / 2.0))
            hits.append(Hit(
                source=doc.metadata.get("source", "?"),
                title=doc.metadata.get("title", "?"),
                text=doc.page_content,
                score=round(relevance, 4),
            ))
        return hits


_retriever: Retriever | None = None


def get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever
