"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";

/**
 * 安全にMarkdownを描画する薄いラッパ。
 * - GFM対応（表・打消し・チェックボックスなど）
 * - サニタイズ（XSS対策）
 * - 必要に応じて code ブロックの簡易スタイル
 */
export default function Markdown({ children }: { children: string }) {
  return (
    <div className="markdown-body">
      <ReactMarkdown
        // LLMの出力はたいてい "answer" 文字列
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize]}
        // 必要に応じて要素ごとの上書き
        components={{
          code({ inline, className, children, ...props }) {
            // ここではシンプルに。ハイライトを付けたければ後述のprismなどを使う
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
                  {...props}
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
                  {...props}
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
                  style={{
                    borderCollapse: "collapse",
                    width: "100%",
                    minWidth: 480,
                  }}
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
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}