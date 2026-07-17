import React, { useMemo, useState } from "react";
import { Button } from "./Button";
import { Input } from "./Input";

export function JsonViewer({ value, defaultExpanded = false }: { value: unknown; defaultExpanded?: boolean }) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [query, setQuery] = useState("");
  const text = useMemo(() => JSON.stringify(value, null, 2), [value]);
  const filtered = query.trim()
    ? text
        .split("\n")
        .filter((line) => line.toLowerCase().includes(query.toLowerCase()))
        .join("\n")
    : text;

  return (
    <div data-testid="hg-json-viewer">
      <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
        <Input
          placeholder="Search JSON"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Search JSON"
        />
        <Button onClick={() => navigator.clipboard?.writeText(text)}>Copy</Button>
        <Button onClick={() => setExpanded((v) => !v)}>{expanded ? "Collapse" : "Expand"}</Button>
      </div>
      <pre
        style={{
          maxHeight: expanded ? "none" : 240,
          overflow: "auto",
          background: "var(--hg-surface-sunken)",
          padding: 12,
          borderRadius: "var(--hg-radius-sm)",
        }}
      >
        {filtered}
      </pre>
    </div>
  );
}
