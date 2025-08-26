from __future__ import annotations
from typing import List, Dict, Any
import numpy as np
#from embeddings import embed
from store import STORE
from llm import llm_searchtext
from jp_tokenize import ja_tokens, normalize_text
from legal_concepts import expand_concepts, literal_risk_tokens

# 民法本文での異表記を吸収するための簡易正規化
LEGAL_CANON = {
    "脅迫": "強迫",            # 民法では「強迫」表記
    "名誉毀損": "名誉 毀損",   # BM25一致を助けるため分割
    "誹謗中傷": "名誉 毀損",   # 相談語→法語へ寄せる
    "ストーカー": "つきまとい"  # 参考（表記差）
}

PAIR_BONUS = {
    709: [710, 723, 719],  # 不法行為 → 慰謝料・名誉回復・共同不法行為
    710: [709, 723],
    723: [709, 710],
}

def expand_canonical(tokens: list[str]) -> list[str]:
    out = list(tokens)
    for t in list(tokens):
        if t in LEGAL_CANON:
            out.extend(ja_tokens(LEGAL_CANON[t]))
    return out

# Hybrid scoring: cosine(sim) + bm25 (min-max正規化) の和

def _minmax(x):
    x = np.asarray(x)
    if x.size == 0: return x
    lo, hi = x.min(), x.max()
    if hi - lo < 1e-12: return np.zeros_like(x)
    return (x - lo) / (hi - lo)

#この関数は現在未使用
def hybrid_search(query: str, top_k: int = 8) -> List[Dict[str, Any]]:
    print("func : hybrid search")
    #assert STORE.embeddings is not None and STORE.bm25 is not None
    assert STORE.bm25 is not None

    bm = STORE.bm25.get_scores(ja_tokens(normalize_text(query)))

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
    bm2_tokens = ja_tokens(normalize_text(" \n".join(kws)))
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

