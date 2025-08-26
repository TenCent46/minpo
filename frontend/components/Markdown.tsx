// frontend/components/Markdown.tsx
"use client";

import React from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";

const components: Components = {
  code(props) {
    // react-markdown は code に inline フラグを渡しますが、
    // 型の都合で any キャストして取り出します
    const { inline, className, children, ...rest } = props as any;

    if (inline) {
      return (
        <code
          className={className}
          style={{
            background: "#f6f8fa",
            padding: "0.1em 0.4em",
            borderRadius: 4,
            fontFamily:
              "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
          }}
          {...rest}
        >
          {children}
        </code>
      );
    }

    return (
      <pre
        style={{
          background: "#0b1020",
          color: "#e6edf3",
          padding: 12,
          borderRadius: 8,
          overflowX: "auto",
        }}
      >
        <code
          className={className}
          {...rest}
          style={{
            fontFamily:
              "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
            fontSize: 13,
          }}
        >
          {children}
        </code>
      </pre>
    );
  },
  a({ children, ...props }) {
    return (
      <a {...props} target="_blank" rel="noreferrer">
        {children}
      </a>
    );
  },
  table({ children, ...props }) {
    return (
      <div style={{ overflowX: "auto" }}>
        <table
          {...props}
          style={{ borderCollapse: "collapse", width: "100%", minWidth: 480 }}
        >
          {children}
        </table>
      </div>
    );
  },
  th({ children, ...props }) {
    return (
      <th
        {...props}
        style={{
          textAlign: "left",
          borderBottom: "1px solid #ddd",
          padding: "6px 8px",
          background: "#fafafa",
        }}
      >
        {children}
      </th>
    );
  },
  td({ children, ...props }) {
    return (
      <td
        {...props}
        style={{ borderBottom: "1px solid #eee", padding: "6px 8px" }}
      >
        {children}
      </td>
    );
  },
};

export default function Markdown({ children }: { children: string }) {
  return (
    <div className="markdown-body">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize]}
        components={components}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}