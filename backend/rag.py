from __future__ import annotations
from typing import Dict, Any, List
from llm import llm_route, llm_answer_from_context, llm_pick_used_articles
from search import retrieve_candidates
from risk import detect_risk_flags


CIVIL_ONLY_NOTE = "このサービスは民法に特化しています。刑事・行政の個別判断は対象外です。"

def answer_query(query: str, mode: str | None = None) -> Dict[str, Any]:
    route = llm_route(query)
    domain = route.get("domain","other")
    print("route : ",route)
    """
    if domain in ("criminal","other"):
        msg = (
            "ご相談ありがとうございます。この内容は民法の範囲を超える可能性が高いため、ここでは具体的判断を行いません。\n\n"
            f"{CIVIL_ONLY_NOTE}\n"
            "※緊急の危険がある場合は110/119等へ。"
        )
        return {
            "answer": msg + "\n\n※本回答は一般的情報であり法律助言ではありません。",
            "warnings": ["民法以外の可能性（刑法/行政法）。専門家へご相談を。"],
            "sources": [],
            "used_sources": []
        }
"""
    # 取得（ヒント優先 + RRF/MMR 補完）
    #hits = retrieve_candidates(query, route.get("law_hints", []))  # 8件程度
    hits = retrieve_candidates(query, route.get("law_hints", []), route.get("search_terms", []), route.get("civil_topics", []))
    # 回答
    answer = llm_answer_from_context(query, hits[:4])
    # 使用条文の選定（id配列）
    used_ids = llm_pick_used_articles(answer, hits)
    ##print("hits : ", hits)

    # used_sources を構築（フロントがそれだけカード化できるように）
    used_map = {h["id"]: h for h in hits}
    #print("used_map : ", used_map)
    used_sources = []
    for uid in used_ids:
        if uid in used_map:
            h = used_map[uid]
            used_sources.append({
                "id": h["id"],
                "title": h.get("title",""),
                "article": h.get("article",""),
                "text": h.get("text",""),
                "score": h.get("score", 0.0),
            })

    #print("used sources : ", used_sources)

    if domain in ("criminal","other"):
        warnings = ["AIの出力は法的助言ではない。個別事情は弁護士へ。", *detect_risk_flags(query)]
    else:
        warnings = ["この内容は民法の範囲を超える可能性が高いです。他の法律を包括的に考える場合は別ツールの採用または弁護士への相談をしてください。", *detect_risk_flags(query)]
    return {
        "answer": answer,
        "warnings": warnings,
        "router": route,        # デバッグ用（不要なら削除可）
        "sources": hits,        # 取得した全候補（従来互換）
        "used_sources": used_sources  # ← これだけをカード表示に使う
    }


"""
def answer_query(query: str, k: int = 8) -> Dict[str, Any]:
    hits = hybrid_search(query, top_k=k)
    answer = synthesize_answer(query, hits[:4])
    warnings = [
        "AIの出力は法的助言ではない。個別事情は弁護士へ。",
        *detect_risk_flags(query),
    ]

# backend/rag.py （return の sources 部分だけ差し替え）
    return {
    "answer": answer,
    "warnings": warnings,
    "sources": [
        {
            "id": h["id"],
            "title": h["title"],
            "article": h.get("article"),
            "url": h.get("url", ""),
            "score": h["score"],
            "snippet": (h.get("text","").replace("\n"," ")[:240] + ("…" if len(h.get("text","")) > 240 else ""))
        }
        for h in hits[:8]
    ],
}"""
    
