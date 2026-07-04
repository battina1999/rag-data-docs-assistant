"""
Embedding + LLM providers behind one interface.

Primary provider is **OpenAI** (embeddings + chat). A dependency-free **local**
provider is used automatically when no OPENAI_API_KEY is present, so the whole
pipeline — ingestion, retrieval, citations, API, tests — runs offline and
deterministically. Real, high-quality answers come from OpenAI once a key is set.

  EMBEDDINGS_PROVIDER / LLM_PROVIDER = auto | openai | local
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import Any, List, Optional

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.llms import LLM

from config import settings

# Canonical "not in the docs" reply, shared by the RAG layer and the offline LLM
# so grounding detection is consistent across providers.
NOT_FOUND_MESSAGE = (
    "I couldn't find this in the documentation. Try rephrasing, or ask the data "
    "platform owners listed in the governance docs."
)

_TOKEN_RE = re.compile(r"[a-z0-9_]+")

# Dropping generic stopwords makes the local hashing embedding discriminate on
# content words only, so the retrieval relevance score cleanly separates
# in-domain questions from out-of-domain ones (the anti-hallucination gate).
_STOPWORDS = {
    "the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "is", "are",
    "was", "were", "be", "been", "it", "its", "this", "that", "these", "those",
    "as", "at", "by", "with", "from", "into", "how", "what", "which", "who",
    "whom", "when", "where", "why", "do", "does", "did", "can", "could", "will",
    "would", "should", "i", "you", "we", "they", "he", "she", "there", "here",
    "about", "if", "then", "than", "so", "such", "not", "no", "yes", "me", "my",
    "our", "your", "their", "us", "have", "has", "had", "but", "also", "any",
}


def _tokens(text: str) -> List[str]:
    return [t for t in _TOKEN_RE.findall(text.lower())
            if t not in _STOPWORDS and len(t) > 1]


class LocalHashingEmbeddings(Embeddings):
    """Deterministic term-frequency hashing embedding (offline stand-in).

    Uses a stable md5-based hash (NOT Python's salted hash) so an index built
    in one process matches queries in another. Vectors are L2-normalized, so
    Euclidean distance in FAISS corresponds to cosine similarity — good enough
    for lexical retrieval in tests without any model download.
    """

    def __init__(self, dim: int = 512):
        self.dim = dim

    def _embed(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        for tok in _tokens(text):
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16) % self.dim
            vec[h] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed(text)


class ExtractiveLocalLLM(LLM):
    """Offline LLM stand-in.

    Produces a deterministic, grounded-looking answer by extracting the first
    couple of sentences of the top retrieved context block from the prompt.
    Never invents facts (it only echoes provided context), which keeps offline
    behaviour honest. Real reasoning/synthesis comes from OpenAI.
    """

    @property
    def _llm_type(self) -> str:
        return "extractive-local"

    def _call(self, prompt: str, stop: Optional[List[str]] = None,
              run_manager: Any = None, **kwargs: Any) -> str:
        # pull the context section written by the RAG prompt builder
        ctx = ""
        if "Context:" in prompt and "Question:" in prompt:
            ctx = prompt.split("Context:", 1)[1].split("Question:", 1)[0]
        # strip [S#] header lines + markdown/yaml noise across the whole context
        clean = []
        for ln in ctx.splitlines():
            s = ln.strip()
            if not s or s.startswith("[S") or s.startswith("#"):
                continue
            clean.append(s.lstrip("-*>| ").strip())
        body = " ".join(clean).strip()
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", body) if len(s) > 20]
        snippet = " ".join(sentences[:2]).strip() or body[:240]
        if not snippet:
            return NOT_FOUND_MESSAGE
        return f"Based on the documentation [S1]: {snippet}"

    @property
    def _identifying_params(self) -> dict:
        return {"provider": "local"}


def get_embeddings() -> Embeddings:
    if settings.resolve("embeddings") == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=settings.openai_embed_model,
                                api_key=settings.openai_api_key)
    return LocalHashingEmbeddings(dim=settings.local_embed_dim)


def get_llm() -> LLM:
    if settings.resolve("llm") == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=settings.openai_chat_model, temperature=0,
                          api_key=settings.openai_api_key)
    return ExtractiveLocalLLM()


def active_providers() -> dict:
    return {"embeddings": settings.resolve("embeddings"), "llm": settings.resolve("llm")}
