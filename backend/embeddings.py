from __future__ import annotations
from sentence_transformers import SentenceTransformer
import numpy as np
from functools import lru_cache

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

@lru_cache(maxsize=1)
def _load_model():
    return SentenceTransformer(MODEL_NAME)

def embed(texts: list[str]) -> np.ndarray:
    model = _load_model()
    vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(vecs)