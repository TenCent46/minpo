# File: backend/legal_concepts.py
from __future__ import annotations
from typing import List

# 最小の概念展開辞書（必要に応じて拡張）
# 口語→民法系の概念語（BM25で効く法的語彙へ寄せる）
_CONCEPT_MAP = {
    "死ね": ["名誉毀損", "人格権", "不法行為", "侮辱", "慰謝料"],
    "殺す": ["名誉毀損", "人格権", "不法行為", "脅迫", "慰謝料"],
    "殺せ": ["名誉毀損", "人格権", "不法行為", "脅迫", "慰謝料"],
    "暴言": ["名誉毀損", "人格権", "不法行為", "侮辱", "慰謝料"],
    "誹謗中傷": ["名誉毀損", "人格権", "不法行為", "侮辱", "削除", "謝罪"],
    "ストーカー": ["人格権", "不法行為", "差止め", "慰謝料"],
    "嫌がらせ": ["人格権", "不法行為", "名誉毀損", "侮辱", "慰謝料"],
    "離婚": ["婚姻", "財産分与", "親権", "慰謝料"],
    "相続": ["法定相続分", "遺留分", "遺言", "代襲相続"],
}

# 検出したい危険語（これ自体をBM25で強くは使わない）
_LITERAL_RISK = {"死ね", "殺す", "殺せ"}


def expand_concepts(text: str) -> List[str]:
    found = []
    for key, vals in _CONCEPT_MAP.items():
        if key in text:
            found.extend(vals)
    # 重複除去
    return list(dict.fromkeys(found))


def literal_risk_tokens(text: str) -> set[str]:
    return {w for w in _LITERAL_RISK if w in text}
