import React from "react";
import { Banner } from "./Banner";
import { Button } from "./Button";

export function ImpersonationBanner({
  tenantId,
  role,
  onExit,
}: {
  tenantId?: string | null;
  role?: string | null;
  onExit: () => void;
}) {
  if (!tenantId) return null;
  return (
    <div data-testid="hg-impersonation-banner">
      <Banner tone="warning">
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
          <span>
            Impersonating <strong>{tenantId}</strong>
            {role ? ` as ${role}` : ""}. Actions are watermarked in audit logs.
          </span>
          <Button variant="primary" onClick={onExit}>
            Exit impersonation
          </Button>
        </div>
      </Banner>
    </div>
  );
}
