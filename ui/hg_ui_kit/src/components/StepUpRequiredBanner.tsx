import React from "react";
import { Banner } from "./Banner";

// Shown when the risk policy holds an approval pending re-authentication. It says
// "step-up required" — it never pretends step-up is complete.
export function StepUpRequiredBanner({
  reason,
  riskCategory,
  onStepUp,
}: {
  reason: string;
  riskCategory?: string;
  onStepUp?: () => void;
}) {
  const label =
    riskCategory === "breakglass"
      ? "Breakglass approval requires step-up and a written reason."
      : riskCategory === "restricted"
        ? "Restricted approval requires step-up for every decision."
        : "High-risk approval requires re-authentication (step-up).";
  return (
    <Banner tone="warning">
      <strong>Step-up required</strong>
      <div>{label}</div>
      <div style={{ opacity: 0.8, fontSize: "0.85em" }}>Reason: {reason}</div>
      {onStepUp ? (
        <button type="button" className="hg-button" onClick={onStepUp} style={{ marginTop: 6 }}>
          Re-authenticate
        </button>
      ) : null}
    </Banner>
  );
}
