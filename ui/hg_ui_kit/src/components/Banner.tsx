import React from "react";
import { BadgeTone, Badge } from "./Badge";

export function Banner({
  tone = "info",
  children,
}: {
  tone?: BadgeTone;
  children: React.ReactNode;
}) {
  return (
    <div
      data-testid="hg-banner"
      style={{
        padding: "12px 16px",
        borderRadius: "var(--hg-radius-sm)",
        border: "1px solid var(--hg-border)",
        marginBottom: 12,
      }}
    >
      <Badge tone={tone}>{tone}</Badge>
      <div style={{ marginTop: 8 }}>{children}</div>
    </div>
  );
}
