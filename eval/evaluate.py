"""
Evaluation harness for the RAG assistant.

Measures the things that separate a trustworthy assistant from a demo:
  * Refusal accuracy   - does it correctly say "not in the docs" for
                         out-of-scope questions? (anti-hallucination)
  * Answer accuracy    - does it answer the questions it should?
  * Retrieval hit-rate - is the expected source document retrieved?
  * Citation coverage  - do grounded answers carry at least one citation?

    python -m eval.evaluate            # report
    python -m eval.evaluate --strict   # non-zero exit if refusal/answer < 100%

Run with OPENAI_API_KEY set for production-quality numbers; it also runs on the
local provider (retrieval hit-rate will be lower, refusal/answer stay meaningful).
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

from config import PROJECT_ROOT
from app.providers import active_providers
from app.rag import get_assistant
from app.retriever import get_retriever

EVAL_FILE = Path(__file__).resolve().parent / "eval_questions.yaml"


def run(strict: bool = False) -> int:
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

    print(f"\nEvaluation  (llm={providers['llm']}, embeddings={providers['embeddings']})")
    print("-" * 72)
    for q, kind, verdict in rows:
        print(f"  [{kind}] {q:<48} {verdict}")
    print("-" * 72)
    print(f"  Answer accuracy   : {pct(answer_ok, answer_total)}  ({answer_ok}/{answer_total})")
    print(f"  Refusal accuracy  : {pct(refuse_ok, refuse_total)}  ({refuse_ok}/{refuse_total})")
    print(f"  Retrieval hit-rate: {pct(retr_hit, retr_total)}  ({retr_hit}/{retr_total})")
    print(f"  Citation coverage : {pct(cite_ok, cite_total)}  ({cite_ok}/{cite_total})")

    critical_ok = (answer_ok == answer_total) and (refuse_ok == refuse_total)
    if strict and not critical_ok:
        print("\nstrict: answer/refusal accuracy below 100% -> failing")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run(strict="--strict" in sys.argv))
