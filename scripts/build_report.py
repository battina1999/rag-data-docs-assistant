"""
Generate the project report PDF (docs/RAG_Assistant_Report.pdf):
what was built, the architecture, design decisions, evaluation, and an
interview-prep Q&A.  Usage:  python scripts/build_report.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable, Image, ListFlowable, ListItem, PageBreak, Paragraph,
    SimpleDocTemplate, Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "docs" / "img"
OUT = ROOT / "docs" / "RAG_Assistant_Report.pdf"

NAVY = colors.HexColor("#1f3b5c")
TEAL = colors.HexColor("#2a9d8f")
LIGHT = colors.HexColor("#eef2f7")
GREY = colors.HexColor("#475569")

styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=styles["Heading1"], textColor=NAVY, fontSize=17, spaceBefore=14, spaceAfter=8)
BODY = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10.5, leading=15, alignment=TA_JUSTIFY, spaceAfter=6)
BULLET = ParagraphStyle("Bullet", parent=BODY, alignment=TA_LEFT, spaceAfter=3)
SMALL = ParagraphStyle("Small", parent=styles["Normal"], fontSize=9, textColor=GREY)
QSTYLE = ParagraphStyle("Q", parent=BODY, alignment=TA_LEFT, textColor=NAVY, fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=2)


def img(path: Path, width_in: float):
    from PIL import Image as PILImage
    w, h = PILImage.open(path).size
    width = width_in * inch
    return Image(str(path), width=width, height=width * h / w)


def bullets(items):
    return ListFlowable([ListItem(Paragraph(t, BULLET), leftIndent=8, value="•") for t in items],
                        bulletType="bullet", start="•", leftIndent=12)


def kv_table(rows, col_widths):
    t = Table(rows, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("LEFTPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t


def qa(s, q, a):
    s.append(Paragraph("Q. " + q, QSTYLE))
    s.append(Paragraph("A. " + a, BODY))


def build():
    doc = SimpleDocTemplate(str(OUT), pagesize=LETTER, topMargin=0.7 * inch, bottomMargin=0.7 * inch,
                            leftMargin=0.85 * inch, rightMargin=0.85 * inch,
                            title="RAG Data Documentation Assistant - Report", author="Dhanush Battina")
    s = []
    s.append(Spacer(1, 1.2 * inch))
    s.append(Paragraph("RAG-Based Data<br/>Documentation Assistant",
                       ParagraphStyle("T", parent=styles["Title"], textColor=NAVY, fontSize=26, leading=32, alignment=TA_CENTER)))
    s.append(Spacer(1, 12))
    s.append(Paragraph("Data / AI Engineering Portfolio — Project Report",
                       ParagraphStyle("ST", parent=styles["Normal"], fontSize=13, textColor=TEAL, alignment=TA_CENTER)))
    s.append(Spacer(1, 22))
    s.append(HRFlowable(width="60%", thickness=1.2, color=colors.HexColor("#cbd5e1")))
    s.append(Spacer(1, 16))
    s.append(Paragraph("A retrieval-augmented assistant that answers questions about data "
                       "documentation with cited, grounded answers — and refuses to guess when the "
                       "answer isn't documented.",
                       ParagraphStyle("cap", parent=BODY, alignment=TA_CENTER, textColor=GREY)))
    s.append(Spacer(1, 22))
    s.append(img(IMG / "architecture.png", 6.5))
    s.append(Spacer(1, 16))
    s.append(Paragraph("Python · LangChain · FAISS · OpenAI API · FastAPI · SQLite · Docker",
                       ParagraphStyle("stk", parent=SMALL, alignment=TA_CENTER)))
    s.append(Paragraph("Author: Dhanush Battina", ParagraphStyle("au", parent=SMALL, alignment=TA_CENTER)))
    s.append(PageBreak())

    s.append(Paragraph("1. Executive summary", H1))
    s.append(Paragraph(
        "This project is a retrieval-augmented generation (RAG) assistant for data "
        "documentation. It ingests pipeline docs, schemas, data dictionaries and "
        "business rules, indexes them for semantic search, and answers natural-language "
        "questions with answers that are <b>grounded in the source documents and cited</b>. "
        "Critically, it <b>refuses to answer</b> when the documentation doesn't cover the "
        "question — the anti-hallucination behaviour that separates a trustworthy assistant "
        "from a demo.", BODY))
    s.append(Paragraph(
        "It is OpenAI-powered, and engineered with a provider seam so the whole system — "
        "ingestion, retrieval, API and tests — also runs offline and deterministically "
        "without an API key. It intentionally consumes the documentation from Project 1 "
        "(the airline data platform), linking the two projects into one story.", BODY))

    s.append(Paragraph("2. What I built", H1))
    s.append(bullets([
        "<b>Ingestion pipeline (LangChain):</b> load → chunk with metadata → embed → "
        "persist a FAISS vector index; plus a SQLite data catalog for exact lookups.",
        "<b>Grounded RAG chain:</b> relevance-scored retrieval, a context-only prompt with "
        "[S#] citations, and a threshold gate that returns a safe fallback without calling the LLM.",
        "<b>Provider seam:</b> OpenAI embeddings + GPT by default; a deterministic local "
        "provider (hashing embeddings + extractive LLM) when no key is present.",
        "<b>FastAPI service + chat UI:</b> /ask, /health, /catalog/* endpoints, OpenAPI docs, "
        "and a simple UI for technical and business users.",
        "<b>Evaluation harness:</b> answer accuracy, refusal accuracy, retrieval hit-rate and "
        "citation coverage on a labeled question set.",
    ]))

    s.append(Paragraph("3. Architecture", H1))
    s.append(Paragraph(
        "Two phases. <b>Ingestion</b> turns documents into a normalized FAISS index and a SQL "
        "catalog. <b>Query</b> retrieves the most relevant chunks, gates them by a cosine "
        "relevance threshold, and — only if context clears the bar — asks the LLM to answer "
        "strictly from that context with citations. Below the bar, it returns the fallback and "
        "never calls the model.", BODY))

    s.append(Paragraph("4. Design decisions &amp; trade-offs", H1))
    s.append(kv_table([
        ["Decision", "Why"],
        ["Refuse before calling the LLM", "Stops hallucination at the source, not with post-hoc filtering."],
        ["OpenAI default + local fallback", "Real quality with a key; still runnable and testable without one."],
        ["FAISS + SQLite together", "Embeddings for meaning; SQL for exact schema/lineage facts."],
        ["Normalized index, cosine score", "Interpretable [0,1] threshold that works across providers."],
        ["Evaluation harness", "Treats answer quality + refusal as measurable, not vibes."],
    ], [2.2 * inch, 4.0 * inch]))

    s.append(Paragraph("5. Evaluation results", H1))
    s.append(Paragraph("On the labeled eval set with the local provider:", BODY))
    s.append(kv_table([
        ["Metric", "Result", "Meaning"],
        ["Answer accuracy", "100%", "answers the questions it should"],
        ["Refusal accuracy", "100%", "refuses out-of-scope questions (no hallucination)"],
        ["Citation coverage", "100%", "grounded answers carry a citation"],
        ["Retrieval hit-rate", "75%", "expected source retrieved (higher with OpenAI)"],
    ], [1.7 * inch, 0.9 * inch, 3.6 * inch]))

    s.append(Paragraph("6. What this project teaches (skills to speak to)", H1))
    s.append(bullets([
        "How RAG works end to end: chunking, embeddings, vector search, grounded generation.",
        "Preventing hallucination with a retrieval-relevance gate and source-cited prompting.",
        "Combining semantic retrieval with a structured SQL catalog.",
        "Designing a provider abstraction so an LLM app is testable and reproducible.",
        "Serving an ML app behind a real API (FastAPI) and containerizing it.",
        "Evaluating an LLM system with objective metrics instead of anecdotes.",
    ]))

    s.append(PageBreak())
    s.append(Paragraph("7. Interview talking points (Q &amp; A)", H1))
    qa(s, "What is RAG and why use it here?",
       "Retrieval-Augmented Generation grounds an LLM in your own documents: you retrieve the "
       "most relevant chunks and pass them as context so the model answers from facts rather than "
       "its parameters. It's ideal for documentation Q&A because answers must be current, "
       "specific, and cite a source.")
    qa(s, "How do you stop it from hallucinating?",
       "Three layers: I retrieve with a cosine relevance score and drop anything below a "
       "threshold; if nothing clears the bar I return a fallback and never call the LLM; and when "
       "I do call it, the prompt instructs it to answer only from the provided context and cite "
       "[S#] tags. The eval set measures refusal accuracy explicitly.")
    qa(s, "Walk me through retrieval.",
       "Documents are chunked with metadata and embedded into a FAISS index that I L2-normalize, "
       "so Euclidean distance maps to cosine similarity. At query time I embed the question, take "
       "the top-k, and convert distance to a [0,1] relevance score for the threshold gate.")
    qa(s, "Why FAISS and SQLite together?",
       "FAISS answers fuzzy, semantic questions ('how are delays defined?'). SQLite answers exact "
       "structural ones ('what columns does fact_flights have?') that you shouldn't trust to "
       "embeddings. Pairing them covers both question types accurately.")
    qa(s, "How do you evaluate a RAG system?",
       "With a labeled set and four metrics: answer accuracy, refusal accuracy (the "
       "anti-hallucination signal), retrieval hit-rate (was the right source retrieved), and "
       "citation coverage. That turns 'it feels good' into numbers you can regress in CI.")
    qa(s, "It's OpenAI-powered — how does it run without a key?",
       "A provider seam. Embeddings and generation go through one interface with an OpenAI "
       "implementation and a deterministic local one (hashing embeddings + an extractive LLM). "
       "With no key it auto-selects local, so ingestion, the API and the whole test suite run "
       "offline; with a key it uses OpenAI for real quality.")
    qa(s, "How would you improve retrieval quality?",
       "Hybrid retrieval (BM25 + vector) plus a cross-encoder reranker, structure-aware chunking, "
       "and metadata filters per warehouse/doc-type. I'd also grow the eval set and track hit-rate "
       "as a regression metric.")
    qa(s, "Cost and latency considerations?",
       "Embeddings are computed once at ingestion; only the query embedding + one generation call "
       "happen per request. Caching, a smaller/cheaper chat model, and streaming keep cost and "
       "perceived latency down; the relevance gate also avoids paying for generation on "
       "out-of-scope questions.")

    s.append(Paragraph("8. How to run it", H1))
    s.append(Paragraph("<b>make setup</b> → install · <b>make ingest</b> → build index + catalog · "
                       "<b>make serve</b> → FastAPI + chat UI · <b>make eval</b> → metrics · "
                       "<b>make test</b> → suite (no key needed). Set OPENAI_API_KEY in .env for "
                       "real answers; otherwise the local provider is used automatically.", BODY))

    s.append(Paragraph("9. Putting it on your resume &amp; LinkedIn", H1))
    s.append(Paragraph("<b>Resume bullet:</b> Built a retrieval-augmented documentation assistant "
                       "(Python, LangChain, FAISS, OpenAI, FastAPI, Docker) with source-cited, "
                       "grounded answers, a relevance-gated anti-hallucination fallback, a SQL data "
                       "catalog, and an evaluation harness (100% refusal accuracy on the eval set).", BODY))
    s.append(Paragraph("<b>LinkedIn line:</b> Shipped a grounded RAG assistant over data "
                       "documentation — LangChain + FAISS retrieval, cited answers, an "
                       "anti-hallucination gate, a FastAPI service, and objective evaluation. "
                       "OpenAI-powered, runnable offline.", BODY))

    doc.build(s)
    print(f"wrote {OUT}  ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    build()
