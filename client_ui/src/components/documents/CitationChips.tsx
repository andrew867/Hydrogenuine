"use client";

import React from "react";
import type { Citation } from "@/types/hg";
import { cn } from "@/lib/cn";

export function CitationChips({
  citations,
  onCitationClick,
}: {
  citations: Citation[];
  onCitationClick?: (c: Citation) => void;
}) {
  if (!citations?.length) return null;
  return (
    <div className="mt-3 pt-3 border-t border-border/70">
      <div className="text-xs text-muted mb-2">Citations</div>
      <div className="flex flex-wrap gap-1.5">
        {citations.map((c, i) => {
          const label =
            c.document_id && (c.page_start != null || c.page_end != null)
              ? `${c.filename || c.document_id}${c.page_start != null ? ` p.${c.page_start}` : ""}${c.page_end != null && c.page_end !== c.page_start ? `–${c.page_end}` : ""}`
              : c.title || c.filename || c.document_id || `Citation ${i + 1}`;
          const clickable = onCitationClick && (c.document_id || c.url);
          return (
            <button
              key={i}
              type="button"
              className={cn(
                "text-xs px-2 py-1 rounded-lg border border-border/70 bg-card/50",
                clickable && "hover:border-accent/60 hover:bg-accent/10 cursor-pointer",
                !clickable && "cursor-default"
              )}
              onClick={() => clickable && (c.document_id ? onCitationClick(c) : c.url ? window.open(c.url) : null)}
              title={c.note || label}
            >
              <span className="text-text">{label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
