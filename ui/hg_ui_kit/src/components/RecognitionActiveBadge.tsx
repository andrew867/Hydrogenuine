import React from "react";
import { Badge, BadgeTone } from "./Badge";

export function RecognitionActiveBadge({
  active,
  effectiveClass,
  href,
}: {
  active: boolean;
  effectiveClass?: string;
  href?: string;
}) {
  if (!active) return null;
  const tone: BadgeTone = effectiveClass === "research" ? "warning" : "danger";
  const label = `Recognition active · ${effectiveClass || "session"}`;
  const content = (
    <span data-testid="hg-recognition-active-badge">
      <Badge tone={tone} className="hg-recognition-active-badge">
        {label}
      </Badge>
    </span>
  );
  if (href) {
    return (
      <a href={href} style={{ textDecoration: "none" }}>
        {content}
      </a>
    );
  }
  return content;
}
