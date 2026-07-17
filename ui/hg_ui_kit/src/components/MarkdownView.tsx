import React from "react";

/** Lightweight markdown renderer (headings, lists, code fences). */
export function MarkdownView({ source }: { source: string }) {
  const lines = source.split("\n");
  const nodes: React.ReactNode[] = [];
  let list: string[] = [];

  const flushList = () => {
    if (list.length === 0) return;
    nodes.push(
      <ul key={`ul-${nodes.length}`}>
        {list.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>,
    );
    list = [];
  };

  for (const line of lines) {
    if (line.startsWith("# ")) {
      flushList();
      nodes.push(<h1 key={nodes.length}>{line.slice(2)}</h1>);
    } else if (line.startsWith("## ")) {
      flushList();
      nodes.push(<h2 key={nodes.length}>{line.slice(3)}</h2>);
    } else if (line.startsWith("- ")) {
      list.push(line.slice(2));
    } else if (line.startsWith("```")) {
      flushList();
      nodes.push(<pre key={nodes.length} style={{ background: "var(--hg-surface-sunken)", padding: 12 }} />);
    } else if (line.trim() === "") {
      flushList();
    } else {
      flushList();
      nodes.push(<p key={nodes.length}>{line}</p>);
    }
  }
  flushList();

  return <article data-testid="hg-markdown-view">{nodes}</article>;
}
