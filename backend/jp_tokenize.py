# backend/jp_tokenize.py
from sudachipy import tokenizer, dictionary
import re

_tokenizer = dictionary.Dictionary().create()
_mode = tokenizer.Tokenizer.SplitMode.C  # 長めの単位

def ja_tokens(text: str) -> list[str]:
    return [m.surface() for m in _tokenizer.tokenize(text, _mode) if m.surface().strip()]

def normalize_text(text: str) -> str:
    # 全角カンマを半角に統一 & 空白正規化
    text = text.replace("，", ",")
    text = re.sub(r"\s+", " ", text)
    return text.strip()