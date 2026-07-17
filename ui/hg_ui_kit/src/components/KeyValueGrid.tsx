import React from "react";

export function KeyValueGrid({ entries }: { entries: Array<{ key: string; value: React.ReactNode }> }) {
  return (
    <dl
      data-testid="hg-kv-grid"
      style={{
        display: "grid",
        gridTemplateColumns: "minmax(120px, 1fr) 2fr",
        gap: "8px 16px",
        margin: 0,
      }}
    >
      {entries.map((row) => (
        <React.Fragment key={row.key}>
          <dt style={{ color: "var(--hg-text-muted)", margin: 0 }}>{row.key}</dt>
          <dd style={{ margin: 0 }}>{row.value}</dd>
        </React.Fragment>
      ))}
    </dl>
  );
}
