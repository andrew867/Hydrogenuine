"use client";

import React, { useEffect, useState } from "react";
import type { ToolEvent } from "@/types/hg";
import { Badge } from "@/components/ui/Badge";
import { Icon } from "@/components/ui/Icon";
import { relTime } from "@/lib/time";

export function ToolCard({ tool, when }: { tool: ToolEvent; when: string }) {
  const [expanded, setExpanded] = useState(tool.status === "running" || tool.status === "error");
  const hasTimeline = (tool.timeline?.length ?? 0) > 0;
  const isCompact = tool.status === "ok" && !expanded;

  useEffect(() => {
    if (tool.status === "running" || tool.status === "error") {
      setExpanded(true);
      return;
    }
    if (tool.status === "ok") {
      setExpanded(false);
    }
  }, [tool.status, hasTimeline]);

  return (
    <div className={`max-w-[760px] w-full rounded-3xl border border-border/70 bg-bg/30 ${isCompact ? "px-4 py-2.5" : "p-4"}`}>
      <div className="flex items-center justify-between gap-2">
        <div className="font-semibold">{tool.name}</div>
        <div className="flex items-center gap-2">
          <Badge tone={tool.status === "error" ? "danger" : tool.status === "running" ? "warning" : "ok"}>
            {tool.status.toUpperCase()}
          </Badge>
          <div className="text-[11px] text-muted">{relTime(when)}</div>
          {hasTimeline ? (
            <button
              type="button"
              onClick={() => setExpanded((e) => !e)}
              className="p-1 rounded-lg text-muted hover:text-text hover:bg-bg/50 transition flex items-center gap-0.5"
              title={expanded ? "Hide timeline" : "Show timeline"}
              aria-expanded={expanded}
            >
              {expanded ? <Icon name="chevronUp" className="h-4 w-4" /> : <Icon name="chevronDown" className="h-4 w-4" />}
              <span className="text-xs">{expanded ? "Hide" : isCompact ? "Details" : "Timeline"}</span>
            </button>
          ) : isCompact ? (
            <button
              type="button"
              onClick={() => setExpanded(true)}
              className="p-1 rounded-lg text-muted hover:text-text hover:bg-bg/50 transition flex items-center gap-0.5"
              title="Show details"
              aria-expanded={expanded}
            >
              <Icon name="chevronDown" className="h-4 w-4" />
              <span className="text-xs">Details</span>
            </button>
          ) : null}
        </div>
      </div>
      {tool.detail ? <div className={`text-sm text-muted ${isCompact ? "mt-1 line-clamp-1" : "mt-2"}`}>{tool.detail}</div> : null}
      {hasTimeline && expanded ? (
        <div className="mt-3 pt-3 border-t border-border/70">
          <div className="text-xs text-muted mb-2">Run timeline</div>
          <div className="space-y-2">
            {tool.timeline!.map((t, i) => (
              <div key={i} className="flex items-center gap-2 text-sm">
                <span className="h-2 w-2 rounded-full bg-accent/50 shrink-0" />
                <span className="text-text">{t.label}</span>
                {t.at ? <span className="text-[11px] text-muted ml-auto">{relTime(t.at)}</span> : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
