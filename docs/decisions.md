# Decision Records

**1. Refuse BEFORE calling the LLM.** If retrieval can't clear the relevance
gate, the model is never invoked — hallucination is prevented structurally,
not filtered after the fact. It also costs nothing to refuse.

**2. Two-signal gate: semantic + lexical.** Expanding the eval set to 30
vocabulary-adjacent traps ("airline baggage fees", "SQL string reversal")
exposed similarity-only gating at 40% refusal. Requiring both a vector
relevance threshold AND query-term coverage in the retrieved context restored
93% refusal while keeping 89% answer accuracy. One signal per failure mode.

**3. Hybrid retrieval with RRF, but the gate stays vector-only.** BM25 scores
are query-relative (no absolute meaning), so they influence *ranking* only.
The refusal decision keeps the interpretable [0,1] cosine threshold —
hybrid recall can never weaken safety. Hit-rate 84% → 95%.

**4. Provider seam (OpenAI default, deterministic local fallback).** The whole
system — ingestion, retrieval, API, 10 tests, 102-question eval — runs without
an API key, so anyone can verify it. With a key, quality upgrades in place.
The local LLM is extractive-only: it can echo context, never invent.

**5. FAISS + SQLite together.** Embeddings answer fuzzy semantic questions;
exact schema questions ("what columns does fact_flights have?") deserve exact
answers from a SQL catalog, not nearest-neighbour guesses.

**6. Eval as a first-class artifact.** Answer accuracy, refusal accuracy,
retrieval hit-rate and citation coverage are measured on a labeled set and
reported in the README as a benchmark table (vector vs hybrid). Claims about
the assistant are numbers, not adjectives.

**7. The knowledge base is the real platform's documentation.** The assistant
answers questions about an actual running system (the airline data platform's
KPIs, model card, data profile) — so the demo is verifiable against the
source repo, and the two projects reinforce each other.
