from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
import numpy as np
import os
DISABLE_EMBEDDINGS = os.getenv("RAG_EMBEDDINGS", "on").lower() in ("off", "0", "false")

DATA_DIR = Path(__file__).parent / "data"
#SEED_PATH = DATA_DIR / "civilcode_seed.json"
INGESTED_DIR = DATA_DIR / "ingested"

class DocStore:
    def __init__(self):
        self.docs: List[Dict[str, Any]] = []
        self.texts: List[str] = []
        self.embeddings = None
        self.bm25 = None

    def load(self):
        docs = []
        if INGESTED_DIR.exists():
            for p in sorted(INGESTED_DIR.glob("*.json")):
                docs.extend(json.loads(p.read_text(encoding="utf-8")))
        #if SEED_PATH.exists():
            #docs.extend(json.loads(SEED_PATH.read_text(encoding="utf-8")))
        # de-dup by id
        seen = set()
        out = []
        for d in docs:
            if d["id"] in seen: continue
            seen.add(d["id"])
            out.append(d)
        self.docs = out
        self.texts = [d["text"] for d in self.docs]
        # vector + bm25
        if self.texts:
            #self.embeddings = embed(self.texts)
            tokenized = [list(d["text"]) for d in self.docs]  # char-level for 日本語BM25の簡易実装
            self.bm25 = BM25Okapi(tokenized)
            print("embeddings are used : ",DISABLE_EMBEDDINGS)
             # 埋め込みは「任意」。失敗しても落ちない
            if not DISABLE_EMBEDDINGS:
                try:
                    from embeddings import embed
                    self.embeddings = embed(self.texts)
                    print("embed success!")
                except Exception as e:
                    # 起動を止めない：ログだけ残し、ベクトル無しで運転
                    print(f"[WARN] embeddings disabled due to error: {e}")
                    self.embeddings = None

    def __len__(self):
        return len(self.docs)

STORE = DocStore()