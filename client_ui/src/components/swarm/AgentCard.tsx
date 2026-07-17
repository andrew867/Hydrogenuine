"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/cn";

export type AgentCardStatus = "queued" | "active" | "completed" | "error" | "thinking" | "streaming";

function statusTone(status: AgentCardStatus): "ok" | "danger" | "warning" | "neutral" {
  if (status === "completed") return "ok";
  if (status === "error") return "danger";
  if (status === "active" || status === "streaming" || status === "thinking") return "warning";
  return "neutral";
}

function statusLabel(status: AgentCardStatus): string {
  if (status === "thinking") return "thinking";
  if (status === "streaming") return "streaming";
  return status;
}

export function AgentCard({
  title,
  role,
  status,
  content,
  isPrimary = false,
  selected = false,
  agentIndex = 0,
  onSelect,
}: {
  title: string;
  role: string;
  status: AgentCardStatus;
  content?: string;
  isPrimary?: boolean;
  selected?: boolean;
  agentIndex?: number;
  onSelect?: () => void;
}) {
  const [expanded, setExpanded] = useState(isPrimary || status === "streaming");
  const preview = (content || "").trim();
  const collapsed = status === "completed" && !expanded;

  return (
    <article
      data-testid="swarm-agent-card"
      className={cn(
        "rounded-2xl border px-3 py-3 text-left transition",
        isPrimary ? "border-accent/40 bg-accent/5 shadow-soft" : "border-border/70 bg-bg/40",
        selected ? "ring-2 ring-accent/40" : "",
        onSelect ? "hover:bg-card/60 cursor-pointer" : "",
      )}
      onClick={onSelect}
      onKeyDown={onSelect ? (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect(); } } : undefined}
      role={onSelect ? "button" : undefined}
      tabIndex={onSelect ? 0 : undefined}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex items-start gap-2">
          <div
            className="h-8 w-8 shrink-0 rounded-xl flex items-center justify-center text-xs font-semibold border"
            style={{
              borderColor: `hsl(${(agentIndex * 47) % 360} 70% 45% / 0.45)`,
              background: `hsl(${(agentIndex * 47) % 360} 70% 45% / 0.12)`,
            }}
          >
            {(title || "A").slice(0, 1).toUpperCase()}
          </div>
          <div className="min-w-0">
            <div className="truncate font-medium">{title}</div>
            <div className="text-[11px] uppercase tracking-wide text-muted">{role}</div>
          </div>
        </div>
        <Badge tone={statusTone(status)}>{statusLabel(status)}</Badge>
      </div>
      {!collapsed ? (
        <div className="mt-2 text-sm text-muted whitespace-pre-wrap break-words">
          {preview ? preview.slice(0, isPrimary ? 600 : 280) : "No output yet."}
          {status === "streaming" ? (
            <span className="inline-block w-0.5 h-4 ml-0.5 bg-accent animate-pulse align-middle" aria-hidden />
          ) : null}
        </div>
      ) : (
        <div className="mt-2 text-sm text-muted truncate">{preview.slice(0, 120) || "Done"}</div>
      )}
      {status === "completed" && preview ? (
        <div className="mt-2">
          <Button
            tone="neutral"
            onClick={(e) => {
              e.stopPropagation();
              setExpanded((v) => !v);
            }}
          >
            {expanded ? "Collapse" : "Expand"}
          </Button>
        </div>
      ) : null}
    </article>
  );
}
