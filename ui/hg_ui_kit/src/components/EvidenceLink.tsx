import React from "react";

export type EvidenceKind = "proof" | "provenance" | "receipt" | "audit";

const labels: Record<EvidenceKind, string> = {
  proof: "View proof bundle",
  provenance: "View provenance",
  receipt: "View receipt",
  audit: "View audit report",
};

export function EvidenceLink({
  kind,
  href,
  onClick,
}: {
  kind: EvidenceKind;
  href?: string;
  onClick?: () => void;
}) {
  const label = labels[kind];
  if (href) {
    return (
      <a data-testid={`hg-evidence-${kind}`} href={href}>
        {label}
      </a>
    );
  }
  return (
    <button type="button" className="hg-btn" data-testid={`hg-evidence-${kind}`} onClick={onClick}>
      {label}
    </button>
  );
}
