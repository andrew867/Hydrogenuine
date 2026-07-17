import React from "react";
import { AuthStatusBadge } from "../components/AuthStatusBadge";
import type { OperatorAuthState } from "../auth/operatorIdentity";

// Top-level Workbench frame. Gated on operator auth: the composer/run controls are
// only enabled when authenticated. Demo-local is flagged by AuthStatusBadge.
export function WorkbenchShell({
  authState,
  children,
}: {
  authState: OperatorAuthState;
  children?: React.ReactNode;
}) {
  const authed = authState.status === "authenticated";
  return (
    <div className="hg-workbench-shell" data-authed={authed}>
      <header
        className="hg-workbench-header"
        style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}
      >
        <strong>Agent Zero Workbench</strong>
        <AuthStatusBadge state={authState} />
      </header>
      {authed ? (
        <div className="hg-workbench-body">
          <div
            className="hg-workbench-operator"
            data-testid="wb-operator"
            style={{ fontSize: "0.85em", opacity: 0.85, margin: "2px 0 8px" }}
          >
            Authenticated as{" "}
            <code>{authState.identity.display_name || authState.identity.subject}</code>
            {" · external effects disabled"}
          </div>
          {children}
        </div>
      ) : (
        <div className="hg-workbench-locked" role="note">
          Sign in with the Agent Zero panel to create a governed run.
        </div>
      )}
    </div>
  );
}
