import React from "react";
import { Badge, BadgeTone } from "./Badge";

export type RuntimeMode = "live" | "shadow" | "demo" | string;

export function EnvBadge({
  env,
  mode,
  safeLocalOnly,
  systemHref,
}: {
  env?: string;
  mode?: RuntimeMode;
  safeLocalOnly?: boolean;
  systemHref?: string;
}) {
  if (!env && !mode) return null;
  const tone: BadgeTone = safeLocalOnly ? "success" : mode === "shadow" ? "warning" : "info";
  const label = [env ? `Env ${env}` : null, mode ? mode.replace("-", " ") : null].filter(Boolean).join(" · ");
  const content = (
    <Badge tone={tone} className="hg-env-badge" data-testid="hg-env-badge">
      {label}
      {safeLocalOnly ? " · safe local" : ""}
    </Badge>
  );
  if (systemHref) {
    return (
      <a href={systemHref} style={{ textDecoration: "none" }}>
        {content}
      </a>
    );
  }
  return content;
}
