import React from "react";
import { Button } from "../components/Button";
import { Badge } from "../components/Badge";

export type GovernedSetting = {
  key: string;
  label: string;
  actionClass: string; // ACTION_CLASS_POLICY key
  value: string;
};

// Settings/persona/temperature/model-route changes are governed config changes.
// High/restricted settings are marked as step-up-gated; the panel does not apply
// them silently — it requests the change and the backend holds it if step-up is
// missing.
export function GovernedSettingsPanel({
  settings,
  onRequestChange,
}: {
  settings: GovernedSetting[];
  onRequestChange?: (key: string) => void;
}) {
  const highRisk = new Set(["configuration", "model_route_change", "memory_mutation"]);
  const restricted = new Set(["external_effect", "embodied_control"]);
  return (
    <div className="hg-governed-settings">
      <strong>Governed settings</strong>
      <ul style={{ margin: "6px 0 0", paddingLeft: 0, listStyle: "none" }}>
        {settings.map((s) => (
          <li key={s.key} style={{ display: "flex", gap: 8, alignItems: "center", padding: "2px 0" }}>
            <span>{s.label}</span>
            <code>{s.value}</code>
            {restricted.has(s.actionClass) ? (
              <Badge tone="danger">restricted · step-up per change</Badge>
            ) : highRisk.has(s.actionClass) ? (
              <Badge tone="warning">step-up required</Badge>
            ) : (
              <Badge tone="default">governed</Badge>
            )}
            <Button
              data-testid={`wb-setting-request-${s.key}`}
              aria-label={`Request change: ${s.label}`}
              onClick={() => onRequestChange?.(s.key)}
            >
              Request change
            </Button>
          </li>
        ))}
      </ul>
    </div>
  );
}
