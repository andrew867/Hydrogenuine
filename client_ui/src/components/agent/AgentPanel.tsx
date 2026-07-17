"use client";

import { useQuery } from "@tanstack/react-query";
import { hgApi } from "@/lib/hgApi";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/cn";
import type { HgAgent } from "@/types/hg";
import { useKeyRingStore } from "@/store/keyRingStore";
import { env } from "@/lib/env";
import { visibilityAwareRefetchInterval } from "hg_ui_kit";

function statusTone(s: string) {
  if (s === "working") return "warning";
  if (s === "blocked") return "danger";
  if (s === "error") return "danger";
  return "ok";
}

export function AgentPanel({ chatId }: { chatId: string }) {
  const { operatorKey, impersonationToken, browserSession, locked } = useKeyRingStore();
  const enabled = !!chatId && (env.demoMode || ((!locked && !!operatorKey) || !!impersonationToken || !!browserSession));
  const { data, isError, error } = useQuery({
    queryKey: ["agents", chatId],
    queryFn: () => hgApi.listAgents(chatId),
    refetchInterval: visibilityAwareRefetchInterval(5_000),
    enabled,
    retry: false,
  });

  const agents = data ?? [];
  const errorStatus = typeof error === "object" && error && "status" in error ? Number((error as { status?: number }).status) : null;
  const treatAsEmpty = errorStatus === 404;
  const byId = new Map(agents.map((a) => [a.id, a]));
  const roots = agents.filter((a) => a.role === "primary");
  const showAsRoots = roots.length > 0 ? roots : agents;

  return (
    <Card>
      <div className="flex items-center justify-between">
        <div className="font-semibold">Agents</div>
        <Badge tone="neutral">{agents.length}</Badge>
      </div>
      <div className="text-xs text-muted mt-1">Primary agents may spawn sub-agents. Status is live.</div>

      <div className="mt-3 space-y-2">
        {isError && !treatAsEmpty && (
          <div className="text-sm text-red-600 dark:text-red-400">
            Could not load agents. {error instanceof Error ? error.message : "Retry or check connection."}
          </div>
        )}
        {(!isError || treatAsEmpty) && showAsRoots.map((r) => (
          <Node key={r.id} id={r.id} byId={byId} depth={0} />
        ))}
        {(!isError || treatAsEmpty) && !showAsRoots.length && (
          <div className="text-sm text-muted">No agents reported.</div>
        )}
      </div>
    </Card>
  );
}

function Node({ id, byId, depth }: { id: string; byId: Map<string, HgAgent>; depth: number }) {
  const a = byId.get(id);
  if (!a) return null;
  return (
    <div className={cn("rounded-2xl border border-border/70 bg-bg/30", depth === 0 ? "p-3" : "p-2")}>
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <div className="font-semibold truncate">{a.name || a.id}</div>
          <div className="text-xs text-muted truncate">{a.role === "primary" ? "primary" : "sub-agent"}</div>
        </div>
        <Badge tone={statusTone(a.status)}>{String(a.status).toUpperCase()}</Badge>
      </div>
      {a.status === "error" && (a.stateReason ?? "") && (
        <div className="mt-1 text-xs text-red-600 dark:text-red-400 truncate" title={a.stateReason ?? ""}>
          {a.stateReason}
        </div>
      )}
      {a.children?.length ? (
        <div className="mt-2 pl-3 border-l border-border/70 space-y-2">
          {a.children.map((cid: string) => (
            <Node key={cid} id={cid} byId={byId} depth={depth + 1} />
          ))}
        </div>
      ) : null}
    </div>
  );
}
