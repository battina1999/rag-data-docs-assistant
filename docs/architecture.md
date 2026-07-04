# Architecture

How the assistant is built, why each choice was made, and the trade-offs —
written to be read on its own by a hiring manager or a teammate.

![Architecture](img/architecture.png)

---

## 1. What it does

It answers natural-language questions about **data documentation** — pipeline
docs, schemas, data dictionaries, and business rules — and returns answers that
are **grounded in the source documents with citations**. When the answer isn't
in the documentation, it **refuses instead of guessing**. It deliberately spans
two domains: the airline platform from Project 1, plus a synthetic e-commerce
company (ShopSphere), so it demonstrates multi-source retrieval.

## 2. Design principles

1. **Grounded or nothing.** Every answer is built only from retrieved context
   and cites its sources. A relevance gate refuses out-of-scope questions
   *before* the LLM is called, which is the single most important property of a
   trustworthy documentation assistant.
2. **OpenAI-powered, but runnable without a key.** OpenAI provides the real
   embeddings and generation. A dependency-free local provider (stable hashing
   embeddings + an extractive LLM) is used automatically when no key is set, so
   the whole system — ingestion, retrieval, API, tests — runs offline and
   deterministically. That is what makes it reviewable.
3. **Semantic + structured.** Free-text retrieval (FAISS) is paired with an
   exact **SQL catalog** (SQLite) for precise table/column/lineage lookups.
4. **Evaluated, not just built.** An eval harness measures answer accuracy,
   refusal accuracy, retrieval hit-rate, and citation coverage.

## 3. Components

### 3.1 Knowledge base (`knowledge_base/`)
Three kinds of documents: **Project 1's real docs** (README, architecture,
Power BI model), **synthetic data-eng docs** (ETL runbook, incident playbook,
metric definitions, DQ/governance rules), and **YAML data dictionaries** for
two warehouses. The default run indexes 9 documents into ~60 chunks.

### 3.2 Ingestion (`app/ingest.py`)
Loads every `.md` / `.txt` / `.yaml` file, attaches metadata (source, title,
category), and splits with a recursive character splitter that prefers markdown
headings as boundaries. Chunks are embedded and written to a **FAISS** index;
the index is **L2-normalized** so Euclidean distance maps to cosine similarity
and yields a stable `[0,1]` relevance score. Ingestion also builds the SQLite
catalog from the YAML dictionaries.

### 3.3 Provider seam (`app/providers.py`)
One interface, two implementations, chosen by `resolve()`:
- **OpenAI** — `text-embedding-3-small` + `gpt-4o-mini` (configurable).
- **local** — `LocalHashingEmbeddings` (deterministic, md5-hashed
  term-frequency vectors; stopword-filtered so retrieval discriminates on
  content words) and `ExtractiveLocalLLM` (returns text drawn only from the
  provided context, never invented).

### 3.4 Retrieval + grounding (`app/retriever.py`, `app/rag.py`)
The retriever converts FAISS's squared-L2 distance to a cosine relevance score.
The RAG layer keeps only chunks at or above the threshold. **If nothing clears
the threshold it returns the fallback without ever calling the LLM** — the
model gets no chance to hallucinate. Otherwise it builds a grounded prompt
(context blocks tagged `[S1] [S2]…`, instruction to answer only from context
and cite tags), runs `prompt | llm | StrOutputParser`, and returns the answer
plus a de-duplicated citation list.

### 3.5 SQL catalog (`app/catalog.py`)
The YAML dictionaries are loaded into a SQLite database (`tables`, `columns`).
This powers exact lookups — "what columns does `fact_flights` have?", "which
tables mention `customer`?" — that semantic search shouldn't be trusted with.

### 3.6 API + UI (`app/api.py`, `ui/index.html`)
FastAPI exposes `POST /ask`, `GET /health`, and `GET /catalog/*`, with
auto-generated OpenAPI docs at `/docs`. A single-file chat UI (for technical and
business users) shows the answer, a grounded/not-in-docs badge, the active
provider, and the cited sources with match scores.

### 3.7 Evaluation (`eval/`)
A labeled question set drives four metrics: **answer accuracy** (answers the
answerable), **refusal accuracy** (refuses the out-of-scope — the
anti-hallucination metric), **retrieval hit-rate** (expected source retrieved),
and **citation coverage**. On the local provider it scores 100% answer / 100%
refusal / 100% citation with a lower retrieval hit-rate; OpenAI embeddings lift
retrieval further.

## 4. Design decisions & trade-offs

| Decision | Why |
|---|---|
| Relevance gate refuses before the LLM | Prevents hallucination at the source, not by post-hoc filtering. |
| OpenAI default, local fallback | Real quality with a key; still runnable and testable without one. |
| FAISS + SQLite (semantic + exact) | Embeddings for meaning, SQL for precise schema facts. |
| Normalized index + cosine score | Gives an interpretable `[0,1]` threshold that works across providers. |
| Deterministic local provider | Fast, free, reproducible CI; no network in tests. |

## 5. How it connects to Project 1

The airline platform (Project 1) produces the documentation this assistant
consumes. Together they tell one story: **build a governed data platform, then
put a grounded AI layer on top of its knowledge.** The two projects are
intentionally linked rather than standalone.

## 6. Scaling this up

- Swap `RecursiveCharacterTextSplitter` for structure-aware chunking and add
  metadata filters (per warehouse / doc type).
- Move FAISS to a managed vector DB (pgvector / Pinecone) for larger corpora.
- Add a reranker and hybrid (BM25 + vector) retrieval to raise hit-rate.
- Log queries + feedback and expand the eval set into a regression gate in CI.
- Stream responses and add per-user auth on the API.
