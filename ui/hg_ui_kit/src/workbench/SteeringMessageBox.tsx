import React from "react";
import { Button } from "../components/Button";
import { Badge } from "../components/Badge";

// Sends a steering message. Steering is advice/context — the box labels it as
// "advice, not authority" so the operator understands it does not approve anything.
export function SteeringMessageBox({
  authenticated,
  value,
  onChange,
  onSend,
}: {
  authenticated: boolean;
  value: string;
  onChange?: (v: string) => void;
  onSend?: (v: string) => void;
}) {
  return (
    <div className="hg-steering-box">
      <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
        <strong>Steering</strong>
        <Badge tone="default">advice, not authority</Badge>
      </div>
      <textarea
        className="hg-input"
        aria-label="Steering message"
        placeholder="Add steering context…"
        value={value}
        disabled={!authenticated}
        onChange={(e) => onChange?.(e.target.value)}
      />
      <Button disabled={!authenticated || !value.trim()} onClick={() => onSend?.(value)}>
        Send steering
      </Button>
    </div>
  );
}
