"""Central configuration for the RAG documentation assistant."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _get(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    # --- provider selection ---
    openai_api_key: str = field(default_factory=lambda: _get("OPENAI_API_KEY", "").strip())
    embeddings_provider: str = field(default_factory=lambda: _get("EMBEDDINGS_PROVIDER", "auto").lower())
    llm_provider: str = field(default_factory=lambda: _get("LLM_PROVIDER", "auto").lower())
    openai_embed_model: str = field(default_factory=lambda: _get("OPENAI_EMBED_MODEL", "text-embedding-3-small"))
    openai_chat_model: str = field(default_factory=lambda: _get("OPENAI_CHAT_MODEL", "gpt-4o-mini"))
    local_embed_dim: int = 512

    # --- chunking / retrieval ---
    chunk_size: int = field(default_factory=lambda: int(_get("CHUNK_SIZE", "800")))
    chunk_overlap: int = field(default_factory=lambda: int(_get("CHUNK_OVERLAP", "120")))
    top_k: int = field(default_factory=lambda: int(_get("TOP_K", "4")))
    relevance_threshold: float = field(default_factory=lambda: float(_get("RELEVANCE_THRESHOLD", "0.15")))
    # 2nd anti-hallucination gate: minimum share of the question's content
    # words that must appear in some retrieved chunk (lexical evidence guard;
    # tuned on the 30-trap eval set: refusal 40% -> 93% on local embeddings)
    coverage_threshold: float = field(default_factory=lambda: float(_get("COVERAGE_THRESHOLD", "0.4")))

    # --- paths ---
    kb_dir: Path = PROJECT_ROOT / "knowledge_base"
    index_dir: Path = field(
        default_factory=lambda: Path(_get("INDEX_DIR", str(PROJECT_ROOT / "index")))
    )

    @property
    def faiss_dir(self) -> Path:
        return self.index_dir / "faiss"

    @property
    def catalog_db(self) -> Path:
        return self.index_dir / "catalog.sqlite"

    def resolve(self, kind: str) -> str:
        """Return the effective provider ('openai' or 'local') for embeddings/llm."""
        explicit = self.embeddings_provider if kind == "embeddings" else self.llm_provider
        if explicit in ("openai", "local"):
            return explicit
        return "openai" if self.openai_api_key else "local"

    def ensure_dirs(self) -> None:
        self.index_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
