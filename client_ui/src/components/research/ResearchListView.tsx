"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { hgApi } from "@/lib/hgApi";
import { useKeyRingStore } from "@/store/keyRingStore";
import { env } from "@/lib/env";
import { HardNavLink } from "@/components/navigation/HardNavLink";
import { Button } from "@/components/ui/Button";
import type { ChatSummary } from "@/types/hg";

function byLatest(a: ChatSummary, b: ChatSummary) {
  return String(b.updatedAt).localeCompare(String(a.updatedAt));
}

export function ResearchListView() {
  const router = useRouter();
  const { restored, operatorKey, impersonationToken, browserSession, locked } = useKeyRingStore();
  const ready = env.demoMode || (restored && !locked && (!!operatorKey || !!impersonationToken || !!browserSession));

  const { data: chats = [], isLoading, error, refetch } = useQuery({
    queryKey: ["chats", "research-list"],
    queryFn: () => hgApi.listChats(),
    enabled: ready,
  });

  const startResearch = async () => {
    const created = await hgApi.createChat("Research workspace");
    router.push(`/research/${encodeURIComponent(created.chat_id)}`);
  };

  return (
    <div className="mx-auto flex min-h-full max-w-4xl flex-col gap-6 px-6 py-10">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold">Research workspaces</h1>
        <p className="text-sm text-muted">
          Open a document-backed research thread, upload sources, and run retrieval workflows.
        </p>
        <Button onClick={startResearch}>Start new research workspace</Button>
      </header>

      {!ready ? (
        <div className="rounded-2xl border border-border/70 bg-card/40 p-6 text-sm text-muted">
          Unlock operator credentials in Settings to load research workspaces.
        </div>
      ) : isLoading ? (
        <div className="text-sm text-muted">Loading workspaces…</div>
      ) : error ? (
        <div className="rounded-2xl border border-danger/40 bg-card/40 p-6 text-sm">
          <p className="text-danger">Could not load research workspaces.</p>
          <Button className="mt-3" onClick={() => void refetch()}>
            Retry
          </Button>
        </div>
      ) : chats.length === 0 ? (
        <div className="rounded-2xl border border-border/70 bg-card/40 p-6 text-sm text-muted">
          No chats yet. Start a research workspace to upload documents and run structured retrieval.
        </div>
      ) : (
        <ul className="divide-y divide-border/70 rounded-2xl border border-border/70 bg-card/40">
          {[...chats].sort(byLatest).map((chat) => (
            <li key={chat.id} className="flex items-center justify-between gap-4 px-4 py-3">
              <div className="min-w-0">
                <div className="truncate font-medium">{chat.title}</div>
                <div className="text-xs text-muted">Updated {new Date(chat.updatedAt).toLocaleString()}</div>
              </div>
              <HardNavLink href={`/research/${encodeURIComponent(chat.id)}`} className="text-sm text-accent">
                Open research
              </HardNavLink>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
