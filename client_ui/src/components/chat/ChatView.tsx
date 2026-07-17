"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useVirtualizer } from "@tanstack/react-virtual";
import { useEventChannel, visibilityAwareRefetchInterval } from "hg_ui_kit";
import { hgApi } from "@/lib/hgApi";
import { getHeaders } from "@/lib/keyRing";
import { personaTypeLabel } from "@/lib/personaGroups";
import { ChatComposer } from "@/components/chat/ChatComposer";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { PersonaPicker } from "@/components/chat/PersonaPicker";
import { Icon } from "@/components/ui/Icon";
import { Badge } from "@/components/ui/Badge";
import { DocumentViewer } from "@/components/documents/DocumentViewer";
import { SourceEvidenceCards } from "@/components/chat/SourceEvidenceCards";
import { openSSE, type StreamEvent } from "@/lib/streaming";
import type { Citation, MessageProvenance } from "@/types/hg";
import { useKeyRingStore } from "@/store/keyRingStore";
import { env } from "@/lib/env";
import type { HgMessage, SwarmWorkspace } from "@/types/hg";
import { HardNavLink } from "@/components/navigation/HardNavLink";
import { readReturnUrl } from "@/lib/navigationContext";
import {
  ApprovalCard,
  ConfirmDialog,
  JumpToBottomFab,
  PageSkeleton,
  TypingIndicator,
  type ApprovalCardItem,
} from "hg_ui_kit";
import { StepupApprovalModal, type StepupApprovalRequest } from "@/components/auth/StepupApprovalModal";

function provenanceCount(items: unknown): number {
  return Array.isArray(items) ? items.length : 0;
}

function ChatMessageList({
  messages,
  pendingUserMessages,
  chatId,
  scrollRef,
  onRetry,
  onWhyClick,
  onCitationClick,
}: {
  messages?: HgMessage[];
  pendingUserMessages: Array<{ id: string; content: string; createdAt: string; deliveryState: "pending" | "accepted" | "responding" | "error" }>;
  chatId: string;
  scrollRef: React.RefObject<HTMLDivElement | null>;
  onRetry: () => void;
  onWhyClick: (messageId: string) => void;
  onCitationClick: (c: Citation) => void;
}) {
  const allMessages = useMemo(
    () => [
      ...(messages || []),
      ...pendingUserMessages.map((item) => ({
        id: item.id,
        chatId,
        role: "user" as const,
        createdAt: item.createdAt,
        content: item.content,
        deliveryState: item.deliveryState,
      })),
    ],
    [chatId, messages, pendingUserMessages],
  );
  const useVirtual = allMessages.length > 50;
  const virtualizer = useVirtualizer({
    count: allMessages.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => 128,
    overscan: 6,
  });

  if (!useVirtual) {
    return (
      <>
        {allMessages.map((m) => (
          <MessageBubble
            key={m.id}
            msg={m}
            onRetry={onRetry}
            onWhyClick={m.role === "assistant" ? () => onWhyClick(m.id) : undefined}
            onCitationClick={onCitationClick}
          />
        ))}
      </>
    );
  }

  return (
    <div style={{ height: virtualizer.getTotalSize(), position: "relative", width: "100%" }}>
      {virtualizer.getVirtualItems().map((virtualRow) => {
        const m = allMessages[virtualRow.index];
        return (
          <div
            key={m.id}
            data-index={virtualRow.index}
            ref={virtualizer.measureElement}
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              transform: `translateY(${virtualRow.start}px)`,
            }}
          >
            <MessageBubble
              msg={m}
              onRetry={onRetry}
              onWhyClick={m.role === "assistant" ? () => onWhyClick(m.id) : undefined}
              onCitationClick={onCitationClick}
            />
          </div>
        );
      })}
    </div>
  );
}

