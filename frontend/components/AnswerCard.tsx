"use client";
import { useState } from "react";

type Source = {
  id: string;
  title: string;
  article: string;
  article_label?: string;
  score: number;
};

export default function AnswerCard({ data }: { data: any }) {
  const { answer, warnings, sources } = data;
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [article, setArticle] = useState<any>(null);

  const backend = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

  const showArticle = async (s: Source) => {
    setOpen(true);
    setLoading(true);
    setArticle(null);
    const q = s.article_label || (s.article?.split("（")[0] ?? s.article);
    try {
      const r = await fetch(`${backend}/laws/civilcode?q=${encodeURIComponent(q)}`, { cache: "no-store" });
      const json = await r.json();
      setArticle(json);
    } catch (e) {
      setArticle({ error: String(e) });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ marginTop: 24, padding: 16, border: "1px solid #ddd", borderRadius: 8 }}>
      <h2>回答</h2>
      <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>{answer}</pre>

      {!!warnings?.length && (
        <div style={{ background: '#fffbe6', border: '1px solid #ffe58f', padding: 12, borderRadius: 8 }}>
          <strong>Warnings</strong>
          <ul>
            {warnings.map((w: string, i: number) => <li key={i}>{w}</li>)}
          </ul>
        </div>
      )}

      <h3>参照</h3>
      <ol>
        {sources?.map((s: Source) => (
          <li key={s.id} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
            <span>{s.title} / {s.article}</span>
            <button onClick={() => showArticle(s)} style={{ padding: "4px 8px" }}>条文を見る</button>
            <small style={{ marginLeft: 'auto', opacity: .6 }}>score: {s.score.toFixed(3)}</small>
          </li>
        ))}
      </ol>

      {/* ポップアウト（簡易モーダル） */}
      {open && (
        <div
          onClick={() => setOpen(false)}
          style={{
            position: "fixed", inset: 0, background: "rgba(0,0,0,.35)",
            display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999
          }}
        >
          <div onClick={(e) => e.stopPropagation()}
               style={{ width: "min(800px, 92vw)", maxHeight: "80vh",
                        background: "#fff", borderRadius: 12, padding: 16, overflow: "auto",
                        boxShadow: "0 10px 30px rgba(0,0,0,.2)"}}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <h3 style={{ margin: 0 }}>{article?.article || "条文"}</h3>
              <button onClick={() => setOpen(false)} style={{ fontSize: 18 }}>✕</button>
            </div>
            {loading ? (
              <p>読み込み中…</p>
            ) : article?.error ? (
              <p style={{ color: "crimson" }}>取得に失敗しました: {article.error}</p>
            ) : (
              <pre style={{ whiteSpace: "pre-wrap" }}>{article?.text}</pre>
            )}
          </div>
        </div>
      )}
    </div>
  );
}