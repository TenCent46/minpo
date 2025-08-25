from __future__ import annotations
import os
from typing import List, Dict, Any

# backend/llm.py（追記）
import json, re


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
    "人間味のある回答をすること。"
    "出典条文には条文番号及びその別名を必ずつけ、複数ある場合には複数明記すること。"
    "例：第八十八条（天然果実および法定果実）"
)



# ========== OpenAI互換（OpenAI / DeepSeek / Ollama / TGI） ==========
def _chat_openai_like(messages: list[dict]) -> str:
    # openai>=1.x
    from openai import OpenAI

    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        #base_url=os.getenv("OPENAI_BASE_URL") or None,  # 無指定なら公式
    )

    # まずは環境変数があればそれを優先。なければ広く利用可能な安定モデルを既定にする。
    model = os.getenv("OPENAI_MODEL") or "gpt-5"
    wants_gpt5 = model.startswith("gpt-5")

    try:
        print("model",model)
  
        response = client.responses.create(
            model="gpt-5",
            input=messages,
            reasoning={
                     "effort": "minimal",
                    #"summary": "auto" # auto, concise, or detailed, gpt-5 series do not support concise 
            },
            text={ 
                    "verbosity": "low",}
            )
        print("response", response)
        #return rsp.choices[0].message.content
        return response.output_text
    except Exception as e:
        err_msg = str(e)
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


def llm_searchtext(query: str) -> List[str]:
    prompt = (
        "次の[質問]以下の内容を読んで質問の背景を理解し、民法に関して関連する検索ワードを出力してください。"
        "出力は,で区切ってください。また出力は10個までとします。\n\n"
        "例えば、「友達から死ねと言われた」に対して\n"
        "脅迫,相続,遺産\n\n"
        f"[質問]{query}"
    )
    prov, use_openai_like = _get_provider_flags()

    result = ""

    print("read synthesize answer")
    # 1) 明示プロバイダ
    if prov == "groq" and os.getenv("GROQ_API_KEY"):
        print("read groq")
        result= _chat_groq([
            #{"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ])
    elif use_openai_like:
        print("openai like")
        try:
            result=_chat_openai_like([
              #  {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ])
        except Exception as e:
            print(f"openai_like_exception: {e}")
            # fall back to extractive summary
            pass
    print("llm_result", result)
    if not isinstance(result, str):
        result = str(result)
    # unify commas and strip spaces/newlines
    result = result.replace("，", ",").replace("\n", ",").replace("\r", ",")
    split = [t.strip() for t in result.split(",") if t.strip()]
    return split


# 追加：Law Router（民法専門。刑法はNOに振り分け）
import json, re

ROUTER_SYSTEM = (
    "あなたは日本の法律質問を分類するルータです。"
    "出力は必ずJSONのみ。余計な文章は禁止。"
    "domain は 'civil'（民法）'criminal'（刑法）'mixed'（両方）'other' のいずれか。"
    "civil の場合は civil_topics（例: ['不法行為','名誉毀損','相続']）、"
    "law_hints は民法内の候補条文（番号 or 別名）を列挙（例: [{'article':'709','alias':'不法行為'}, ...]）。"
    "search_terms はBM25向けの語句配列。"
    "例：{'domain':'civil','civil_topics':['不法行為'],'law_hints':[{'article':'709','alias':'不法行為'},{'article':'710','alias':'慰謝料'}],'search_terms':['人格権','名誉','慰謝料']}"
)

def _json_from_text(s: str) -> dict:
    # 最初と最後の波括弧の間をJSONとして抽出
    m = re.search(r"\{.*\}", s, re.S)
    if not m: 
        return {}
    try:
        return json.loads(m.group(0))
    except Exception:
        # 末尾カンマ/単引用など軽微な崩れは修正を試みても良いが、まずは素通し
        return {}

def llm_route(query: str) -> dict:
    msg = [
        {"role": "system", "content": ROUTER_SYSTEM},
        {"role": "user",   "content": f"質問: {query}\n厳格JSONで返答。"}
    ]
    # Groq固定
    result = _chat_groq(msg)
    data = _json_from_text(result) or {}
    # 最低限の形に正規化
    data.setdefault("domain", "other")
    data.setdefault("civil_topics", [])
    data.setdefault("law_hints", [])
    data.setdefault("search_terms", [])
    # 文字列化
    for h in data["law_hints"]:
        if "article" in h:
            h["article"] = str(h["article"])
    return data


ANSWER_SYSTEM = (
    "あなたは日本の民法に関するリーガルアシスタント。"
    "与えたコンテキスト内の条文だけを根拠に、"
    "要点→注意点→参照条文 の順で簡潔に回答。"
    "断定を避け、最後に『一般的情報であり法律助言ではない』と明記。"
    "出典条文には条文番号と別名を複数あれば列挙（例：第七百九条（不法行為による損害賠償））。"
)

def llm_answer_from_context(query: str, hits: List[Dict[str, Any]]) -> str:
    ctx = "\n\n".join([f"【{h.get('article','?')}】\n{h['text']}" for h in hits])
    prompt = (
        f"[質問]\n{query}\n\n"
        f"[参照コンテキスト]\n{ctx}\n\n"
        "上記の範囲内だけで回答してください。"
    )
    return _chat_groq([
        {"role": "system", "content": ANSWER_SYSTEM},
        {"role": "user", "content": prompt},
    ])


def _json_pick(s: str) -> dict|list:
    m = re.search(r"\{.*\}|\[.*\]", s, re.S)
    if not m: return {}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {}

PICK_SYSTEM = (
    "あなたは与えられた候補条文リストの中から、回答の根拠として実際に使用した条文だけを厳格に選ぶ係です。"
    "出力は必ず JSON（配列）で、各要素は候補の id を文字列で返すこと。余計な文章は一切禁止。"
)

def llm_pick_used_articles(answer_text: str, hits: list[dict]) -> list[str]:
    """
    hits: [{'id': 'civilcode:709', 'article': '第709条...', 'text': '…'}, ...]
    """
    # 候補をLLMに渡す（id と article だけ掲示）→ JSON配列の id[]
    cand_view = "\n".join([f"- id:{h['id']} / {h.get('article','')}" for h in hits])
    prompt = (
        "以下はあなたが作成した回答本文と、候補条文の一覧です。"
        "回答本文の中で実際に根拠として使った条文だけを、候補一覧の id で返してください。\n\n"
        f"[回答本文]\n{answer_text}\n\n[候補条文]\n{cand_view}\n\n"
        "JSON配列のみを返し、他のテキストは出力しないでください。例：[\"civilcode:709\",\"civilcode:710\"]"
    )
    s = _chat_groq([
        {"role":"system","content": PICK_SYSTEM},
        {"role":"user","content": prompt},
    ])
    data = _json_pick(s)
    if isinstance(data, list):
        return [str(x) for x in data if isinstance(x,(str,int))]
    return []