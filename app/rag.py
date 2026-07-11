"""
The RAG chain: retrieve -> ground -> answer with citations.

Grounding rules that make this more than a toy:
  * The prompt instructs the model to answer ONLY from the provided context and
    to cite sources with [S#] tags.
  * If no retrieved chunk clears the relevance threshold, we short-circuit to a
    safe fallback ("not in the documentation") WITHOUT calling the LLM, so the
    model is never given the chance to hallucinate an answer.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from config import settings
from app.providers import NOT_FOUND_MESSAGE as FALLBACK, active_providers, get_llm
from app.retriever import Hit, get_retriever

PROMPT = PromptTemplate.from_template(
    """You are a data documentation assistant for a data engineering team.
Answer the user's QUESTION using ONLY the CONTEXT below. Cite the sources you
use with their [S#] tags. If the answer is not in the context, reply exactly:
"{fallback}" Do not invent tables, columns, metrics, or values.

Context:
{context}

Question: {question}

Answer (grounded, cite sources as [S#]):"""
)


@dataclass
class Citation:
    tag: str
    source: str
    title: str
    score: float
    snippet: str


@dataclass
class Answer:
    question: str
    answer: str
    grounded: bool
    provider: str
    citations: list

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


class RAGAssistant:
    def __init__(self):
        self.retriever = get_retriever()
        self.llm = get_llm()

    def _format_context(self, hits: list[Hit]) -> tuple[str, list[Citation]]:
        blocks, citations = [], []
        for i, h in enumerate(hits, start=1):
            tag = f"S{i}"
            blocks.append(f"[{tag}] (source: {h.source} — {h.title})\n{h.text}")
            citations.append(Citation(
                tag=tag, source=h.source, title=h.title, score=h.score,
                snippet=" ".join(h.text.split())[:200],
            ))
        return "\n\n".join(blocks), citations

    @staticmethod
    def _coverage(question: str, hits) -> float:
        """Best share of the question's content tokens found in any hit."""
        from app.providers import _tokens

        q = set(_tokens(question))
        if not q:
            return 0.0
        return max((len(q & set(_tokens(h.text))) / len(q) for h in hits), default=0.0)

    def answer(self, question: str) -> Answer:
        provider = active_providers()["llm"]
        hits = self.retriever.search(question)
        kept = [h for h in hits if h.score >= settings.relevance_threshold]

        # Two-signal anti-hallucination gate:
        #  1) semantic: best vector relevance >= threshold
        #  2) lexical : enough of the question's content words actually appear
        #     in the retrieved context (kills vocabulary-adjacent traps like
        #     "airline baggage fees" that embeddings alone score too high)
        if kept and self._coverage(question, kept) < settings.coverage_threshold:
            kept = []

        if not kept:
            return Answer(question=question, answer=FALLBACK, grounded=False,
                          provider=provider, citations=[])

        context, citations = self._format_context(kept)
        chain = PROMPT | self.llm | StrOutputParser()
        text = chain.invoke({"context": context, "question": question,
                             "fallback": FALLBACK}).strip()

        grounded = text.strip() != FALLBACK
        return Answer(
            question=question, answer=text, grounded=grounded, provider=provider,
            citations=[c.__dict__ for c in (citations if grounded else [])],
        )


_assistant: RAGAssistant | None = None


def get_assistant() -> RAGAssistant:
    global _assistant
    if _assistant is None:
        _assistant = RAGAssistant()
    return _assistant
