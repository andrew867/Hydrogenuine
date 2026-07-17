"use client";

import { useQuery } from "@tanstack/react-query";
import { hgApi } from "@/lib/hgApi";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import type { ActivityProjection } from "@/types/hg";
import { visibilityAwareRefetchInterval } from "hg_ui_kit";

export function ActivityPanel({ chatId }: { chatId: string }) {
  const { data } = useQuery<ActivityProjection | null>({
    queryKey: ["activity-projection", chatId],
    queryFn: () => hgApi.getActivityProjection({ chat_id: chatId, limit_runs: 8, limit_decisions: 12, view: "compact" }),
    refetchInterval: visibilityAwareRefetchInterval(5_000),
  });

  const summary = data?.active ?? data?.compact;
  const sinceLastWake = data?.since_last_wake ?? data?.compact?.since_last_wake;
  const timeline: Array<Record<string, unknown>> = data?.expanded?.timeline ?? sinceLastWake?.timeline ?? [];

  return (
    <Card>
      <div className="flex items-center justify-between">
        <div className="font-semibold">Activity</div>
        <Badge tone="neutral">{timeline.length}</Badge>
      </div>
      <div className="text-xs text-muted mt-1">A compact unified timeline for agent work and audits.</div>
      {sinceLastWake?.summary ? (
        <div className="mt-2 rounded-xl border border-border/70 bg-bg/30 p-2 text-xs text-muted">
          since last wake: {sinceLastWake.summary}
        </div>
      ) : null}
      {summary?.latest ? (
        <div className="mt-2 text-xs text-muted">
          latest: {String(summary.latest.title || "—")}
          {summary.latest.detail ? ` · ${String(summary.latest.detail)}` : ""}
        </div>
      ) : null}

      <div className="mt-3 space-y-2">
        {timeline.slice(0, 6).map((item, idx: number) => {
          const row = item as Record<string, unknown>;
          const title = String(row.title ?? row.event_type ?? "Timeline event");
          const detail = String(row.detail ?? row.message ?? "No detail available.");
          const key = String(row.event_id ?? row.message_id ?? idx);
          const eventType = String(row.event_type ?? "event");
          return (
            <div key={key} className="rounded-2xl border border-border/70 bg-bg/30 p-3">
              <div className="flex items-center justify-between">
                <div className="font-semibold">{title}</div>
                <Badge tone="neutral">{eventType.toUpperCase()}</Badge>
              </div>
              <div className="mt-2 text-xs text-muted">{detail}</div>
            </div>
          )
        })}
        {!timeline.length ? <div className="text-sm text-muted">No recent activity yet.</div> : null}
      </div>
    </Card>
  );
}
