import React from "react";
import { Modal } from "./Overlay";
import { Button } from "./Button";
import { Input } from "./Input";

export function StepUpModal({
  open,
  title = "Step-up authentication required",
  description,
  code,
  onCodeChange,
  error,
  verifying,
  onSubmit,
  onClose,
}: {
  open: boolean;
  title?: string;
  description: string;
  code: string;
  onCodeChange: (value: string) => void;
  error?: string | null;
  verifying?: boolean;
  onSubmit: () => void;
  onClose: () => void;
}) {
  return (
    <Modal open={open} onClose={onClose}>
      <div style={{ padding: 16 }} data-testid="hg-stepup-modal">
        <h2 style={{ marginTop: 0 }}>{title}</h2>
        <p>{description}</p>
        {error ? <p style={{ color: "var(--hg-status-danger)" }}>{error}</p> : null}
        <Input
          aria-label="Authenticator code"
          placeholder="6-digit code"
          value={code}
          onChange={(e) => onCodeChange(e.target.value)}
        />
        <div style={{ display: "flex", gap: 8, marginTop: 12, justifyContent: "flex-end" }}>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" disabled={verifying || code.trim().length < 6} onClick={onSubmit}>
            {verifying ? "Verifying…" : "Verify"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
