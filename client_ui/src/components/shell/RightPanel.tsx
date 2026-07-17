"use client";

import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { AgentPanel } from "@/components/agent/AgentPanel";
import { ActivityPanel } from "@/components/tools/ActivityPanel";
import { ChatSteeringSliders } from "@/components/chat/ChatSteeringSliders";
import { DocumentSidebar } from "@/components/documents/DocumentSidebar";
import { HardNavLink } from "@/components/navigation/HardNavLink";
import { hgApi } from "@/lib/hgApi";
import { useKeyRingStore } from "@/store/keyRingStore";
import { env } from "@/lib/env";
import { visibilityAwareRefetchInterval } from "hg_ui_kit";

export function RightPanel() {
  const path = usePathname();
  const match = path?.match(/^\/chat\/(.+)$/);
  const chatId = match?.[1] ? decodeURIComponent(match[1]) : null;
  const { restored, operatorKey, impersonationToken, browserSession, locked } = useKeyRingStore();
  const personaReady = env.demoMode || (restored && !locked && (!!operatorKey || !!impersonationToken || !!browserSession));
  const { data: chat } = useQuery({
    queryKey: ["chat", chatId],
    queryFn: () => hgApi.getChat(chatId || ""),
    enabled: !!chatId,
  });
  const { data: personas = [] } = useQuery({
    queryKey: ["personas"],
    queryFn: () => hgApi.listPersonas(),
    enabled: !!chatId && personaReady,
  });
  const { data: swarm } = useQuery({
    queryKey: ["swarm", chat?.swarmRunId],
    queryFn: () => hgApi.getSwarmWorkspace(chat?.swarmRunId || ""),
    enabled: !!chat?.swarmRunId,
    refetchInterval: visibilityAwareRefetchInterval(15_000),
  });

  const selectedPersona = personas.find((item) => item.fingerprint_id === (chat?.fingerprint_id || chat?.fingerprintId));
  const selectedSkin = selectedPersona?.skins.find((item) => item.id === (chat?.skin_id || chat?.skinId));
  const temporaryPersona = personas.find((item) => item.fingerprint_id === chat?.temporary_fingerprint_id);
  const temporarySkin = temporaryPersona?.skins.find((item) => item.id === chat?.temporary_skin_id);
  const participants = [
    ...(swarm?.orchestrator ? [swarm.orchestrator] : []),
    ...(swarm?.members ?? []),
  ];
  if (!chatId) return null;

  return (
    <aside className="w-[360px] max-w-[88vw] border-l border-border/80 bg-bg/60 backdrop-blur overflow-y-auto">
      <div className="p-3">
        <div className="text-sm font-semibold">Details</div>
        <div className="text-xs text-muted">Agents, tool timeline, documents, safety and approvals</div>
      </div>
      <div className="px-3 pb-4 space-y-4">
        {selectedPersona || selectedSkin ? (
          <div className="rounded-2xl border border-border/70 bg-card/50 p-3">
            <div className="text-xs uppercase tracking-wide text-muted">Active persona</div>
            <div className="mt-2 font-semibold">{selectedPersona?.name || "Default assistant"}</div>
            <div className="mt-1 text-sm text-muted">{selectedSkin?.name || "Base skin"}</div>
            {temporaryPersona ? (
              <div className="mt-3 rounded-xl border border-amber-400/30 bg-amber-400/10 px-3 py-2 text-sm text-amber-100">
                Temporary steering: {temporaryPersona.name}{temporarySkin ? ` · ${temporarySkin.name}` : ""} for {chat?.temporary_turns_remaining ?? 0} more turn(s)
              </div>
            ) : null}
          </div>
        ) : null}
        <div className="rounded-2xl border border-border/70 bg-card/50 p-3">
          <ChatSteeringSliders chatId={chatId} />
        </div>
        {chat?.swarmRunId && swarm ? (
          <div className="rounded-2xl border border-border/70 bg-card/50 p-3">
            <div className="flex items-center justify-between gap-2">
              <div>
                <div className="font-semibold">Swarm participants</div>
                <div className="text-xs text-muted">Master and member chats in this run</div>
              </div>
              <HardNavLink
                href={`/swarm/${encodeURIComponent(chat.swarmRunId ?? "")}`}
                className="text-xs text-accent hover:underline"
              >
                Open workspace
              </HardNavLink>
            </div>
            <div className="mt-3 space-y-2">
              {participants.map((participant) => {
                const href = `/chat/${encodeURIComponent(participant.id)}`;
                const isCurrent = participant.id === chatId;
                return (
                  <HardNavLink
                    key={participant.id}
                    className={`block w-full text-left rounded-xl border px-3 py-2 ${isCurrent ? "border-accent/50 bg-accent/10" : "border-border/70 bg-bg/40 hover:bg-card/60"}`}
                    href={href}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="min-w-0">
                        <div className="truncate font-medium">{participant.title}</div>
                        <div className="text-[11px] uppercase tracking-wide text-muted">
                          {participant.swarmRole === "orchestrator" ? "Master" : "Member"} · {participant.status}
                        </div>
                      </div>
                    </div>
                  </HardNavLink>
                );
              })}
            </div>
          </div>
        ) : null}
        <div className="border-b border-border/70 pb-4">
          <DocumentSidebar chatId={chatId} />
        </div>
        <AgentPanel chatId={chatId} />
        <ActivityPanel chatId={chatId} />
      </div>
    </aside>
  );
}
