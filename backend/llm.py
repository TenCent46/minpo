from __future__ import annotations
import os
from typing import List, Dict, Any

def _get_provider_flags():
    prov = (os.getenv("LLM_PROVIDER", "").lower().strip() or "")
    use_openai_like = bool(
        prov in {"openai", "deepseek", "ollama", "tgi"}
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("OPENAI_BASE_URL")
    )
    return prov, use_openai_like

SYSTEM_PROMPT = (
    "あなたは日本の民法・判例を扱うリーガルアシスタントである。"
    "回答は与えられたコンテキストの範囲で、条文番号と要点を簡潔に説明し、"
    "断定を避け、最後に『これは一般的情報であり法律助言ではない』旨を明記すること。"
)

# ========== OpenAI互換（OpenAI / DeepSeek / Ollama / TGI） ==========
def _chat_openai_like(messages: list[dict]) -> str:
    # openai>=1.x
    from openai import OpenAI
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL") or None,  # 無指定なら公式
    )
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    rsp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0,
    )
    return rsp.choices[0].message.content

# ========== Groq（SDK版） ==========
def _chat_groq(messages: list[dict]) -> str:
    from groq import Groq
    from groq import BadRequestError
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    try:
        r = client.chat.completions.create(model=model, messages=messages, temperature=0)
        return r.choices[0].message.content
    except BadRequestError as e:
        msg = str(e)
        if "model_decommissioned" in msg or "has been decommissioned" in msg:
            for fallback in ("llama-3.3-70b-versatile", "llama-3.1-8b-instant"):
                if fallback == model:
                    continue
                try:
                    r = client.chat.completions.create(model=fallback, messages=messages, temperature=0)
                    return r.choices[0].message.content
                except Exception:
                    pass
        raise

# ========== 公開APIに頼らないフォールバック（抽出要約） ==========
def _extractive_fallback(hits: List[Dict[str, Any]]) -> str:
    parts = []
    for h in hits[:3]:
        t = h["text"].replace("\n", " ")
        parts.append(t[:300])
    body = " / ".join(parts)
    return (
        f"【要点（抽出）】{body}\n\n"
        f"※本回答は一般的情報であり、法律助言ではない。個別事情は専門家へ。"
    )

def synthesize_answer(query: str, hits: List[Dict[str, Any]]) -> str:
    # 参照コンテキストを作成
    context = "\n\n".join([f"\n{h['text']}" for h in hits])
    prompt = (
        "次の参照を根拠に、ユーザーの質問に日本語で簡潔に回答せよ。"
        "参照外の知識は使わない。要点→注意点→参照条文の順で出力：\n\n"
        f"[参照]\n{context}\n\n[質問]\n{query}"
    )
    prov, use_openai_like = _get_provider_flags()
    # 1) 明示プロバイダ
    if prov == "groq" and os.getenv("GROQ_API_KEY"):
        return _chat_groq([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ])
    if use_openai_like:
        try:
            return _chat_openai_like([
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ])
        except Exception:
            pass  # fall back to extractive summary

    # 2) どれも無ければ抽出
    return _extractive_fallback(hits)

def llm_runtime_info() -> dict:
    prov, use_openai_like = _get_provider_flags()
    info = {"provider": prov}
    if prov == "groq":
        info.update({
            "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            "api_key_present": bool(os.getenv("GROQ_API_KEY")),
        })
    if use_openai_like:
        info.update({
            "openai_like_base_url": os.getenv("OPENAI_BASE_URL") or "<official>",
            "openai_like_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "openai_like_key_present": bool(os.getenv("OPENAI_API_KEY")),
        })
    return info