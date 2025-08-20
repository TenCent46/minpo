from __future__ import annotations
from typing import List, Dict, Any
import numpy as np
from embeddings import embed
from store import STORE

# Hybrid scoring: cosine(sim) + bm25 (min-max正規化) の和

def _minmax(x):
    x = np.asarray(x)
    if x.size == 0: return x
    lo, hi = x.min(), x.max()
    if hi - lo < 1e-12: return np.zeros_like(x)
    return (x - lo) / (hi - lo)


def hybrid_search(query: str, top_k: int = 8) -> List[Dict[str, Any]]:
    #assert STORE.embeddings is not None and STORE.bm25 is not None
    assert STORE.bm25 is not None

    bm = STORE.bm25.get_scores(list(query))

    bm_n = _minmax(bm)

    score = 0.6 * cos_n + 0.4 * bm_n

        # 埋め込みがあれば加点。なければ BM25 のみ。
    if STORE.embeddings is not None:
        from embeddings import embed
        q_vec = embed([query])[0]
        cos = (STORE.embeddings @ q_vec)
        cos_n = _minmax(cos)
        score = 0.6 * cos_n + 0.4 * bm_n
    else:
        score = bm_n

    idx = np.argsort(score)[::-1][:top_k]

    results = []
    for i in idx:
        d = STORE.docs[int(i)].copy()
        d["score"] = float(score[int(i)])
        results.append(d)
    return results