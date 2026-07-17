import React from "react";
import { Skeleton } from "./Skeleton";

export function PageSkeleton({
  rows = 4,
  label,
}: {
  rows?: number;
  label?: string;
}) {
  return (
    <div data-testid="hg-page-skeleton" aria-busy="true" aria-label={label || "Loading"}>
      {label ? (
        <p style={{ color: "var(--hg-text-muted)", fontSize: 13, margin: "0 0 12px" }}>{label}</p>
      ) : null}
      <Skeleton height={24} className="hg-page-skeleton-title" />
      <div style={{ marginTop: 12, display: "grid", gap: 8 }}>
        {Array.from({ length: rows }).map((_, index) => (
          <Skeleton key={index} height={16} />
        ))}
      </div>
    </div>
  );
}
