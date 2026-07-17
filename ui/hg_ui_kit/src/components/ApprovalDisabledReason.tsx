import React from "react";
import type { OperatorAuthState } from "../auth/operatorIdentity";

// Renders the inline reason approval controls are disabled. Fed verbatim from the
// backend StepUpVerdict.reason / auth state so the UI never silently enables a
// control the server would refuse.
export function approvalDisabledReason(
  state: OperatorAuthState,
  verdictReason?: string,
): string | null {
  if (state.status === "unauthenticated") return "Sign in to review approvals.";
  if (state.status === "lockdown") return `Console locked down: ${state.reason}`;
  if (state.status === "step_up_required") return state.reason;
  if (verdictReason && verdictReason !== "login_sufficient" &&
      verdictReason !== "recent_session_ok" && !verdictReason.startsWith("step_up_")) {
    return verdictReason;
  }
  return null; // enabled
}

export function ApprovalDisabledReason({
  state,
  verdictReason,
}: {
  state: OperatorAuthState;
  verdictReason?: string;
}) {
  const reason = approvalDisabledReason(state, verdictReason);
  if (!reason) return null;
  return (
    <p className="hg-approval-disabled-reason" role="note" style={{ opacity: 0.8, fontSize: "0.85em" }}>
      {reason}
    </p>
  );
}

export function approvalControlsEnabled(state: OperatorAuthState): boolean {
  return state.status === "authenticated";
}
