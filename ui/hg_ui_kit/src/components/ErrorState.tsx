import React from "react";
import { Button } from "./Button";

export function ErrorState({
  title = "Something went wrong",
  message,
  requestId,
  onRetry,
}: {
  title?: string;
  message: string;
  requestId?: string;
  onRetry?: () => void;
}) {
  return (
    <div data-testid="hg-error-state" className="hg-card" role="alert">
      <h3 style={{ marginTop: 0, color: "var(--hg-status-danger)" }}>{title}</h3>
      <p>{message}</p>
      {requestId ? (
        <p style={{ fontSize: 12, color: "var(--hg-text-muted)" }}>
          Request ID: <code data-testid="hg-error-request-id">{requestId}</code>
        </p>
      ) : null}
      {onRetry ? (
        <Button variant="primary" onClick={onRetry}>
          Retry
        </Button>
      ) : null}
    </div>
  );
}