def retrieve_candidates(query: str, law_hints: list[dict], search_terms: list[str] | None = None, civil_topics: list[str] | None = None, top_k: int = 30):
    print("func : retrieve candidates")
    # 1) ヒントで直取り
    hinted = _match_by_article_hints(law_hints)
    hinted_set = set(hinted)

    # === 検索語の優先度設計 ===
    # 1) 原文（口語）
    base_tokens = ja_tokens(normalize_text(query))

    # 2) ルータの search_terms（最優先：法的語彙を想定）
    router_terms = [normalize_text(str(x)).strip(",") for x in (search_terms or []) if x]
    router_tokens = ja_tokens(normalize_text(" ".join(router_terms))) if router_terms else []

    # 3) ルータの civil_topics（概念語：優先）
    topic_terms = [normalize_text(str(x)).strip(",") for x in (civil_topics or []) if x]
    topic_tokens = ja_tokens(normalize_text(" ".join(topic_terms))) if topic_terms else []

    # 4) 口語→法的概念展開（静的辞書）：優先
    concept_terms = expand_concepts(query)
    concept_tokens = ja_tokens(normalize_text(" ".join(concept_terms))) if concept_terms else []

    # 5) リテラル危険語（例："死ね"）は、概念語が得られた場合は重みを下げる
    risk_literals = literal_risk_tokens(query)
    risk_tokens = ja_tokens(" ".join(risk_literals)) if risk_literals else []

    # === 重み付け（BM25に重みを反映する簡便法：トークンの繰り返し回数で擬似的に重み付け） ===
    def repeat(tokens, k):
        out = []
        for t in tokens:
            out.extend([t]*k)
        return out

    # 原文は1x、Router語は3x、トピック/概念は2x、危険リテラルは0x（除外）
    q_tokens_weighted = []
    q_tokens_weighted += repeat(router_tokens, 3)
    q_tokens_weighted += repeat(topic_tokens, 2)
    q_tokens_weighted += repeat(concept_tokens, 2)
    q_tokens_weighted += repeat([t for t in base_tokens if t not in risk_tokens], 1)

    # BM25 スコア（重み付き）
    bm = STORE.bm25.get_scores(q_tokens_weighted) if q_tokens_weighted else np.zeros(len(STORE.docs))
    print("bm", bm)

    # 参考チャネル：Routerのみ（強優先）、LLM拡張（補助）
    if router_tokens:
        bm_router = STORE.bm25.get_scores(repeat(router_tokens, 3))
    else:
        bm_router = np.zeros_like(bm)

    raw = llm_searchtext(query)
    kws_llm = [normalize_text(str(x)).strip(",") for x in (raw or []) if x]
    print("kws_llm", kws_llm)
    llm_joined = normalize_text(" ".join(kws_llm)) if kws_llm else ""
    llm_tokens_raw = ja_tokens(llm_joined) if llm_joined else []
    # 異表記を吸収
    llm_tokens = expand_canonical(llm_tokens_raw)
    # 危険リテラルを LLM チャネルからも除外
    llm_tokens = [t for t in llm_tokens if t not in risk_tokens]
    # フォールバック：それでも空なら全文字（BM25語彙と当たりやすくする）
    if not llm_tokens and llm_joined:
        llm_tokens = list(llm_joined)
    # 語彙オーバーラップをログ
    try:
        if hasattr(STORE, "vocab") and STORE.vocab is not None:
            ov = [t for t in set(llm_tokens) if t in STORE.vocab]
            print(f"llm_tokens overlap with bm25 vocab: {len(ov)} -> {ov[:20]}")
    except Exception:
        pass
    bm_llm = STORE.bm25.get_scores(repeat(llm_tokens, 2)) if llm_tokens else np.zeros_like(bm)
    print("bm_llm", bm_llm)
    print("bm llm shape", bm_llm.shape)
    # 3) RRF 融合（埋込があれば併用）
    def _minmax(x):
        x = np.asarray(x)
        return np.zeros_like(x) if x.size==0 or x.max()-x.min()<1e-12 else (x-x.min())/(x.max()-x.min())
    def _ranks(a):
        o = np.argsort(a)[::-1]
        r = np.empty_like(o)
        r[o] = np.arange(len(a))
        return r

    K = 60
    parts = []
    parts.append(1.0/(K+_ranks(_minmax(bm))))          # 重み付き統合クエリ
    parts.append(1.2/(K+_ranks(_minmax(bm_router))))   # Router語（最優先）
    parts.append(0.6/(K+_ranks(_minmax(bm_llm))))      # LLM拡張（補助）

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

    print("rrf",rrf)


    try:
    # 候補ごとに article_num を引く
        article_nums = []
        for i, d in enumerate(STORE.docs):
            n = d.get("article_num")
            article_nums.append(int(n) if isinstance(n, (int, float, str)) and str(n).isdigit() else None)

    # 上位に 709/710/723 が居たら、対応ペアにボーナス
        bonus = np.zeros_like(rrf, dtype=float)
        top_pre = np.argsort(rrf)[::-1][:50]  # 上位50を見て関係を張る
        present = set([article_nums[j] for j in top_pre if article_nums[j] is not None])

        for base in list(present):
            neighbors = PAIR_BONUS.get(base, [])
            for nb in neighbors:
            # その条文番号のインデックス（複数ありうるが通常1件）
                for j, n in enumerate(article_nums):
                    if n == nb:
                        bonus[j] += 0.4  # 係数は適宜。0.3〜0.6で手応えを見て
        rrf = rrf + bonus
    except Exception:
        pass

    cand = np.argsort(rrf)[::-1][:max(top_k, 8)]

    # MMR を使わず、単純な上位選択 + 条文番号での重複除外に切り替え
    # より安定・低遅延で、法令ドキュメントでは重複（同条異片）を抑えやすい
    # 上位候補を広めにとってから、article_num でユニーク化
    pool = list(np.argsort(rrf)[::-1][:max(top_k * 4, 32)])
    final_idx = []
    seen_nums = set()
    for j in pool:
        num = STORE.docs[j].get("article_num")
        # article_num が同じものは一つにまとめる（なければ id でフォールバック）
        key = int(num) if isinstance(num, (int, float, str)) and str(num).isdigit() else STORE.docs[j].get("id")
        if key in seen_nums:
            continue
        seen_nums.add(key)
        final_idx.append(j)
        if len(final_idx) >= max(8, top_k):
            break

    results = []
    for i in final_idx:
        d = STORE.docs[int(i)].copy()
        d["score"] = float(rrf[int(i)])
        results.append(d)
    print("results",results)
    return results
