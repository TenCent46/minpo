from __future__ import annotations
from typing import List, Dict, Any
import numpy as np
#from embeddings import embed
from store import STORE
from llm import llm_searchtext
from jp_tokenize import ja_tokens, normalize_text

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

    bm = STORE.bm25.get_scores(ja_tokens(query))

    raw = llm_searchtext(query)
    # normalize and drop empties
    kws = []
    for kw in raw or []:
        if not kw:
            continue
        kw = normalize_text(str(kw)).strip(",")
        if kw:
            kws.append(kw)

    # Tokenize LLM-expanded query with Sudachi as well
    bm2_tokens = ja_tokens(" \n".join(kws))
    bm2 = STORE.bm25.get_scores(bm2_tokens) if bm2_tokens else np.zeros_like(bm)
    print("bm : ", bm)
    print("bm2 : ", bm2)

    bm_n = _minmax(bm)
    bm2_n = _minmax(bm2)

    #score = 0.6 * cos_n + 0.4 * bm_n

        # 埋め込みがあれば加点。なければ BM25 のみ。
    if STORE.embeddings is not None:
        print("embeddings used")
        from embeddings import embed
        q_vec = embed([query])[0]
        cos = (STORE.embeddings @ q_vec)
        cos_n = _minmax(cos)
        score = 0.6 * cos_n + 0.28 * bm_n + 0.12 * bm2_n
    else:
        print("embeddings are not used")
        score = 0.7 * bm_n + 0.3 * bm2_n

    idx = np.argsort(score)[::-1][:top_k]

    results = []
    for i in idx:
        d = STORE.docs[int(i)].copy()
        d["score"] = float(score[int(i)])
        results.append(d)
    return results

# 追加：条文ヒントに基づく強制取得＋BM25補完
import re

def _match_by_article_hints(hints: list[dict]) -> list[int]:
    """hints: [{'article':'709','alias':'不法行為'}, ...]
       号や別名でも拾えるよう、article文字列の数字を優先マッチ。
    """
    idxs = []
    numbers = set()
    aliases = set()
    for h in hints or []:
        a = str(h.get("article","")).strip()
        if a:
            m = re.search(r"\d+", a)
            if m: numbers.add(m.group(0))
        al = str(h.get("alias","")).strip()
        if al: aliases.add(al)
    for i, d in enumerate(STORE.docs):
        art = str(d.get("article",""))
        text = d.get("text","")
        ok = False
        for n in numbers:
            if n and n in art:
                ok = True; break
        if not ok and aliases:
            for al in aliases:
                if al and (al in art or al in text):
                    ok = True; break
        if ok:
            idxs.append(i)
    return idxs

def retrieve_candidates(query: str, law_hints: list[dict], top_k: int = 30):
    # 1) ヒントで直取り
    hinted = _match_by_article_hints(law_hints)
    hinted_set = set(hinted)

    # 2) BM25（Sudachi） + LLM拡張（既存）
    bm = STORE.bm25.get_scores(ja_tokens(query))
    raw = llm_searchtext(query)
    kws = [normalize_text(str(x)).strip(",") for x in (raw or []) if x]
    bm2 = STORE.bm25.get_scores(ja_tokens(" ".join(kws))) if kws else np.zeros_like(bm)

    # 3) RRF 融合（埋込があれば併用）
    def _minmax(x):
        x = np.asarray(x); 
        return np.zeros_like(x) if x.size==0 or x.max()-x.min()<1e-12 else (x-x.min())/(x.max()-x.min())
    def _ranks(a):
        o = np.argsort(a)[::-1]; r = np.empty_like(o); r[o] = np.arange(len(a)); return r

    parts = []
    K = 60
    bm_n, bm2_n = _minmax(bm), _minmax(bm2)
    parts.append(1.0/(K+_ranks(bm_n)))
    parts.append(0.8/(K+_ranks(bm2_n)))

    use_mmr = False
    cos = None
    if STORE.embeddings is not None:
        from embeddings import embed
        q_vec = embed([query])[0]
        cos = (STORE.embeddings @ q_vec)
        cos_n = _minmax(cos)
        parts.append(1.2/(K+_ranks(cos_n)))
        use_mmr = True

    rrf = np.sum(parts, axis=0)
    # ヒント命中はボーナス加点
    if hinted:
        bonus = np.zeros_like(rrf, dtype=float)
        bonus[list(hinted_set)] = 0.5  # 係数は好みで
        rrf = rrf + bonus

    cand = np.argsort(rrf)[::-1][:max(top_k, 8)]

    # MMR でダイバーシティ（埋込がある場合）
    if use_mmr and cos is not None:
        emb = STORE.embeddings
        selected = []
        pool = list(cand)
        # 初手は最大cos
        first = pool[int(np.argmax(cos[pool]))]
        selected.append(first); pool.remove(first)
        while pool and len(selected)<8:
            best_j, best_val = None, -1e9
            for j in pool:
                rel = emb[j] @ q_vec
                div = np.max(emb[j] @ emb[selected].T)
                val = 0.75*rel - 0.25*div
                if val>best_val:
                    best_val, best_j = val, j
            selected.append(best_j); pool.remove(best_j)
        final_idx = selected
    else:
        final_idx = cand[:8]

    results = []
    for i in final_idx:
        d = STORE.docs[int(i)].copy()
        d["score"] = float(rrf[int(i)])
        results.append(d)
    return results