"""
Evaluation harness for the RAG assistant.

Measures the things that separate a trustworthy assistant from a demo:
  * Refusal accuracy   - does it correctly say "not in the docs" for
                         out-of-scope questions? (anti-hallucination)
  * Answer accuracy    - does it answer the questions it should?
  * Retrieval hit-rate - is the expected source document retrieved?
  * Citation coverage  - do grounded answers carry at least one citation?

    python -m eval.evaluate                          # report (current mode)
    python -m eval.evaluate --retrieval vector       # force vector-only
    python -m eval.evaluate --retrieval hybrid       # force BM25+vector
    python -m eval.evaluate --compare                # benchmark table (runs both)
    python -m eval.evaluate --strict                 # non-zero exit if refusal/answer < 100%

Run with OPENAI_API_KEY set for production-quality numbers; it also runs on the
local provider (retrieval hit-rate will be lower, refusal/answer stay meaningful).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import yaml

from config import PROJECT_ROOT
from app.providers import active_providers

EVAL_FILE = Path(__file__).resolve().parent / "eval_questions.yaml"
RESULTS_DIR = Path(__file__).resolve().parent / "results"


def run(strict: bool = False, quiet: bool = False) -> dict:
    # import here so RETRIEVAL_MODE set by --retrieval/--compare is respected
    from app.rag import get_assistant
    from app.retriever import get_retriever, retrieval_mode

    cases = yaml.safe_load(EVAL_FILE.read_text())
    assistant = get_assistant()
    retriever = get_retriever()
    providers = active_providers()

    rows = []
    answer_ok = answer_total = 0
    refuse_ok = refuse_total = 0
    retr_hit = retr_total = 0
    cite_ok = cite_total = 0

    for c in cases:
        q = c["question"]
        should = c["should_answer"]
        res = assistant.answer(q)
        hits = retriever.search(q)
        hit_sources = [h.source for h in hits]

        if should:
            answer_total += 1
            answered = res.grounded
            answer_ok += int(answered)
            if c.get("expected_source"):
                retr_total += 1
                hit = any(c["expected_source"] in s for s in hit_sources)
                retr_hit += int(hit)
            if res.grounded:
                cite_total += 1
                cite_ok += int(len(res.citations) > 0)
            verdict = "OK" if answered else "MISS(no answer)"
        else:
            refuse_total += 1
            refused = not res.grounded
            refuse_ok += int(refused)
            verdict = "OK" if refused else "MISS(hallucinated)"

        rows.append((q[:46], "answer" if should else "refuse", verdict))

    def pct(a, b):
        return f"{(100.0 * a / b if b else 0):.0f}%"

    summary = {
        "mode": retrieval_mode(),
        "answer_accuracy": [answer_ok, answer_total],
        "refusal_accuracy": [refuse_ok, refuse_total],
        "retrieval_hit_rate": [retr_hit, retr_total],
        "citation_coverage": [cite_ok, cite_total],
    }
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / f"results_{retrieval_mode()}.json").write_text(json.dumps(summary, indent=2))

    if not quiet:
        print(f"\nEvaluation  (retrieval={retrieval_mode()}, llm={providers['llm']}, "
              f"embeddings={providers['embeddings']})")
        print("-" * 72)
        for q, kind, verdict in rows:
            if "MISS" in verdict:
                print(f"  [{kind}] {q:<48} {verdict}")
        print("-" * 72)
        print(f"  Answer accuracy   : {pct(answer_ok, answer_total)}  ({answer_ok}/{answer_total})")
        print(f"  Refusal accuracy  : {pct(refuse_ok, refuse_total)}  ({refuse_ok}/{refuse_total})")
        print(f"  Retrieval hit-rate: {pct(retr_hit, retr_total)}  ({retr_hit}/{retr_total})")
        print(f"  Citation coverage : {pct(cite_ok, cite_total)}  ({cite_ok}/{cite_total})")

    summary["critical_ok"] = (answer_ok == answer_total) and (refuse_ok == refuse_total)
    if strict and not summary["critical_ok"]:
        print("\nstrict: answer/refusal accuracy below 100% -> failing")
        sys.exit(1)
    return summary


def compare() -> None:
    """Benchmark vector-only vs hybrid and print the README table."""
    results = {}
    for mode in ("vector", "hybrid"):
        os.environ["RETRIEVAL_MODE"] = mode
        # reset singletons so the mode change takes effect
        import app.retriever as retriever_mod
        import app.rag as rag_mod
        retriever_mod._retriever = None
        rag_mod._assistant = None
        results[mode] = run(quiet=True)
        print(f"  ran {mode}: hit-rate {results[mode]['retrieval_hit_rate']}")

    def fmt(r, key):
        a, b = r[key]
        return f"{100.0 * a / b:.0f}% ({a}/{b})"

    v, h = results["vector"], results["hybrid"]
    print("\n| Metric | Vector-only | Hybrid (BM25 + vector) |")
    print("|---|---|---|")
    for key, label in [("retrieval_hit_rate", "Retrieval hit-rate"),
                       ("answer_accuracy", "Answer accuracy"),
                       ("refusal_accuracy", "Refusal accuracy"),
                       ("citation_coverage", "Citation coverage")]:
        print(f"| {label} | {fmt(v, key)} | **{fmt(h, key)}** |")


if __name__ == "__main__":
    if "--compare" in sys.argv:
        compare()
    else:
        for i, a in enumerate(sys.argv):
            if a == "--retrieval" and i + 1 < len(sys.argv):
                os.environ["RETRIEVAL_MODE"] = sys.argv[i + 1]
        run(strict="--strict" in sys.argv)
