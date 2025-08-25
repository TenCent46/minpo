from __future__ import annotations
import os
from typing import List, Dict, Any

# Avoid HF tokenizers fork warning / potential deadlocks when the server forks
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

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
    "断定を避けること。"
    "出典条文には天然果実及び法定果実条文番号を必ずつけ、複数ある場合には複数明記すること。"
    "例：第八十八条（天然果実および法定果実）"
)

# ========== OpenAI互換（OpenAI / DeepSeek / Ollama / TGI） ==========
def _chat_openai_like(messages: list[dict]) -> str:
    # openai>=1.x
    from openai import OpenAI

    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL") or None,  # 無指定なら公式
    )

    # まずは環境変数があればそれを優先。なければ広く利用可能な安定モデルを既定にする。
    model = os.getenv("OPENAI_MODEL") or "gpt-5"
    wants_gpt5 = model.startswith("gpt-5")

    try:
        print("model",model)
        print([m.id for m in client.models.list().data if "gpt-5" in m.id])

        # 2) Responses API で最小リクエスト（ChatではなくResponses）
        r = client.responses.create(model="gpt-5", input="OKだけ返して")
        print(r.output_text)
        """rsp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0,
        )"""
        response = client.responses.create(
            model="gpt-5",
            input=[
                    {
                        "role": "user",
                        "content": "Write a one-sentence bedtime story about a unicorn."
                    }
                ]
            )
        print("response", response)
        #return rsp.choices[0].message.content
        return response.output_text
    except Exception as e:
        # モデル未許可/廃止/タイプミスなどに備え、フォールバックを順に試す
        err_msg = str(e)
        print(err_msg)

        # Fallback chain (kept small & practical)
        fallbacks = []
        if wants_gpt5:
            # Prefer other gpt-5 variants first, then step down to 4o
            gpt5_variants = ["gpt-5-mini", "gpt-5-nano", "gpt-5-chat-latest", "gpt-5"]
            for v in gpt5_variants:
                if v != model:
                    fallbacks.append((v, True))   # prefer Responses API for gpt-5 family
            # finally, step down to 4o chat
            fallbacks.extend([("gpt-4o", False), ("gpt-4o-mini", False)])
        else:
            # try sibling mini/regular on chat
            if model != "gpt-4o-mini":
                fallbacks.append(("gpt-4o-mini", False))
            if model != "gpt-4o":
                fallbacks.append(("gpt-4o", False))

        tried = []
        last_err = None

        def _try(fb_model: str, prefer_responses: bool) -> str:
            tried.append((fb_model, prefer_responses))
            if prefer_responses:
                # Use Responses API
                resp = client.responses.create(model=fb_model, input=messages[-1]["content"])
                return resp.output_text
            else:
                rsp = client.chat.completions.create(
                    model=fb_model,
                    messages=messages,
                    temperature=0,
                )
                return rsp.choices[0].message.content

        for fb_model, fb_resp in fallbacks:
            try:
                return _try(fb_model, prefer_responses=fb_resp)
            except Exception as e2:
                last_err = e2
                print(last_err)
                continue
        print(f"[openai-like] exhausted fallbacks; tried={tried}, last_error={last_err}")
        # すべて失敗した場合はエラー内容を上位に伝える
        raise RuntimeError(f"OpenAI-like chat failed for model '{model}': {err_msg}") from e

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

    print("read synthesize answer")
    # 1) 明示プロバイダ
    if prov == "groq" and os.getenv("GROQ_API_KEY"):
        print("read groq")
        return _chat_groq([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ])
    if use_openai_like:
        print("openai like")
        try:
            return _chat_openai_like([
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ])
        except Exception as e:
            print(f"openai_like_exception: {e}")
            # fall back to extractive summary
            pass

    
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