// frontend/components/AnswerCard.tsx（差し替え）
import { STATIC_STATUS_PAGE_GET_INITIAL_PROPS_ERROR } from "next/dist/lib/constants";
import LawCard from "./LawCard";

export default function AnswerCard({ data }: { data: any }) {
  const { answer, warnings, used_sources, sources } = data || {};
  const list = (used_sources && used_sources.length > 0) ? used_sources : (sources || []);

  return (
    <div style={{ marginTop: 24, padding: 16, border: "1px solid #ddd", borderRadius: 8 }}>
      <h2>回答</h2>
      <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>{answer}</pre>

      {!!warnings?.length && (
        <div style={{ background: '#fffbe6', border: '1px solid #ffe58f', padding: 12, borderRadius: 8 }}>
          <strong>Warnings</strong>
          <ul>{warnings.map((w: string, i: number) => <li key={i}>{w}</li>)}</ul>
        </div>
      )}

      <h3 style={{ marginTop: 16 }}>出典条文</h3>
      <h5 style={{ marginTop: 16 }}>クリックして全文を表示できます。</h5>
      {list?.length === 0 ? (
        <div style={{ opacity: .7 }}>（該当なし）</div>
      ) : (
        <div
          style={{
            display: "flex",
            gap: 12,
            overflowX: "auto",
            paddingBottom: 8,
          }}
        >
          {list.map((s: any) => <LawCard key={s.id} law={s} />)}
        </div>
      )}
            <h3 style={{ marginTop: 16 }}>その他関連する可能性の条文</h3>
            {sources?.length === 0 ? (
        <div style={{ opacity: .7 }}>（該当なし）</div>
      ) : (
        <div
          style={{
            display: "flex",
            gap: 12,
            overflowX: "auto",
            paddingBottom: 8,
          }}
        >
          {sources.map((s: any) => <LawCard key={s.id} law={s} />)}
        </div>
      )}
    </div>
  );
}