"use client";

import React, { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { hgApi } from "@/lib/hgApi";
import { useKeyRingStore } from "@/store/keyRingStore";
import { env } from "@/lib/env";
import { HardNavLink } from "@/components/navigation/HardNavLink";
import { Button } from "@/components/ui/Button";
import type { ChatSummary } from "@/types/hg";

function swarmOrchestrators(chats: ChatSummary[]) {
  const seen = new Set<string>();
  const rows: ChatSummary[] = [];
  for (const chat of chats) {
    const runId = chat.swarmRunId;
    if (!runId || chat.swarmRole !== "orchestrator") continue;
    if (seen.has(runId)) continue;
    seen.add(runId);
    rows.push(chat);
  }
  return rows.sort((a, b) => String(b.updatedAt).localeCompare(String(a.updatedAt)));
}

export function SwarmListView() {
  const { restored, operatorKey, impersonationToken, browserSession, locked } = useKeyRingStore();
  const ready = env.demoMode || (restored && !locked && (!!operatorKey || !!impersonationToken || !!browserSession));

  const { data: chats = [], isLoading, error, refetch } = useQuery({
    queryKey: ["chats", "swarm-list"],
    queryFn: () => hgApi.listChats(),
    enabled: ready,
  });

  const swarms = useMemo(() => swarmOrchestrators(chats), [chats]);

  return (
    <div className="mx-auto flex min-h-full max-w-4xl flex-col gap-6 px-6 py-10">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold">Swarm runs</h1>
        <p className="text-sm text-muted">
          Parallel multi-entity runs grouped by orchestrator. Start a swarm from the home workspace or sidebar.
        </p>
        <HardNavLink href="/" className="inline-flex text-sm text-accent">
          ← Back to workspace home
        </HardNavLink>
      </header>

      {!ready ? (
        <div className="rounded-2xl border border-border/70 bg-card/40 p-6 text-sm text-muted">
          Unlock operator credentials in Settings to list swarm runs.
        </div>
      ) : isLoading ? (
        <div className="text-sm text-muted">Loading swarm runs…</div>
      ) : error ? (
        <div className="rounded-2xl border border-danger/40 bg-card/40 p-6 text-sm">
          <p className="text-danger">Could not load swarm runs.</p>
          <Button className="mt-3" onClick={() => void refetch()}>
            Retry
          </Button>
        </div>
      ) : swarms.length === 0 ? (
        <div className="rounded-2xl border border-border/70 bg-card/40 p-6 text-sm text-muted">
          No swarm runs yet. Use the Swarm lane on the home page to launch parallel agents.
        </div>
      ) : (
        <ul className="divide-y divide-border/70 rounded-2xl border border-border/70 bg-card/40">
          {swarms.map((chat) => (
            <li key={chat.swarmRunId!} className="flex items-center justify-between gap-4 px-4 py-3">
              <div className="min-w-0">
                <div className="truncate font-medium">{chat.title || `Swarm ${chat.swarmRunId?.slice(0, 8)}`}</div>
                <div className="text-xs text-muted">
                  Run {chat.swarmRunId?.slice(0, 8)}… · updated {new Date(chat.updatedAt).toLocaleString()}
                </div>
              </div>
              <HardNavLink href={`/swarm/${encodeURIComponent(chat.swarmRunId!)}`} className="text-sm text-accent">
                Open swarm
              </HardNavLink>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
