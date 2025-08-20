from __future__ import annotations

def detect_risk_flags(q: str) -> list[str]:
    q = q.lower()
    flags = []
    keywords = {
        "時効": "時効・除斥期間の可能性あり。期限徒過は重大。",
        "出訴期間": "不服申立・訴訟の期間制限。",
        "差押": "強制執行・保全手続の専門対応が必要。",
        "登記": "不動産・動産譲渡登記の実体・対抗要件の確認。",
        "契約書": "契約条項の個別確認が必要。",
        "相続": "戸籍・遺言・遺留分の個別確認が必要。",
        "損害賠償": "責任要件・因果関係・損害算定は事実依存。",
    }
    for k, v in keywords.items():
        if k in q:
            flags.append(v)
    return flags