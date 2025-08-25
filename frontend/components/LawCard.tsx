// frontend/components/LawCard.tsx（新規）
import { useState } from "react";

export default function LawCard({ law }: { law: any }) {
  const [open, setOpen] = useState(false);
  const short = (law?.text || "").slice(0, 40) + ((law?.text || "").length > 40 ? "…" : "");
  return (
    <div
      onClick={() => setOpen((v) => !v)}
      style={{
        minWidth: 260,
        maxWidth: 320,
        border: "1px solid #ddd",
        borderRadius: 8,
        padding: 12,
        cursor: "pointer",
        background: open ? "#fafafa" : "#fff",
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 6 }}>{law?.article || "(条)"}</div>
      <div style={{ fontSize: 12, opacity: 0.8, whiteSpace: "pre-wrap" }}>
        {open ? law?.text : short}
      </div>
    </div>
  );
}