import React from "react";
import { Button } from "./Button";

export function EmptyState({
  title,
  description,
  actionLabel,
  onAction,
}: {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  return (
    <div data-testid="hg-empty-state" className="hg-card" style={{ textAlign: "center" }}>
      <h3 style={{ marginTop: 0 }}>{title}</h3>
      <p style={{ color: "var(--hg-text-secondary)" }}>{description}</p>
      {actionLabel && onAction ? (
        <Button variant="primary" onClick={onAction}>
          {actionLabel}
        </Button>
      ) : null}
    </div>
  );
}
