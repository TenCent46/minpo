from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()  # backend/.env を読み込む（最優先で読み込む）
from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from store import STORE
from rag import answer_query
from ingest_egov import DATA_DIR
from pathlib import Path
import json, re


app = FastAPI(title="CivilCode RAG")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)



DATA_FILE = Path(__file__).parent / "data" / "ingested" / "civilcode_egov.json"

def normalize_query(q: str) -> dict:
    q = (q or "").strip()
    digits = re.findall(r"\d+", q)
    num = digits[0] if digits else None
    label = f"第{num}条" if num else q
    return {"label": label, "num": num}


@app.on_event("startup")
def _startup():
    STORE.load()

@app.get("/health")
def health():
    return {"status": "ok", "docs": len(STORE)}

@app.get("/search")
def search(query: str = Query(..., description="自然言語の質問")):
    return answer_query(query)

@app.get("/sources")
def sources():
    # 現在ロードされている文書の一覧
    return STORE.docs[:100]

@app.get("/laws/civilcode")
def get_civilcode(q: str = Query(..., description="例: 第二条 / 第2条 / 2条 / 第709条")):
    if not DATA_FILE.exists():
        return JSONResponse(status_code=404, content={"error": "data file not found"})

    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    norm = normalize_query(q)
    label, num = norm["label"], norm["num"]

    hit = None
    if num:
        hit = next((
            d for d in data
            if re.sub(r"\D", "", d.get("article_label","")) == str(num)
            or d.get("id","").endswith(f":第{num}条")
        ), None)
    if not hit:
        hit = next((
            d for d in data
            if d.get("article_label") == label
            or d.get("article","").startswith(label)
        ), None)

    if not hit:
        return JSONResponse(status_code=404, content={"error": f"not found: {q}"})
    return hit

@app.post("/ingest/egov")
def ingest_from_egov():
    # 事前に ingest_egov.py をCLIで実行しても同じ
    from ingest_egov import fetch_civil_code_xml, parse_law_xml, save_json
    xml_bytes = fetch_civil_code_xml()
    docs = parse_law_xml(xml_bytes)
    out = DATA_DIR / "civilcode_egov.json"
    save_json(docs, out)
    # 再ロード
    STORE.load()
    return {"ingested": len(docs)}

@app.get("/debug/echo")
def debug_echo(q: str = "", request: Request = None):
    return {"q": q, "headers": dict(request.headers) if request else {}}