export function ChatView({ chatId }: { chatId: string }) {
  const qc = useQueryClient();
  const streamingRef = useRef("");
  const [streamTick, setStreamTick] = useState(0);
  const [isStreamingActive, setIsStreamingActive] = useState(false);
  const streamRafRef = useRef<number | null>(null);
  const [streamConnected, setStreamConnected] = useState(false);
  const [swarmChannelHealthy, setSwarmChannelHealthy] = useState(false);
  const [agentThought, setAgentThought] = useState<string | null>(null);
  const [viewCitation, setViewCitation] = useState<Citation | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportFileName, setExportFileName] = useState<string | null>(null);
  const [personaConfirmOpen, setPersonaConfirmOpen] = useState(false);
  const [showJumpFab, setShowJumpFab] = useState(false);
  const [chatApproval, setChatApproval] = useState<ApprovalCardItem | null>(null);
  const [approvalBusy, setApprovalBusy] = useState(false);
  const [approvalError, setApprovalError] = useState<string | null>(null);
  const [stepupRequest, setStepupRequest] = useState<StepupApprovalRequest | null>(null);
  const [showPersonaEditor, setShowPersonaEditor] = useState(false);
  const [draftFingerprintId, setDraftFingerprintId] = useState("");
  const [draftSkinId, setDraftSkinId] = useState("");
  const [draftApplyMode, setDraftApplyMode] = useState<"permanent" | "temporary">("permanent");
  const [draftTurnCount, setDraftTurnCount] = useState(3);
  const [savingPersona, setSavingPersona] = useState(false);
  const [pendingUserMessages, setPendingUserMessages] = useState<Array<{ id: string; content: string; createdAt: string; deliveryState: "pending" | "accepted" | "responding" | "error" }>>([]);
  const [responsePhase, setResponsePhase] = useState<"idle" | "sending" | "accepted" | "responding" | "error">("idle");
  const [liveToolEvents, setLiveToolEvents] = useState<Array<{ id: string; name: string; status: "running" | "ok" | "error"; detail?: string }>>([]);
  const [liveActivity, setLiveActivity] = useState<Array<{ id: string; kind: "thinking" | "tool" | "approval" | "steering"; label: string; detail?: string; status?: "running" | "ok" | "error" }>>([]);
  const [selectedProvenance, setSelectedProvenance] = useState<MessageProvenance | null>(null);
  const [selectedProvenanceLoading, setSelectedProvenanceLoading] = useState(false);
  const closeStreamRef = useRef<(() => void) | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const shouldStickToBottomRef = useRef(true);
  const searchParams = useSearchParams();
  const returnUrl = readReturnUrl(searchParams, "");
  const { restored, operatorKey, impersonationToken, browserSession, locked } = useKeyRingStore();
  const personaReady = env.demoMode || (restored && !locked && (!!operatorKey || !!impersonationToken || !!browserSession));
  const provenanceMessageId = searchParams.get("message_id") || "";

  const { data: chat } = useQuery({ queryKey: ["chat", chatId], queryFn: () => hgApi.getChat(chatId) });
  const { data: personas = [], isLoading: personasLoading } = useQuery({
    queryKey: ["personas"],
    queryFn: () => hgApi.listPersonas(),
    enabled: personaReady,
  });
  const bumpStreamTick = useCallback(() => {
    if (streamRafRef.current != null) return;
    streamRafRef.current = window.requestAnimationFrame(() => {
      streamRafRef.current = null;
      setStreamTick((tick) => tick + 1);
    });
  }, []);

  const { data: messages, isLoading } = useQuery({
    queryKey: ["messages", chatId],
    queryFn: () => hgApi.listMessages(chatId),
    refetchInterval: streamConnected || agentThought || isStreamingActive
      ? false
      : visibilityAwareRefetchInterval(30_000),
  });
  const { data: swarmWorkspace } = useQuery({
    queryKey: ["swarm", chat?.swarmRunId],
    queryFn: () => hgApi.getSwarmWorkspace(chat?.swarmRunId || ""),
    enabled: !!chat?.swarmRunId,
    refetchInterval: swarmChannelHealthy ? false : visibilityAwareRefetchInterval(15_000),
  });

  useEventChannel({
    streamUrl: chat?.swarmRunId ? hgApi.swarmStreamUrl(chat.swarmRunId) : "",
    enabled: !!chat?.swarmRunId && !env.demoMode,
    headers: () => {
      const auth = getHeaders("operator", { baseUrl: env.apiBase || undefined, skipEnvCheck: false });
      return auth.ok ? auth.headers : {};
    },
    onEvent: (event) => {
      if (event.type !== "swarm.workspace" || !chat?.swarmRunId) return;
      const payload = event.data as { workspace?: SwarmWorkspace };
      if (payload?.workspace) {
        qc.setQueryData(["swarm", chat.swarmRunId], payload.workspace);
        setSwarmChannelHealthy(true);
      }
    },
  });

  const hasAssistantReply = React.useMemo(() => {
    const list = messages ?? [];
    return list.some((item) => item.role === "assistant" && (item.content || "").trim().length > 0);
  }, [messages]);

  useEffect(() => {
    const node = scrollRef.current;
    if (!node) return;
    const onWheel = (event: WheelEvent) => {
      if (event.deltaY < 0) {
        shouldStickToBottomRef.current = false;
      }
    };
    const onScroll = () => {
      const distanceFromBottom = node.scrollHeight - node.scrollTop - node.clientHeight;
      shouldStickToBottomRef.current = distanceFromBottom < 56;
      setShowJumpFab(distanceFromBottom > 120);
    };
    onScroll();
    node.addEventListener("wheel", onWheel, { passive: true });
    node.addEventListener("scroll", onScroll);
    return () => {
      node.removeEventListener("wheel", onWheel);
      node.removeEventListener("scroll", onScroll);
    };
  }, [chatId]);

  useEffect(() => {
    shouldStickToBottomRef.current = true;
  }, [chatId]);

  useEffect(() => {
    setSelectedProvenance(null);
  }, [chatId]);

  useEffect(() => {
    const list = messages ?? [];
    if (!list.length || !pendingUserMessages.length) return;
    const latestAssistant = [...list].reverse().find((item) => item.role === "assistant" && (item.content || "").trim());
    if (!latestAssistant) return;
    setPendingUserMessages([]);
    setLiveToolEvents((prev) => prev.map((item) => ({ ...item, status: item.status === "running" ? "ok" : item.status })));
    streamingRef.current = "";
    setIsStreamingActive(false);
    setAgentThought(null);
    setResponsePhase("idle");
  }, [messages, pendingUserMessages.length]);

  useEffect(() => {
    const hasRunningTools = liveToolEvents.some((item) => item.status === "running");
    if (!isStreamingActive && !agentThought && !hasRunningTools && hasAssistantReply) {
      setResponsePhase("idle");
      setPendingUserMessages([]);
      setLiveToolEvents((prev) => prev.map((item) => ({ ...item, status: item.status === "running" ? "ok" : item.status })));
      setLiveActivity((prev) =>
        prev.map((item) => ({
          ...item,
          status: item.status === "running" ? "ok" : item.status,
        }))
      );
    }
  }, [agentThought, hasAssistantReply, isStreamingActive, liveToolEvents]);

  const openProvenance = useCallback(async (messageId: string) => {
    if (!messageId) return;
    setSelectedProvenanceLoading(true);
    try {
      const provenance = await hgApi.getMessageProvenance(chatId, messageId);
      setSelectedProvenance(provenance);
    } catch {
      setSelectedProvenance(null);
    } finally {
      setSelectedProvenanceLoading(false);
    }
  }, [chatId]);

  useEffect(() => {
    if (!provenanceMessageId) return;
    void openProvenance(provenanceMessageId);
  }, [openProvenance, provenanceMessageId]);

  useEffect(() => {
    const node = scrollRef.current;
    if (!node || !shouldStickToBottomRef.current) return;
    const raf = window.requestAnimationFrame(() => {
      node.scrollTop = node.scrollHeight;
    });
    return () => window.cancelAnimationFrame(raf);
  }, [messages, pendingUserMessages, streamTick, isStreamingActive, liveActivity.length]);

  const onRetry = useCallback(async () => {
    const list = messages ?? [];
    const lastUser = [...list].reverse().find((m) => m.role === "user");
    if (lastUser?.content?.trim()) {
      await hgApi.sendMessage(chatId, lastUser.content.trim());
      await qc.invalidateQueries({ queryKey: ["messages", chatId] });
      await qc.invalidateQueries({ queryKey: ["chats"] });
    }
  }, [chatId, messages, qc]);

  useEffect(() => {
    if (!chatId) return;
    const pushActivity = (item: { id: string; kind: "thinking" | "tool" | "approval" | "steering"; label: string; detail?: string; status?: "running" | "ok" | "error" }) => {
      setLiveActivity((prev) => [...prev.filter((existing) => existing.id !== item.id), item].slice(-8));
    };
    const onEvent = (event: StreamEvent) => {
      if (event.type === "message.delta") {
        setResponsePhase("responding");
        setPendingUserMessages((prev) => prev.map((item) => ({ ...item, deliveryState: "responding" })));
        streamingRef.current += event.delta;
        setIsStreamingActive(true);
        bumpStreamTick();
      } else if (event.type === "message.final") {
        setResponsePhase("idle");
        setPendingUserMessages([]);
        setLiveToolEvents((prev) => prev.map((item) => ({ ...item, status: item.status === "running" ? "ok" : item.status })));
        setLiveActivity((prev) => prev.map((item) => ({ ...item, status: item.status === "running" ? "ok" : item.status })));
        streamingRef.current = "";
        setIsStreamingActive(false);
        setStreamTick((tick) => tick + 1);
        setAgentThought(null);
        void qc.invalidateQueries({ queryKey: ["messages", chatId] });
        void qc.invalidateQueries({ queryKey: ["agents", chatId] });
        void qc.invalidateQueries({ queryKey: ["chat", chatId] });
        void qc.invalidateQueries({ queryKey: ["chats"] });
      } else if (event.type === "agent.status") {
        setAgentThought(event.thought ?? null);
        if (event.status === "idle" && !event.thought) {
          setResponsePhase((prev) => (prev === "error" ? prev : "idle"));
        }
        if (event.thought) {
          pushActivity({
            id: `thinking-${event.agentId}`,
            kind: "thinking",
            label: event.label || "Agent",
            detail: event.thought,
            status: event.status === "error" ? "error" : event.status === "working" ? "running" : "ok",
          });
        }
        void qc.invalidateQueries({ queryKey: ["agents", chatId] });
      } else if (event.type === "agent.thinking") {
        setResponsePhase("responding");
        setAgentThought(event.thought);
        pushActivity({
          id: `thinking-${event.agentId}`,
          kind: "thinking",
          label: "Thinking",
          detail: event.thought,
          status: "running",
        });
      } else if (event.type === "steering_applied") {
        pushActivity({
          id: `steering-${Date.now()}`,
          kind: "steering",
          label: "Persona steering applied",
          detail: event.profileIds.length ? event.profileIds.join(", ") : "Profile fragments injected",
          status: "ok",
        });
      } else if (event.type === "tool.start") {
        setLiveToolEvents((prev) => [...prev.slice(-7), { id: `${Date.now()}-${event.name}`, name: event.name, status: "running" }]);
        pushActivity({
          id: `tool-${event.name}`,
          kind: "tool",
          label: event.name,
          detail: "Running",
          status: "running",
        });
      } else if (event.type === "tool.result") {
        const toolFailed = typeof event.result === "object" && event.result !== null && "ok" in event.result
          ? (event.result as { ok?: boolean }).ok === false
          : false;
        setLiveToolEvents((prev) => {
          const next = [...prev];
          const index = [...next].reverse().findIndex((item) => item.name === event.name && item.status === "running");
          if (index >= 0) {
            const actual = next.length - 1 - index;
            next[actual] = { ...next[actual], status: toolFailed ? "error" : "ok", detail: typeof event.result === "string" ? event.result : undefined };
            return next;
          }
          return [...next.slice(-7), { id: `${Date.now()}-${event.name}`, name: event.name, status: toolFailed ? "error" : "ok" }];
        });
        pushActivity({
          id: `tool-${event.name}`,
          kind: "tool",
          label: event.name,
          detail: typeof event.result === "string" ? event.result : "Completed",
          status: toolFailed ? "error" : "ok",
        });
      } else if (event.type === "approval.created") {
        const approval = event.approval as Record<string, unknown> | null;
        const approvalId = String(approval?.id || approval?.approval_id || `approval-${Date.now()}`);
        setChatApproval({
          id: approvalId,
          title: typeof approval?.title === "string" ? approval.title : "Approval required to continue",
          summary: typeof approval?.summary === "string" ? approval.summary : "Review this request before the assistant can continue.",
          kind: typeof approval?.kind === "string" ? approval.kind : "approval",
          risk: typeof approval?.risk === "string" ? approval.risk : "medium",
        });
        pushActivity({
          id: `approval-${approvalId}`,
          kind: "approval",
          label: "Approval requested",
          detail: typeof approval?.kind === "string" ? approval.kind : "Review required before continuing",
          status: "running",
        });
      }
    };
    setStreamConnected(true);
    closeStreamRef.current = openSSE(chatId, onEvent);
    return () => {
      closeStreamRef.current?.();
      closeStreamRef.current = null;
      setStreamConnected(false);
      streamingRef.current = "";
      setIsStreamingActive(false);
      setAgentThought(null);
      setLiveToolEvents([]);
      setLiveActivity([]);
    };
  }, [bumpStreamTick, chatId, qc]);

  const handleSend = useCallback(async (content: string) => {
    const optimisticId = `pending-${Date.now()}`;
    const createdAt = new Date().toISOString();
    setPendingUserMessages((prev) => [...prev, { id: optimisticId, content, createdAt, deliveryState: "pending" }]);
    setResponsePhase("sending");
    try {
      await hgApi.sendMessage(chatId, content);
      setPendingUserMessages((prev) => prev.map((item) => item.id === optimisticId ? { ...item, deliveryState: "accepted" } : item));
      setResponsePhase("accepted");
      window.setTimeout(() => {
        setPendingUserMessages((prev) => prev.map((item) => item.id === optimisticId && item.deliveryState === "accepted"
          ? { ...item, deliveryState: "responding" }
          : item));
        setResponsePhase((prev) => (prev === "accepted" ? "responding" : prev));
      }, 1800);
      await qc.invalidateQueries({ queryKey: ["messages", chatId] });
      await qc.invalidateQueries({ queryKey: ["chat", chatId] });
      await qc.invalidateQueries({ queryKey: ["chats"] });
    } catch (error) {
      setPendingUserMessages((prev) => prev.map((item) => item.id === optimisticId ? { ...item, deliveryState: "error" } : item));
      setResponsePhase("error");
      throw error;
    }
  }, [chatId, qc]);

  const title = chat?.title || chatId;
  const selectedPersona = personas.find((item) => item.fingerprint_id === chat?.fingerprint_id || item.fingerprint_id === chat?.fingerprintId);
  const selectedSkin = selectedPersona?.skins.find((item) => item.id === chat?.skin_id || item.id === chat?.skinId);
  const temporaryPersona = personas.find((item) => item.fingerprint_id === chat?.temporary_fingerprint_id);
  const temporarySkin = temporaryPersona?.skins.find((item) => item.id === chat?.temporary_skin_id);
  const currentFingerprintId = chat?.fingerprint_id || chat?.fingerprintId || "";
  const currentSkinId = chat?.skin_id || chat?.skinId || "";
  const hasManualSteering = Boolean(chat?.traitOverrides && Object.keys(chat.traitOverrides).length);
  const selectedProvenanceCounts = selectedProvenance ? {
    retrieval: provenanceCount(selectedProvenance.source_groups?.retrieval),
    policy: provenanceCount(selectedProvenance.source_groups?.policy),
    evidence: provenanceCount(selectedProvenance.source_groups?.evidence),
    reflection: provenanceCount(selectedProvenance.source_groups?.reflection),
    mirroring: provenanceCount(selectedProvenance.source_groups?.user_mirroring),
    inference: provenanceCount(selectedProvenance.source_groups?.inference),
  } : null;

  useEffect(() => {
    setDraftFingerprintId(currentFingerprintId);
    setDraftSkinId(currentSkinId);
    setDraftApplyMode("permanent");
    setDraftTurnCount(chat?.temporary_turns_remaining || 3);
  }, [chat?.temporary_turns_remaining, currentFingerprintId, currentSkinId]);

  const scrollToBottom = useCallback(() => {
    const node = scrollRef.current;
    if (!node) return;
    shouldStickToBottomRef.current = true;
    node.scrollTop = node.scrollHeight;
    setShowJumpFab(false);
  }, []);

  const resolveChatApproval = useCallback(async (decision: "approve" | "deny", note: string) => {
    if (!chatApproval) return;
    setApprovalBusy(true);
    setApprovalError(null);
    try {
      await hgApi.resolveApproval(chatApproval.id, decision, note);
      setChatApproval(null);
      setLiveActivity((prev) => prev.map((item) => (item.kind === "approval" ? { ...item, status: "ok" } : item)));
      await qc.invalidateQueries({ queryKey: ["messages", chatId] });
      await qc.invalidateQueries({ queryKey: ["chat", chatId] });
    } catch (error) {
      const typed = error as Error & { code?: string };
      if (typed.code === "stepup_required") {
        setStepupRequest({ approvalId: chatApproval.id, decision, note });
        return;
      }
      setApprovalError(typed.message || "Approval action failed.");
      throw error;
    } finally {
      setApprovalBusy(false);
    }
  }, [chatApproval, chatId, qc]);

  const handleExportDocx = useCallback(async () => {
    setExporting(true);
    setExportFileName(null);
    try {
      const transcript = (messages ?? []).filter((item) => {
        if (item.role === "tool") return false;
        return (item.content || "").trim().length > 0;
      });
      const sections = transcript.length > 0
        ? transcript.map((item: HgMessage) => ({
            heading: item.role === "user" ? "User" : item.role === "assistant" ? "Assistant" : item.role === "system" ? "System" : "Message",
            text: item.content,
            level: 2,
          }))
        : [{ heading: "Conversation", text: "No transcript content was available for export.", level: 2 }];
      const res = await hgApi.createExportDocx({ title: `${title} — Export`, sections });
      const downloadName = `${(res.title || title || "Export").replace(/[^a-zA-Z0-9._-]/g, "_")}-${new Date().toISOString().slice(0, 10)}.docx`;
      setExportFileName(downloadName);
      const blob = await hgApi.fetchFileBlob(res.file_id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = downloadName;
      a.click();
      URL.revokeObjectURL(url);
    } catch (_) {
      // Error surfaced by API
    } finally {
      setExporting(false);
      window.setTimeout(() => setExportFileName(null), 4000);
    }
  }, [messages, title]);

  const applyPersonaSave = useCallback(async () => {
    setSavingPersona(true);
    try {
      await hgApi.patchChat(chatId, {
        fingerprint_id: draftApplyMode === "permanent" ? draftFingerprintId || null : currentFingerprintId || null,
        skin_id: draftApplyMode === "permanent" ? draftSkinId || null : currentSkinId || null,
        temporary_fingerprint_id: draftApplyMode === "temporary" ? draftFingerprintId || null : null,
        temporary_skin_id: draftApplyMode === "temporary" ? draftSkinId || null : null,
        temporary_turns_remaining: draftApplyMode === "temporary" ? draftTurnCount : null,
      });
      await qc.invalidateQueries({ queryKey: ["chat", chatId] });
      await qc.invalidateQueries({ queryKey: ["chats"] });
      setShowPersonaEditor(false);
    } finally {
      setSavingPersona(false);
    }
  }, [chatId, currentFingerprintId, currentSkinId, draftFingerprintId, draftSkinId, draftApplyMode, draftTurnCount, qc]);

  const handlePersonaSave = useCallback(() => {
    const personaChanged = draftFingerprintId !== currentFingerprintId || draftSkinId !== currentSkinId;
    if (personaChanged && hasManualSteering) {
      setPersonaConfirmOpen(true);
      return;
    }
    void applyPersonaSave();
  }, [applyPersonaSave, currentFingerprintId, currentSkinId, draftFingerprintId, draftSkinId, hasManualSteering]);

  const isTyping = responsePhase === "responding" || responsePhase === "accepted" || isStreamingActive || !!agentThought;

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 py-3 border-b border-border/70 bg-bg/30 backdrop-blur sticky top-0 z-10">
        {returnUrl ? (
          <div className="mb-2">
            <HardNavLink href={returnUrl} className="text-sm text-accent hover:underline">Back to origin</HardNavLink>
          </div>
        ) : null}
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <div className="font-semibold truncate">{title}</div>
            <div className="text-xs text-muted truncate">
              {agentThought || (responsePhase === "sending" ? "Sending your message…" : responsePhase === "accepted" ? "Message accepted. Waiting for response…" : responsePhase === "responding" ? "Responding…" : chat?.subtitle || "Chat")}
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              {selectedPersona ? <Badge tone="neutral">Persona {selectedPersona.name}</Badge> : null}
              {selectedSkin ? <Badge tone="neutral">Skin {selectedSkin.name}</Badge> : null}
              <HardNavLink
                href={`/research/${encodeURIComponent(chatId)}`}
                className="inline-flex rounded-full border border-border/70 px-2 py-0.5 text-[11px] uppercase tracking-wide text-muted hover:bg-card/60"
              >
                Research workspace
              </HardNavLink>
              {temporaryPersona ? (
                <Badge tone="warning">
                  Temporary {temporaryPersona.name}{temporarySkin ? ` · ${temporarySkin.name}` : ""} · {chat?.temporary_turns_remaining ?? 0} turn(s) left
                </Badge>
              ) : null}
              {chat?.swarmRunId ? (
                <HardNavLink
                  href={`/swarm/${encodeURIComponent(chat.swarmRunId ?? "")}`}
                  className="inline-flex rounded-full border border-border/70 px-2 py-0.5 text-[11px] uppercase tracking-wide text-muted hover:bg-card/60"
                >
                  {chat.swarmRole === "orchestrator" ? "Swarm master" : "Swarm member"}
                </HardNavLink>
              ) : null}
            </div>
          </div>
          <div className="flex items-center gap-1">
            <button
              className="px-3 py-2 rounded-2xl border border-border/70 bg-card/60 hover:border-accent/60 text-sm"
              title="Change persona"
              onClick={() => setShowPersonaEditor((value) => !value)}
            >
              Persona
            </button>
            <button
              className="p-2 rounded-2xl border border-border/70 bg-card/60 hover:border-accent/60 disabled:opacity-50"
              title={exporting ? "Exporting DOCX…" : exportFileName ? `Exported ${exportFileName}` : "Export as DOCX"}
              onClick={() => void handleExportDocx()}
              disabled={exporting}
              aria-busy={exporting}
            >
              <Icon name="download" className="h-5 w-5" />
            </button>
            <button
              className="p-2 rounded-2xl border border-border/70 bg-card/60 hover:border-accent/60"
              title="Refresh"
              onClick={() => qc.invalidateQueries({ queryKey: ["messages", chatId] })}
            >
              <Icon name="refresh" />
            </button>
          </div>
        </div>
        {showPersonaEditor ? (
          <div className="mt-3 grid gap-3 rounded-2xl border border-border/70 bg-card/60 p-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]">
            {hasManualSteering ? (
              <div className="md:col-span-3 rounded-2xl border border-amber-400/30 bg-amber-400/10 px-3 py-2 text-sm text-amber-100">
                This chat has manual steering overrides. Re-applying a persona can change the current tone and behavior.
              </div>
            ) : null}
            <div className="md:col-span-3 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setDraftApplyMode("permanent")}
                className={`rounded-xl border px-3 py-2 text-sm ${draftApplyMode === "permanent" ? "border-accent/50 bg-accent/10" : "border-border/70 bg-bg/40 hover:bg-card/60"}`}
              >
                Apply permanently
              </button>
              <button
                type="button"
                onClick={() => setDraftApplyMode("temporary")}
                className={`rounded-xl border px-3 py-2 text-sm ${draftApplyMode === "temporary" ? "border-accent/50 bg-accent/10" : "border-border/70 bg-bg/40 hover:bg-card/60"}`}
              >
                Apply for next N turns
              </button>
              {draftApplyMode === "temporary" ? (
                <label className="flex items-center gap-2 rounded-xl border border-border/70 bg-bg/40 px-3 py-2 text-sm">
                  <span className="text-muted">Turns</span>
                  <input
                    type="number"
                    min={1}
                    max={12}
                    value={draftTurnCount}
                    onChange={(event) => setDraftTurnCount(Math.max(1, Math.min(12, Number(event.target.value) || 1)))}
                    className="w-16 rounded-lg border border-border/70 bg-card/50 px-2 py-1 text-sm"
                  />
                </label>
              ) : null}
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted">Persona</label>
              <PersonaPicker
                personas={personas}
                fingerprintId={draftFingerprintId}
                skinId={draftSkinId}
                onFingerprintChange={setDraftFingerprintId}
                onSkinChange={setDraftSkinId}
                compact
                loading={personasLoading}
              />
            </div>
            <div className="flex items-end">
              <button
                type="button"
                onClick={() => void handlePersonaSave()}
                disabled={savingPersona}
                className="rounded-xl bg-accent/15 border border-accent/30 px-4 py-2 text-sm hover:bg-accent/20 disabled:opacity-50"
              >
                {savingPersona ? "Saving…" : "Apply"}
              </button>
            </div>
          </div>
        ) : null}
      </div>

      {exporting || exportFileName ? (
        <div className="px-4 py-2 text-xs text-muted border-b border-border/70 bg-card/40" aria-live="polite">
          {exporting ? "Preparing DOCX export…" : `Downloaded ${exportFileName}`}
        </div>
      ) : null}
      <div className="relative flex-1 min-h-0">
      <div ref={scrollRef} className="h-full overflow-y-auto px-3 py-4 space-y-3">
        {chatApproval ? (
          <ApprovalCard
            approval={chatApproval}
            busy={approvalBusy}
            error={approvalError}
            onApprove={(note) => resolveChatApproval("approve", note)}
            onDeny={(note) => resolveChatApproval("deny", note)}
          />
        ) : null}
        {selectedProvenance ? (
          <div className="rounded-[24px] border border-accent/30 bg-accent/5 p-3">
            <div className="mb-2 flex items-start justify-between gap-3">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">Why this reply</div>
                <div className="text-sm text-muted">
                  {selectedProvenance.why}
                </div>
                <div className="mt-1 text-[11px] uppercase tracking-[0.16em] text-muted">
                  {selectedProvenance.message_id} · {selectedProvenance.chat_id}
                </div>
              </div>
              <div className="flex items-center gap-2">
                {selectedProvenance.timeline_href ? (
                  <HardNavLink
                    href={selectedProvenance.timeline_href}
                    className="inline-flex rounded-full border border-border/70 px-3 py-1 text-xs text-muted hover:bg-card/60"
                  >
                    Open in chat
                  </HardNavLink>
                ) : null}
                <button
                  type="button"
                  className="inline-flex rounded-full border border-border/70 px-3 py-1 text-xs text-muted hover:bg-card/60"
                  onClick={() => setSelectedProvenance(null)}
                >
                  Dismiss
                </button>
              </div>
            </div>
            {selectedProvenanceLoading ? (
              <div className="text-sm text-muted">Loading provenance…</div>
            ) : null}
            {selectedProvenance.turn_provenance ? (
              <div className="grid gap-2 md:grid-cols-3">
                <div className="rounded-2xl border border-border/70 bg-bg/40 p-3 text-sm">
                  <div className="text-xs uppercase tracking-wide text-muted">Prompt</div>
                  <div>{selectedProvenance.turn_provenance.prompt_id || "—"}</div>
                </div>
                <div className="rounded-2xl border border-border/70 bg-bg/40 p-3 text-sm">
                  <div className="text-xs uppercase tracking-wide text-muted">Model config</div>
                  <div>{selectedProvenance.turn_provenance.model_config_id || "—"}</div>
                </div>
                <div className="rounded-2xl border border-border/70 bg-bg/40 p-3 text-sm">
                  <div className="text-xs uppercase tracking-wide text-muted">Sampling</div>
                  <div className="truncate">
                    {selectedProvenance.turn_provenance.sampling_params ? JSON.stringify(selectedProvenance.turn_provenance.sampling_params) : "—"}
                  </div>
                </div>
              </div>
            ) : null}
            {selectedProvenanceCounts ? (
              <div className="mt-3 rounded-2xl border border-border/70 bg-bg/40 p-3">
                <div className="text-xs uppercase tracking-wide text-muted">Source mix</div>
                <div className="mt-2 grid gap-2 md:grid-cols-3 xl:grid-cols-6">
                  <div className="rounded-xl border border-border/60 bg-card/40 px-3 py-2 text-sm">
                    <div className="text-xs uppercase tracking-wide text-muted">Retrieved</div>
                    <div>{selectedProvenanceCounts.retrieval}</div>
                  </div>
                  <div className="rounded-xl border border-border/60 bg-card/40 px-3 py-2 text-sm">
                    <div className="text-xs uppercase tracking-wide text-muted">Policy</div>
                    <div>{selectedProvenanceCounts.policy}</div>
                  </div>
                  <div className="rounded-xl border border-border/60 bg-card/40 px-3 py-2 text-sm">
                    <div className="text-xs uppercase tracking-wide text-muted">Evidence</div>
                    <div>{selectedProvenanceCounts.evidence}</div>
                  </div>
                  <div className="rounded-xl border border-border/60 bg-card/40 px-3 py-2 text-sm">
                    <div className="text-xs uppercase tracking-wide text-muted">Reflection</div>
                    <div>{selectedProvenanceCounts.reflection}</div>
                  </div>
                  <div className="rounded-xl border border-border/60 bg-card/40 px-3 py-2 text-sm">
                    <div className="text-xs uppercase tracking-wide text-muted">Mirroring</div>
                    <div>{selectedProvenanceCounts.mirroring}</div>
                  </div>
                  <div className="rounded-xl border border-border/60 bg-card/40 px-3 py-2 text-sm">
                    <div className="text-xs uppercase tracking-wide text-muted">Inference</div>
                    <div>{selectedProvenanceCounts.inference}</div>
                  </div>
                </div>
              </div>
            ) : null}
            {selectedProvenance.source_groups?.policy?.length ? (
              <div className="mt-3 rounded-2xl border border-border/70 bg-bg/40 p-3">
                <div className="text-xs uppercase tracking-wide text-muted">Policy bindings</div>
                <div className="mt-2 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
                  {selectedProvenance.source_groups.policy.map((item, index) => (
                    <div key={`${item.kind}-${index}`} className="rounded-xl border border-border/60 bg-card/40 px-3 py-2 text-sm">
                      <div className="text-xs uppercase tracking-wide text-muted">{item.label}</div>
                      <div className="truncate">{typeof item.value === "string" ? item.value : JSON.stringify(item.value)}</div>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
            {selectedProvenance.source_groups?.retrieval?.length ? (
              <div className="mt-3">
                <div className="text-xs uppercase tracking-wide text-muted">Retrieval sources</div>
                <div className="mt-2">
                  <SourceEvidenceCards sources={selectedProvenance.source_groups.retrieval} />
                </div>
              </div>
            ) : null}
            {selectedProvenance.source_groups?.evidence?.length ? (
              <div className="mt-3 rounded-2xl border border-border/70 bg-bg/40 p-3">
                <div className="text-xs uppercase tracking-wide text-muted">Evidence rows</div>
                <div className="mt-2 grid gap-2">
                  {selectedProvenance.source_groups.evidence.map((row, index) => (
                    <div key={`${row.ledger_id || "ledger"}-${index}`} className="rounded-xl border border-border/60 bg-card/40 px-3 py-2 text-sm">
                      <div className="font-medium">{row.evidence_type || "evidence"}</div>
                      <div className="text-xs text-muted">
                        {row.timestamp || "—"} {row.approval_id ? `· approval ${row.approval_id}` : ""}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        ) : provenanceMessageId && selectedProvenanceLoading ? (
          <div className="rounded-[24px] border border-border/70 bg-card/40 p-3 text-sm text-muted">
            Loading provenance…
          </div>
        ) : null}
        {liveActivity.length ? (
          <div className="rounded-[24px] border border-border/70 bg-card/40 p-3">
            <div className="mb-2 flex items-center justify-between">
              <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">Live activity</div>
              <Badge tone="neutral">{liveActivity.length}</Badge>
            </div>
            <div className="space-y-2">
              {[...liveActivity].reverse().map((item) => (
                <div key={item.id} className="flex items-start justify-between gap-3 rounded-2xl border border-border/60 bg-bg/40 px-3 py-2">
                  <div className="min-w-0">
                    <div className="text-sm font-medium">{item.label}</div>
                    {item.detail ? <div className="text-xs text-muted">{item.detail}</div> : null}
                  </div>
                  <Badge tone={item.status === "error" ? "danger" : item.status === "running" ? "warning" : "ok"}>
                    {item.kind}
                  </Badge>
                </div>
              ))}
            </div>
          </div>
        ) : null}
        {chat?.swarmRunId && chat?.swarmRole === "orchestrator" && swarmWorkspace ? (
          <div className="rounded-[24px] border border-border/70 bg-card/40 p-3">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">Swarm progress</div>
                <div className="text-sm text-muted">Master thread stays here. Jump directly into any member thread without losing the orchestration view.</div>
              </div>
              <HardNavLink
                href={`/swarm/${encodeURIComponent(chat.swarmRunId ?? "")}`}
                className="inline-flex rounded-full border border-border/70 px-3 py-1 text-xs text-muted hover:bg-card/60"
              >
                Open workspace
              </HardNavLink>
            </div>
            <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
              {[...(swarmWorkspace.orchestrator ? [swarmWorkspace.orchestrator] : []), ...(swarmWorkspace.members ?? [])].map((participant) => (
                <HardNavLink
                  key={participant.id}
                  href={`/chat/${encodeURIComponent(participant.id)}`}
                  className={`rounded-2xl border px-3 py-3 ${participant.id === chatId ? "border-accent/50 bg-accent/10" : "border-border/70 bg-bg/40 hover:bg-card/60"}`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="min-w-0">
                      <div className="truncate font-medium">{participant.title}</div>
                      <div className="text-[11px] uppercase tracking-wide text-muted">
                        {participant.swarmRole === "orchestrator" ? "Master" : "Member"} · {participant.status}
                      </div>
                    </div>
                    <Badge tone={participant.status === "error" ? "danger" : participant.status === "completed" ? "ok" : "warning"}>
                      {participant.status}
                    </Badge>
                  </div>
                  <div className="mt-2 text-xs text-muted">
                    {participant.latestText ? participant.latestText.slice(0, 140) : "No transcript yet."}
                  </div>
                </HardNavLink>
              ))}
            </div>
          </div>
        ) : null}
        {isLoading ? <PageSkeleton label="Loading messages" rows={5} /> : null}
        <ChatMessageList
          messages={messages}
          pendingUserMessages={pendingUserMessages}
          chatId={chatId}
          scrollRef={scrollRef}
          onRetry={onRetry}
          onWhyClick={(messageId) => void openProvenance(messageId)}
          onCitationClick={(c) => c.document_id && setViewCitation(c)}
        />
        {isStreamingActive ? (
          <div aria-live="polite" aria-atomic="false">
            <MessageBubble
              msg={{
                id: "streaming",
                chatId,
                role: "assistant",
                createdAt: new Date().toISOString(),
                content: "",
              }}
              isStreaming
              streamTextRef={streamingRef}
              streamTick={streamTick}
            />
          </div>
        ) : null}
      </div>
      </div>

      <div className="border-t border-border/70 bg-bg/40 backdrop-blur">
        <ChatComposer
          chatId={chatId}
          sendState={responsePhase}
          liveToolEvents={liveToolEvents}
          onSend={handleSend}
        />
      </div>

      <ConfirmDialog
        open={personaConfirmOpen}
        title="Override manual steering?"
        description="This chat already has manual steering adjustments. Applying a different persona can override the current steering feel."
        confirmLabel="Apply persona"
        onCancel={() => setPersonaConfirmOpen(false)}
        onConfirm={() => {
          setPersonaConfirmOpen(false);
          void applyPersonaSave();
        }}
      />
      <StepupApprovalModal
        request={stepupRequest}
        actionLabel={stepupRequest?.decision === "deny" ? "Deny with step-up" : "Approve with step-up"}
        onClose={() => setStepupRequest(null)}
        onCompleted={() => {
          setChatApproval(null);
          setStepupRequest(null);
          void qc.invalidateQueries({ queryKey: ["messages", chatId] });
        }}
      />
      {viewCitation?.document_id ? (
        <DocumentViewer
          documentId={viewCitation.document_id}
          filename={viewCitation.filename ?? viewCitation.document_id}
          mime={undefined}
          onClose={() => setViewCitation(null)}
          pageStart={viewCitation.page_start}
        />
      ) : null}
    </div>
  );
}
