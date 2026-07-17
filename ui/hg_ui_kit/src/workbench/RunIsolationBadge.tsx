import React from "react";
import { Badge } from "../components/Badge";

// Signals run isolation + the always-off external-effects boundary. If external
// effects were ever enabled (they are not in the foundation), this turns danger.
export function RunIsolationBadge({
  runId,
  externalEffectsEnabled,
}: {
  runId: string;
  externalEffectsEnabled: boolean;
}) {
  if (externalEffectsEnabled) {
    return <Badge tone="danger">external effects ENABLED</Badge>;
  }
  return (
    <Badge tone="success" className="hg-run-isolation-badge">
      isolated · no external effects
    </Badge>
  );
}
