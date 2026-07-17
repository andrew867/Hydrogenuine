import React, { useState } from "react";
import { Button } from "./Button";
import { Badge } from "./Badge";

export type ApprovalCardItem = {
  id: string;
  title?: string;
  summary?: string;
  kind?: string;
  risk?: "low" | "medium" | "high" | string;
};

export function ApprovalCard({
  approval,
  busy = false,
  error,
  onApprove,
  onDeny,
}: {
  approval: ApprovalCardItem;
  busy?: boolean;
  error?: string | null;
  onApprove: (note: string) => void | Promise<void>;
  onDeny: (note: string) => void | Promise<void>;
}) {
  const [note, setNote] = useState("");

  return (
    <div data-testid="hg-approval-card" className="hg-card" style={{ borderColor: "var(--hg-status-warning)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
        <strong>{approval.title || "Approval required"}</strong>
        {approval.kind ? <Badge tone="default">{approval.kind}</Badge> : null}
        {approval.risk ? (
          <Badge tone={approval.risk === "high" ? "danger" : approval.risk === "medium" ? "warning" : "success"}>
            {String(approval.risk).toUpperCase()}
          </Badge>
        ) : null}
      </div>
      {approval.summary ? <p style={{ margin: "0 0 12px", color: "var(--hg-text-secondary)" }}>{approval.summary}</p> : null}
      <label style={{ display: "block", fontSize: 12, color: "var(--hg-text-muted)", marginBottom: 4 }}>Note (optional)</label>
      <input
        data-testid="hg-approval-note"
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Audit note"
        style={{
          width: "100%",
          marginBottom: 12,
          padding: "8px 10px",
          borderRadius: "var(--hg-radius-sm)",
          border: "1px solid var(--hg-border)",
          background: "var(--hg-surface-1)",
          color: "var(--hg-text-primary)",
        }}
      />
      {error ? <p style={{ color: "var(--hg-status-danger)", fontSize: 13 }}>{error}</p> : null}
      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <Button disabled={busy} onClick={() => void onDeny(note)}>
          Deny
        </Button>
        <Button variant="primary" disabled={busy} data-testid="hg-approval-approve" onClick={() => void onApprove(note)}>
          Approve
        </Button>
      </div>
    </div>
  );
}
