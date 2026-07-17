"use client";

import React from "react";

export function SwarmProgressRail({
  completed,
  total,
  active = 0,
  errors = 0,
}: {
  completed: number;
  total: number;
  active?: number;
  errors?: number;
}) {
  const safeTotal = Math.max(total, 1);
  const pct = Math.min(100, Math.round((completed / safeTotal) * 100));
  return (
    <div className="rounded-2xl border border-border/70 bg-bg/40 p-4" data-testid="swarm-progress-rail">
      <div className="flex items-center justify-between gap-3 mb-2">
        <div className="font-semibold">Swarm progress</div>
        <div className="text-sm text-muted">
          {completed}/{total} complete
          {active > 0 ? ` · ${active} active` : ""}
          {errors > 0 ? ` · ${errors} error` : ""}
        </div>
      </div>
      <div className="h-2 rounded-full bg-card/80 overflow-hidden border border-border/50">
        <div
          className="h-full bg-accent transition-all duration-500 ease-out"
          style={{ width: `${pct}%` }}
          role="progressbar"
          aria-valuenow={completed}
          aria-valuemin={0}
          aria-valuemax={total}
        />
      </div>
    </div>
  );
}
