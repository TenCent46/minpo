from __future__ import annotations
import httpx
from lxml import etree
from pathlib import Path
import json
from urllib.parse import quote

DATA_DIR = Path(__file__).parent / "data" / "ingested"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 民法: 法令ID 129AC0000000089
LAW_ID = "129AC0000000089"
ENDPOINT = f"https://laws.e-gov.go.jp/api/1/lawdata/{LAW_ID}"


def fetch_civil_code_xml() -> bytes:
    with httpx.Client(timeout=60) as client:
        r = client.get(ENDPOINT)
        r.raise_for_status()
        return r.content


def parse_law_xml(xml_bytes: bytes):
    root = etree.fromstring(xml_bytes)
    # 既定名前空間のURI（ある場合）
    ns_uri = root.nsmap.get(None)

    # nsが取れるならprefix付き、ダメならlocal-name()にフォールバックするヘルパ
    def xp(expr_no_ns: str, tag: str):
        # expr_no_ns は "Law" や "Article" などのタグ名
        if ns_uri:

            return f".//ns:{tag}"
        else:
            return f".//*[local-name()='{tag}']"

    ns = {"ns": ns_uri} if ns_uri else None

    # Lawノード
    law_nodes = root.xpath(xp("//", "Law"), namespaces=ns) if ns else root.xpath("//*[local-name()='Law']")
    if not law_nodes:
        raise ValueError("Law node not found in e-Gov XML")
    law = law_nodes[0]

    # タイトル
    title_node = law.xpath(xp(".", "LawTitle"), namespaces=ns) if ns else law.xpath(".//*[local-name()='LawTitle']")
    law_title = title_node[0].text if title_node else "民法"

    # 条文
    articles = law.xpath(xp(".", "Article"), namespaces=ns) if ns else law.xpath(".//*[local-name()='Article']")

    docs = []
    for i, a in enumerate(articles):
        # 見出し・条番号
        cap = a.xpath(xp(".", "ArticleCaption"), namespaces=ns) if ns else a.xpath(".//*[local-name()='ArticleCaption']")
        ttl = a.xpath(xp(".", "ArticleTitle"), namespaces=ns) if ns else a.xpath(".//*[local-name()='ArticleTitle']")
        cap_text = cap[0].text if cap else ""
        art_title = ttl[0].text if ttl else "(条)"

        # 本文（Paragraph → Sentence）
        paragraphs = a.xpath(xp(".", "Paragraph"), namespaces=ns) if ns else a.xpath(".//*[local-name()='Paragraph']")
        sentences = []
        for p in paragraphs:
            sent_nodes = p.xpath(xp(".", "Sentence"), namespaces=ns) if ns else p.xpath(".//*[local-name()='Sentence']")
            if sent_nodes:
                text = "".join([(s.text or "") for s in sent_nodes])
            else:
                text = (p.text or "").strip()
            if text:
                sentences.append(text)

        body = "\n".join([s.strip() for s in sentences if s.strip()])
        if not body:
            continue

        article_num = art_title
        doc_id = f"civilcode:{article_num}"
        """
        url = f"https://laws.e-gov.go.jp/law/{LAW_ID}#/{article_num}"
        docs.append({
            "id": doc_id,
            "title": law_title,
            "article": article_num,
            "text": f"{cap_text}\n{body}".strip(),
            "url": url,
        })"""
        article_label = article_num.split("（")[0] if "（" in article_num else article_num
        #url = f"/laws/civilcode/{article_num}"
        #url = f"/laws/civilcode?q={quote(article_label)}"

        docs.append({
            #"article_num":(i+1),
            "id": doc_id,
            "title": law_title,
            "article": art_title,
            "article_label": article_label,
            "text": f"{cap_text}\n{body}".strip(),
            #"url": url,
        })
    return docs
    root = etree.fromstring(xml_bytes)
    ns = {"ns": root.nsmap.get(None, None)}
    # LawBody/Item/Article ... はスキーマにより階層が深いことがある
    law_nodes = root.xpath("//Law", namespaces=ns) or root.xpath("//*[local-name()='Law']")
    law = law_nodes[0]
    title_node = law.xpath(".//LawTitle", namespaces=ns) or law.xpath(".//*[local-name()='LawTitle']")
    law_title = title_node[0].text if title_node else "民法"

    articles = law.xpath(".//Article", namespaces=ns) or law.xpath(".//*[local-name()='Article']")
    docs = []
    for a in articles:
        # 見出し・条番号
        cap = a.xpath("./ArticleCaption", namespaces=ns) or a.xpath("./*[local-name()='ArticleCaption']")
        ttl = a.xpath("./ArticleTitle", namespaces=ns) or a.xpath("./*[local-name()='ArticleTitle']")
        cap_text = cap[0].text if cap else ""
        art_title = ttl[0].text if ttl else "(条)"
        # 本文（Paragraph → Sentence）を連結
        paragraphs = a.xpath(".//Paragraph", namespaces=ns) or a.xpath(".//*[local-name()='Paragraph']")
        sentences = []
        for p in paragraphs:
            sent_nodes = p.xpath(".//Sentence", namespaces=ns) or p.xpath(".//*[local-name()='Sentence']")
            if sent_nodes:
                text = "".join([s.text or "" for s in sent_nodes])
            else:
                text = (p.text or "").strip()
            if text:
                sentences.append(text)
        body = "\n".join([s.strip() for s in sentences if s.strip()])
        if not body:
            continue
        # 1条を1ドキュメントとして格納
        article_num = art_title
        doc_id = f"civilcode:{article_num}"
        url = f"https://laws.e-gov.go.jp/law/{LAW_ID}#/{article_num}"
        docs.append({
            "id": doc_id,
            "title": law_title,
            "article": article_num,
            "text": f"{cap_text}\n{body}".strip(),
            "url": url,
        })
    return docs


def save_json(docs, path: Path):
    path.write_text(json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    xml_bytes = fetch_civil_code_xml()
    docs = parse_law_xml(xml_bytes)
    out = DATA_DIR / "civilcode_egov.json"
    save_json(docs, out)
    print(f"Saved {len(docs)} articles to {out}")