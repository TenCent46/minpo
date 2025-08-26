"use client";
import { useState } from "react";
import AnswerCard from "../components/AnswerCard";

export default function Page() {
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any>(null);

  const doSearch = async () => {
    if (!q) return;
    setLoading(true);
    setData(null);
    const endpoint = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
    const res = await fetch(`${endpoint}/search?query=${encodeURIComponent(q)}`);
    const json = await res.json();
    setData(json);
    setLoading(false);
  };

  return (
    <div style={{ maxWidth: 860, margin: "40px auto", padding: 16 }}>
      <h1>民法RAG 検索</h1>
        <p style={{opacity:.8}}>
        専門用語/口語どちらでも可。根拠条文を引用して簡潔に回答。
        {" "}
        <a href="https://laws.e-gov.go.jp/law/129AC0000000089" target="_blank" rel="noreferrer">
          e‑Gov法令検索を開く
        </a>
      </p>
      <div style={{ display: "flex", gap: 8 }}>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && doSearch()}
          placeholder="例：SNSの誹謗中傷は民法上どうなる？ 相続分は？ 契約解除したい…"
          style={{ flex: 1, padding: 12, borderRadius: 8, border: "1px solid #ccc" }}
        />
        <button onClick={doSearch} disabled={loading} style={{ padding: "12px 16px" }}>
          {loading ? "検索中…" : "検索"}
        </button>
      </div>
      {data && <AnswerCard data={data} />}
    </div>
  );
}