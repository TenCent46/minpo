from __future__ import annotations
from typing import Dict, Any
from search import hybrid_search
from llm import synthesize_answer
from risk import detect_risk_flags


def answer_query(query: str, k: int = 8) -> Dict[str, Any]:
    hits = hybrid_search(query, top_k=k)
    answer = synthesize_answer(query, hits[:4])
    warnings = [
        "AIの出力は法的助言ではない。個別事情は弁護士へ。",
        *detect_risk_flags(query),
    ]
    return {
        "answer": answer,
        "warnings": warnings,
        "sources": [
            {
                "id": h["id"],
                "title": h["title"],
                "article": h.get("article"),
                "article_label": h.get("article_label"),
                "score": h["score"],
            }
        for h in hits[:8]
        ],
    }