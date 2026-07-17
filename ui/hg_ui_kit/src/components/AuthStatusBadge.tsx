import React from "react";
import { Badge } from "./Badge";
import type { OperatorAuthState } from "../auth/operatorIdentity";

// Login/session state at a glance. Demo-local is always visibly flagged so it is
// never mistaken for production operator auth.
export function AuthStatusBadge({ state }: { state: OperatorAuthState }) {
  if (state.status === "unauthenticated") {
    return <Badge tone="default">Signed out</Badge>;
  }
  if (state.status === "lockdown") {
    return <Badge tone="danger">Locked down</Badge>;
  }
  if (state.status === "step_up_required") {
    return <Badge tone="warning">Step-up required</Badge>;
  }
  const { identity } = state;
  if (identity.demo_local_signing) {
    return <Badge tone="warning">Demo-local — not production auth</Badge>;
  }
  return (
    <Badge tone="success">
      {identity.provider === "keycloak" ? "Keycloak" : "Authenticated"}
      {identity.display_name ? ` · ${identity.display_name}` : ""}
    </Badge>
  );
}
