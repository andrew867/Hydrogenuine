import React from "react";
import { cn } from "../lib/cn";

export type BadgeTone = "default" | "success" | "warning" | "danger" | "info";

const toneStyle: Record<BadgeTone, React.CSSProperties> = {
  default: {},
  success: { background: "rgba(21,128,61,0.15)", color: "var(--hg-status-success)" },
  warning: { background: "rgba(180,83,9,0.15)", color: "var(--hg-status-warning)" },
  danger: { background: "rgba(185,28,28,0.15)", color: "var(--hg-status-danger)" },
  info: { background: "rgba(29,78,216,0.15)", color: "var(--hg-status-info)" },
};

export function Badge({
  children,
  tone = "default",
  className,
}: {
  children: React.ReactNode;
  tone?: BadgeTone;
  className?: string;
}) {
  return (
    <span className={cn("hg-badge", className)} style={toneStyle[tone]}>
      {children}
    </span>
  );
}

export function StatusChip({ status, label }: { status: BadgeTone; label: string }) {
  return <Badge tone={status}>{label}</Badge>;
}
