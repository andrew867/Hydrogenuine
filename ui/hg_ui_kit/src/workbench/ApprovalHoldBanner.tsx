import React from "react";
import { Banner } from "../components/Banner";

// Rendered when a governed action is HELD pending step-up/approval. Shows the
// reason verbatim from the backend verdict; never implies the action proceeded.
export function ApprovalHoldBanner({
  reason,
  setting,
}: {
  reason: string;
  setting?: string;
}) {
  return (
    <Banner tone="warning">
      <div role="alert" data-testid="wb-hold-banner">
        <strong>Action held</strong>
        <div>
          {setting ? `Change to "${setting}" is held pending step-up.` : "Action held pending step-up."}
        </div>
        <div style={{ opacity: 0.8, fontSize: "0.85em" }}>Reason: {reason}</div>
      </div>
    </Banner>
  );
}
