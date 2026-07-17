"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEventChannel, visibilityAwareRefetchInterval } from "hg_ui_kit";
import { useVirtualizer } from "@tanstack/react-virtual";
import { hgApi } from "@/lib/hgApi";
import { getHeaders } from "@/lib/keyRing";
import { env } from "@/lib/env";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { appendReturnUrl, getCurrentPathWithSearch, readReturnUrl } from "@/lib/navigationContext";
import type { SwarmWorkspace, SwarmWorkspaceChat } from "@/types/hg";
import { SwarmProgressRail } from "@/components/swarm/SwarmProgressRail";
import { AgentCard, type AgentCardStatus } from "@/components/swarm/AgentCard";
import { useRef } from "react";

function mapStatus(status: SwarmWorkspaceChat["status"]): AgentCardStatus {
  if (status === "active") return "streaming";
  return status;
}

export function SwarmOrchestratorView({ swarmRunId }: { swarmRunId: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const qc = useQueryClient();
  const selectedChatFromUrl = searchParams.get("chat");
  const [returnUrl, setReturnUrl] = useState<string | null>(null);
  const [currentSwarmHref, setCurrentSwarmHref] = useState("");
  const [channelHealthy, setChannelHealthy] = useState(false);
  const agentListRef = useRef<HTMLDivElement>(null);

  const { data: workspace, isLoading } = useQuery({
    queryKey: ["swarm", swarmRunId],
    queryFn: () => hgApi.getSwarmWorkspace(swarmRunId),
    refetchInterval: (query) => (channelHealthy ? false : visibilityAwareRefetchInterval(15_000)),
  });

  const applyWorkspace = useCallback(
    (next: SwarmWorkspace) => {
      qc.setQueryData(["swarm", swarmRunId], next);
    },
    [qc, swarmRunId],
  );

  useEventChannel({
    streamUrl: hgApi.swarmStreamUrl(swarmRunId),
    enabled: !env.demoMode,
    headers: () => {
      const auth = getHeaders("operator", { baseUrl: env.apiBase || undefined, skipEnvCheck: false });
      return auth.ok ? auth.headers : {};
    },
    onEvent: (event) => {
      if (event.type !== "swarm.workspace") return;
      const payload = event.data as { workspace?: SwarmWorkspace };
      if (payload?.workspace) {
        applyWorkspace(payload.workspace);
        setChannelHealthy(true);
      }
    },
  });

  const participants = useMemo(
    () => [
      ...(workspace?.orchestrator ? [workspace.orchestrator] : []),
      ...(workspace?.members ?? []),
    ],
    [workspace],
  );
  const defaultSelectedChatId = workspace?.orchestrator?.id || workspace?.members?.[0]?.id || "";
  const selectedChatId = selectedChatFromUrl || defaultSelectedChatId;
  const selectedChat = participants.find((item) => item.id === selectedChatId) || workspace?.orchestrator || workspace?.members?.[0] || null;

  const { data: messages = [], isLoading: messagesLoading } = useQuery({
    queryKey: ["swarm-messages", selectedChat?.id],
    queryFn: () => hgApi.listMessages(selectedChat?.id || ""),
    enabled: !!selectedChat?.id,
    refetchInterval: channelHealthy ? false : visibilityAwareRefetchInterval(15_000),
  });

  useEffect(() => {
    const sync = () => {
      const search = typeof window === "undefined" ? "" : window.location.search || "";
      setReturnUrl(readReturnUrl(new URLSearchParams(search), ""));
      setCurrentSwarmHref(getCurrentPathWithSearch());
    };
    sync();
    window.addEventListener("popstate", sync);
    window.addEventListener("hashchange", sync);
    return () => {
      window.removeEventListener("popstate", sync);
      window.removeEventListener("hashchange", sync);
    };
  }, []);

  const virtualizer = useVirtualizer({
    count: participants.length,
    getScrollElement: () => agentListRef.current,
    estimateSize: () => 132,
    overscan: 4,
  });

  const selectParticipant = (participantId: string) => {
    const next = new URLSearchParams();
    next.set("chat", participantId);
    if (returnUrl) next.set("returnUrl", returnUrl);
    router.replace(`/swarm/${encodeURIComponent(swarmRunId)}?${next.toString()}`);
  };

  return (
    <div className="p-4 max-w-[1320px] mx-auto">
      <div className="mb-4">
        {returnUrl ? (
          <div className="mb-2">
            <Link href={returnUrl} className="text-sm text-accent hover:underline">Back to origin</Link>
          </div>
        ) : null}
        <div className="text-lg font-semibold">{workspace?.orchestrator?.title || "Swarm workspace"}</div>
        <div className="text-sm text-muted">Live agent cards with SSE workspace updates.</div>
        <div className="text-xs text-muted font-mono break-all mt-1">{swarmRunId}</div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-4">
          <SwarmProgressRail
            completed={workspace?.counts.completed ?? 0}
            total={participants.length}
            active={(workspace?.counts.active ?? 0) + (workspace?.counts.queued ?? 0)}
            errors={workspace?.counts.error ?? 0}
          />

          <Card className="p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <div className="font-semibold">{selectedChat?.title || "Transcript"}</div>
                <div className="text-sm text-muted">
                  {selectedChat?.swarmRole === "orchestrator" ? "Master thread" : "Member thread"} · {selectedChat?.status || "queued"}
                </div>
              </div>
              {selectedChat?.id ? (
                <Link href={appendReturnUrl(`/chat/${encodeURIComponent(selectedChat.id)}`, currentSwarmHref || `/swarm/${encodeURIComponent(swarmRunId)}`)}>
                  <Button tone="neutral">Open full chat</Button>
                </Link>
              ) : null}
            </div>
            <div className="space-y-3 max-h-[480px] overflow-y-auto">
              {messagesLoading ? <div className="text-sm text-muted">Loading transcript…</div> : null}
              {messages.map((message) => (
                <MessageBubble key={message.id} msg={message} />
              ))}
              {!messagesLoading && !messages.length ? <div className="text-sm text-muted">No messages yet.</div> : null}
            </div>
          </Card>
        </div>

        <Card className="p-4 h-fit">
          <div className="mb-3">
            <div className="font-semibold">Agents</div>
            <div className="text-sm text-muted">
              {channelHealthy ? "Live via SSE" : isLoading ? "Loading…" : "Polling fallback (15s)"}
            </div>
          </div>
          <div ref={agentListRef} className="max-h-[70vh] overflow-y-auto">
            <div style={{ height: virtualizer.getTotalSize(), position: "relative" }}>
              {virtualizer.getVirtualItems().map((row) => {
                const participant = participants[row.index];
                if (!participant) return null;
                return (
                  <div
                    key={participant.id}
                    style={{
                      position: "absolute",
                      top: 0,
                      left: 0,
                      width: "100%",
                      transform: `translateY(${row.start}px)`,
                      paddingBottom: 8,
                    }}
                  >
                    <AgentCard
                      title={participant.title}
                      role={participant.swarmRole === "orchestrator" ? "Master" : "Member"}
                      status={mapStatus(participant.status)}
                      content={participant.latestText}
                      isPrimary={participant.swarmRole === "orchestrator"}
                      selected={participant.id === selectedChat?.id}
                      agentIndex={row.index}
                      onSelect={() => selectParticipant(participant.id)}
                    />
                  </div>
                );
              })}
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
