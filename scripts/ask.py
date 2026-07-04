"""CLI: ask the assistant a question.  Usage: python scripts/ask.py "your question" """
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag import get_assistant  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python scripts/ask.py "your question"')
        raise SystemExit(1)
    question = " ".join(sys.argv[1:])
    res = get_assistant().answer(question)
    print(f"\nQ: {question}")
    print(f"\n{res.answer}\n")
    if res.citations:
        print("Sources:")
        for c in res.citations:
            print(f"  [{c['tag']}] {c['source']} — {c['title']}  ({c['score']*100:.0f}% match)")
    else:
        print(f"(grounded={res.grounded}; no citations)")


if __name__ == "__main__":
    main()
