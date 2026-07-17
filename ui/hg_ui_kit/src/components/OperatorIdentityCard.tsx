import React from "react";
import { Card } from "./Card";
import { Badge } from "./Badge";
import type { OperatorIdentityView } from "../auth/operatorIdentity";

function truncate(s: string, n = 10): string {
  return s.length > n ? `${s.slice(0, n)}…` : s;
}

// Shows who the verified operator is. Subject UUID is the identity key; the
// session id is shown hashed only; demo-local is flagged; no token material.
export function OperatorIdentityCard({ identity }: { identity: OperatorIdentityView }) {
  return (
    <Card className="hg-operator-identity-card">
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
        <strong>{identity.display_name || "Operator"}</strong>
        {identity.demo_local_signing ? (
          <Badge tone="warning">demo-local</Badge>
        ) : identity.production_operator_auth ? (
          <Badge tone="success">keycloak-verified</Badge>
        ) : (
          <Badge tone="default">unverified</Badge>
        )}
      </div>
      <dl style={{ margin: "8px 0 0", display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 8px" }}>
        <dt>Subject</dt>
        <dd title={identity.subject}><code>{truncate(identity.subject, 12)}</code></dd>
        {identity.email ? (<><dt>Email</dt><dd>{identity.email}</dd></>) : null}
        <dt>Roles</dt>
        <dd>{identity.roles.map((r) => <Badge key={r} tone="info">{r}</Badge>)}</dd>
        <dt>Assurance</dt>
        <dd>{identity.assurance_level}</dd>
        {identity.session_id_hash ? (
          <><dt>Session</dt><dd><code>{truncate(identity.session_id_hash, 16)}</code></dd></>
        ) : null}
      </dl>
    </Card>
  );
}
