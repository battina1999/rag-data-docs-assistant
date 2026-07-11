"""
Hybrid retrieval: FAISS vector search + BM25 lexical search, merged with
Reciprocal Rank Fusion (RRF).

Design that keeps refusals safe:
  * The ANTI-HALLUCINATION GATE stays on the absolute vector cosine score
    (interpretable [0,1] threshold). BM25 scores are query-relative, so they
    are used ONLY to improve ranking/recall of the context — never to decide
    whether the docs contain an answer. Refusal accuracy is unaffected.
  * RETRIEVAL_MODE=vector|hybrid (default hybrid) allows A/B benchmarking;
    eval/evaluate.py reports both.
"""
from __future__ import annotations

import os
import pickle
from dataclasses import dataclass

from langchain_community.vectorstores import FAISS

from config import settings
from app.providers import get_embeddings

RRF_K = 60  # standard reciprocal-rank-fusion constant


def retrieval_mode() -> str:
    return os.environ.get("RETRIEVAL_MODE", "hybrid").lower()


@dataclass
class Hit:
    source: str
    title: str
    text: str
    score: float          # vector cosine when known; bm25-only hits carry the
                          # min kept vector score (display only, gate unaffected)
    via: str = "vector"   # vector | bm25 | both


class Retriever:
    def __init__(self):
        self._vs = None
        self._bm25 = None

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

    @property
    def bm25(self):
        if self._bm25 is None:
            path = settings.index_dir / "bm25.pkl"
            if path.exists():
                with open(path, "rb") as fh:
                    self._bm25 = pickle.load(fh)
            else:
                self._bm25 = {}
        return self._bm25

    # ------------------------------------------------------------------ #
    def _vector_hits(self, query: str, k: int) -> list[Hit]:
        results = self.vs.similarity_search_with_score(query, k=k)
        hits = []
        for doc, sq_l2 in results:
            relevance = max(0.0, min(1.0, 1.0 - float(sq_l2) / 2.0))
            hits.append(Hit(
                source=doc.metadata.get("source", "?"),
                title=doc.metadata.get("title", "?"),
                text=doc.page_content,
                score=round(relevance, 4),
                via="vector",
            ))
        return hits

    def _bm25_hits(self, query: str, k: int) -> list[Hit]:
        from app.providers import _tokens

        idx = self.bm25
        if not idx:
            return []
        scores = idx["bm25"].get_scores(_tokens(query))
        order = sorted(range(len(scores)), key=lambda i: -scores[i])[:k]
        hits = []
        for i in order:
            if scores[i] <= 0:
                continue
            md = idx["metadatas"][i]
            hits.append(Hit(
                source=md.get("source", "?"), title=md.get("title", "?"),
                text=idx["texts"][i], score=0.0, via="bm25",
            ))
        return hits

    def search(self, query: str, k: int | None = None) -> list[Hit]:
        """Return ranked hits. hits[0].score is ALWAYS the best vector cosine,
        so the caller's threshold gate keeps its absolute meaning."""
        k = k or settings.top_k
        vector = self._vector_hits(query, k)
        if retrieval_mode() != "hybrid":
            return vector

        lexical = self._bm25_hits(query, k)

        # RRF merge on (source, first 80 chars) identity
        def key(h: Hit):
            return (h.source, h.text[:80])

        ranks: dict = {}
        for lst in (vector, lexical):
            for r, h in enumerate(lst):
                ranks.setdefault(key(h), {"hit": h, "rrf": 0.0, "vias": set()})
                ranks[key(h)]["rrf"] += 1.0 / (RRF_K + r + 1)
                ranks[key(h)]["vias"].add(h.via)

        vec_scores = {key(h): h.score for h in vector}
        floor = min((h.score for h in vector), default=0.0)
        merged = []
        for entry in sorted(ranks.values(), key=lambda e: -e["rrf"]):
            h = entry["hit"]
            h.via = "both" if len(entry["vias"]) > 1 else next(iter(entry["vias"]))
            h.score = vec_scores.get(key(h), round(floor, 4))
            merged.append(h)

        gate = max((h.score for h in vector), default=0.0)
        merged = merged[:k]
        # guarantee hits[0].score carries the gate value for the caller
        if merged and merged[0].score < gate:
            best = max(vector, key=lambda h: h.score)
            merged = [best] + [h for h in merged if key(h) != key(best)][:k - 1]
        return merged


_retriever: Retriever | None = None


def get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever
