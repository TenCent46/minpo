// frontend/components/AnswerCard.tsx
"use client";

import Markdown from "./Markdown";
import LawCard from "./LawCard";

type LawItem = {
  id: string;
  title: string;
  article?: string;
  url?: string;
  score?: number;
  // LawCard 側で使う追加フィールドがあればここに追記
};

type AnswerPayload = {
  answer?: string;
  warnings?: string[];
  used_sources?: LawItem[];
  sources?: LawItem[];
};

export default function AnswerCard({ data }: { data: AnswerPayload | any }) {
  const { answer, warnings, used_sources, sources } = data || {};
  // used_sources があればそれをメイン出典に、なければ sources を流用
  const mainList: LawItem[] = (used_sources && used_sources.length > 0) ? used_sources : (sources || []);
  // 「その他関連」は、mainList で使ったものを除外して並べる
  const mainIds = new Set((mainList || []).map(s => s.id));
  const relatedList: LawItem[] = (sources || []).filter((s: LawItem) => !mainIds.has(s.id));

  return (
    <div style={{ marginTop: 24, padding: 16, border: "1px solid #ddd", borderRadius: 8 }}>
      <h2>回答</h2>

      {/* Markdown/プレーンテキスト両対応 */}
      <div style={{ lineHeight: 1.7 }}>
        <Markdown>{answer || ""}</Markdown>
      </div>

      {!!warnings?.length && (
        <div style={{ background: '#fffbe6', border: '1px solid #ffe58f', padding: 12, borderRadius: 8, marginTop: 12 }}>
          <strong>Warnings</strong>
          <ul style={{ margin: "6px 0 0 18px" }}>
            {warnings.map((w: string, i: number) => <li key={i}>{w}</li>)}
          </ul>
        </div>
      )}

      <section style={{ marginTop: 16 }}>
        <h3>出典条文</h3>
        <p style={{ margin: "6px 0 10px", opacity: .8 }}>クリックで全文を展開できます。</p>
        {(!mainList || mainList.length === 0) ? (
          <div style={{ opacity: .7 }}>（該当なし）</div>
        ) : (
          <div
            style={{
              display: "flex",
              gap: 12,
              overflowX: "auto",
              paddingBottom: 8,
              scrollSnapType: "x proximity",
            }}
          >
            {mainList.map((s: LawItem) => (
              <div key={s.id} style={{ scrollSnapAlign: "start" }}>
                <LawCard law={s} />
              </div>
            ))}
          </div>
        )}
      </section>

      <section style={{ marginTop: 16 }}>
        <h3>その他関連する可能性のある条文</h3>
        {(!relatedList || relatedList.length === 0) ? (
          <div style={{ opacity: .7 }}>（該当なし）</div>
        ) : (
          <div
            style={{
              display: "flex",
              gap: 12,
              overflowX: "auto",
              paddingBottom: 8,
              scrollSnapType: "x proximity",
            }}
          >
            {relatedList.map((s: LawItem) => (
              <div key={s.id} style={{ scrollSnapAlign: "start" }}>
                <LawCard law={s} />
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}