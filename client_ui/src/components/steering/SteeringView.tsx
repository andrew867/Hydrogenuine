"use client";

import React, { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { hgApi } from "@/lib/hgApi";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { ChatSteeringSliders } from "@/components/chat/ChatSteeringSliders";

const STEERING_FRESH_WINDOW_MS = 14 * 24 * 60 * 60 * 1000;
const STEERING_MAX_VISIBLE = 40;

/** Steerable entities = chats from gateway (same source as sidebar). Prefer recent chats with persona. */
function useSteerableChats(showStale: boolean): {
  visible: { id: string; title: string; hasPersona: boolean; updatedAt: string }[];
  hiddenStaleCount: number;
} {
  const { data: chats } = useQuery({
    queryKey: ["chats"],
    queryFn: () => hgApi.listChats(),
  });
  const list = chats ?? [];
  const sorted = [...list].sort((a, b) => String(b.updatedAt || "").localeCompare(String(a.updatedAt || "")));
  const withPersona = sorted.filter((c) => c.fingerprintId != null && c.fingerprintId !== "");
  const preferred = withPersona.length > 0 ? withPersona : sorted;
  const cutoff = Date.now() - STEERING_FRESH_WINDOW_MS;
  const fresh = preferred.filter((c) => {
    const updatedAt = Date.parse(c.updatedAt || "");
    return Number.isFinite(updatedAt) && updatedAt >= cutoff;
  });
  const baseline = fresh.length > 0 ? fresh : preferred.slice(0, STEERING_MAX_VISIBLE);
  const visibleSource = showStale ? preferred : baseline.slice(0, STEERING_MAX_VISIBLE);
  const hiddenStaleCount = showStale ? 0 : Math.max(preferred.length - visibleSource.length, 0);
  return {
    visible: visibleSource.map((c) => ({
      id: c.id,
      title: c.title || c.id,
      hasPersona: Boolean(c.fingerprintId),
      updatedAt: c.updatedAt,
    })),
    hiddenStaleCount,
  };
}

export function SteeringView() {
  const [selectedChatId, setSelectedChatId] = useState<string | null>(null);
  const [showStale, setShowStale] = useState(false);
  const { visible, hiddenStaleCount } = useSteerableChats(showStale);
  const entities = useMemo(() => visible, [visible]);

  return (
    <div className="p-4 max-w-[980px] mx-auto">
      <div className="mb-4">
        <div className="text-lg font-semibold">Entity steering</div>
        <div className="text-sm text-muted">
          Steering defaults to recent chats with personas first. Old chat debris stays hidden unless you ask for it.
        </div>
      </div>

      <div className="flex gap-4 flex-col sm:flex-row">
        <Card className="sm:w-64 shrink-0">
          <div className="flex items-center justify-between gap-2 mb-2">
            <div className="font-semibold">Chats / entities</div>
            {hiddenStaleCount > 0 ? (
              <button
                type="button"
                onClick={() => setShowStale((v) => !v)}
                className="text-xs text-muted hover:text-text"
              >
                {showStale ? "Hide stale" : `Show stale (${hiddenStaleCount})`}
              </button>
            ) : null}
          </div>
          <div className="space-y-1">
            {entities.map((e) => (
              <button
                key={e.id}
                onClick={() => setSelectedChatId(e.id)}
                className={`block w-full text-left rounded-xl px-3 py-2 text-sm border transition ${
                  selectedChatId === e.id ? "bg-accent/15 border-accent/50" : "border-border/70 hover:bg-card/60"
                }`}
              >
                <span className="truncate block">{e.title}</span>
                {e.hasPersona && <span className="text-xs text-muted">persona</span>}
              </button>
            ))}
            {!entities.length ? <div className="text-sm text-muted">No chats yet. Create a chat (with persona) from the sidebar.</div> : null}
          </div>
        </Card>

        {selectedChatId ? (
          <Card className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-4">
              <div className="font-semibold truncate">{entities.find((e) => e.id === selectedChatId)?.title ?? selectedChatId}</div>
              <div className="flex gap-2 shrink-0">
                <Link href={`/chat/${selectedChatId}`}>
                  <Button tone="neutral">Open chat</Button>
                </Link>
                <Button tone="neutral" onClick={() => setSelectedChatId(null)}>Close</Button>
              </div>
            </div>
            <ChatSteeringSliders chatId={selectedChatId} />
          </Card>
        ) : (
          <Card className="flex-1 flex items-center justify-center text-muted">
            Select a chat to edit steering (trait sliders).
          </Card>
        )}
      </div>
    </div>
  );
}
