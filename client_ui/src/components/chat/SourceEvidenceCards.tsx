"use client";

import React from "react";
import type { SourceEvidence } from "@/types/hg";

export function SourceEvidenceCards({ sources }: { sources: SourceEvidence[] }) {
  if (!sources.length) return null;
  return (
    <div className="mt-3 border-t border-border/70 pt-3">
      <div className="mb-2 text-xs text-muted">Sources</div>
      <div className="grid gap-2">
        {sources.map((source, index) => (
          <a
            key={`${source.url}-${index}`}
            href={source.url}
            target="_blank"
            rel="noreferrer"
            className="rounded-2xl border border-border/70 bg-bg/40 px-3 py-3 hover:border-accent/60 hover:bg-card/60"
          >
            <div className="text-sm font-medium">{source.title || source.url}</div>
            {source.source ? <div className="mt-1 text-[11px] uppercase tracking-wide text-muted">{source.source}</div> : null}
            {source.snippet ? <div className="mt-2 text-xs text-muted line-clamp-3">{source.snippet}</div> : null}
          </a>
        ))}
      </div>
    </div>
  );
}
