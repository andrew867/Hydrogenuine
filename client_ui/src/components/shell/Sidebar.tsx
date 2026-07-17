"use client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { hgApi } from "@/lib/hgApi";
import { useKeyRingStore } from "@/store/keyRingStore";
import { relTime } from "@/lib/time";
import { env } from "@/lib/env";
import { Icon } from "@/components/ui/Icon";
import { cn } from "@/lib/cn";
import { usePathname, useRouter } from "next/navigation";
import React from "react";
import { NewChatModal } from "@/components/chat/NewChatModal";
import { SwarmRunModal } from "@/components/swarm/SwarmRunModal";
import { HardNavLink } from "@/components/navigation/HardNavLink";
import type { ChatSummary } from "@/types/hg";
import { operatorHashUrl } from "@/lib/operatorLinks";
import { ConfirmDialog } from "hg_ui_kit";
import { useUiStore } from "@/store/uiStore";

type PendingConfirm =
  | { kind: "chat"; id: string }
  | { kind: "swarm"; id: string }
  | null;

function groupChatsBySwarm(chats: ChatSummary[]): { ungrouped: ChatSummary[]; swarms: Map<string, ChatSummary[]> } {
  const ungrouped: ChatSummary[] = [];
  const swarms = new Map<string, ChatSummary[]>();
  for (const c of chats) {
    const runId = c.swarmRunId != null && c.swarmRunId !== "" ? c.swarmRunId : null;
    if (!runId) {
      ungrouped.push(c);
    } else {
      const list = swarms.get(runId) ?? [];
      list.push(c);
      swarms.set(runId, list);
    }
  }
  return { ungrouped, swarms };
}

function byLatest(a: ChatSummary, b: ChatSummary) {
  return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime();
}

export function Sidebar() {
  const path = usePathname();
  const router = useRouter();
  const qc = useQueryClient();
  const [newChatOpen, setNewChatOpen] = React.useState(false);
  const swarmOpen = useUiStore((s) => s.swarmModalOpen);
  const swarmPreset = useUiStore((s) => s.swarmModalPreset);
  const openSwarmModal = useUiStore((s) => s.openSwarmModal);
  const closeSwarmModal = useUiStore((s) => s.closeSwarmModal);
  const [expandedSwarms, setExpandedSwarms] = React.useState<Set<string>>(new Set());
  const [deletingChatId, setDeletingChatId] = React.useState<string | null>(null);
  const [deletingSwarmId, setDeletingSwarmId] = React.useState<string | null>(null);
  const [archivingChatId, setArchivingChatId] = React.useState<string | null>(null);
  const [archivingSwarmId, setArchivingSwarmId] = React.useState<string | null>(null);
  const [pendingConfirm, setPendingConfirm] = React.useState<PendingConfirm>(null);
  const researchChatId =
    path?.startsWith("/chat/")
      ? decodeURIComponent(path.replace(/^\/chat\//, "").split("/")[0] || "")
      : path?.startsWith("/research/")
        ? decodeURIComponent(path.replace(/^\/research\//, "").split("/")[0] || "")
        : null;
  const swarmRunIdFromPath = path?.startsWith("/swarm/") ? decodeURIComponent(path.replace(/^\/swarm\//, "").split("/")[0] || "") : null;
  React.useEffect(() => {
    setNewChatOpen(false);
    closeSwarmModal();
  }, [path, closeSwarmModal]);
  React.useEffect(() => {
    if (swarmRunIdFromPath) setExpandedSwarms((prev) => new Set([...prev, swarmRunIdFromPath]));
  }, [swarmRunIdFromPath]);
  const isSwarmExpanded = (runId: string) => expandedSwarms.has(runId);
  const { adminKey, operatorKey, impersonationToken, browserSession, locked } = useKeyRingStore();
  const hasWorkspaceAuth = env.demoMode || ((!locked && !!operatorKey) || !!impersonationToken || !!browserSession);
  const { data: tenant } = useQuery({
    queryKey: ["tenant-me"],
    queryFn: () => hgApi.getTenantMe(),
    enabled: !env.demoMode && hasWorkspaceAuth,
    retry: false,
  });
  const isPrincipal = tenant?.role === "principal" && !!tenant?.principal_id;
  const canViewDiagnostics =
    env.demoMode ||
    (!!adminKey && !locked) ||
    (!!operatorKey && !locked) ||
    tenant?.role === "operator" ||
    tenant?.role === "admin";
  const { data } = useQuery({
    queryKey: ["chats"],
    queryFn: () => hgApi.listChats(),
    enabled: hasWorkspaceAuth,
    retry: false,
  });
  const [q, setQ] = React.useState("");
  const navigate = React.useCallback((href: string) => {
    if (typeof window !== "undefined") {
      window.location.assign(href);
      return;
    }
    router.push(href);
  }, [router]);

  const allChats = (data || []).filter(c =>
    (c.title + " " + (c.subtitle || "")).toLowerCase().includes(q.toLowerCase())
  ).sort(byLatest);
  const { ungrouped, swarms } = groupChatsBySwarm(allChats);
  const operatorStatusHref = operatorHashUrl("/status");
  const operatorProofsHref = operatorHashUrl("/proofs");
  const operatorSocialHref = operatorHashUrl("/social");

  const isInteractiveTarget = (target: EventTarget | null) =>
    target instanceof Element && !!target.closest("a,button,input,textarea,select,[role='button']");

  const activateRow =
    (href: string) =>
    (event: React.MouseEvent<HTMLDivElement> | React.KeyboardEvent<HTMLDivElement>) => {
      if ("key" in event) {
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
      } else if (isInteractiveTarget(event.target)) {
        return;
      }
      navigate(href);
    };

  const toggleSwarm = (runId: string) => {
    setExpandedSwarms((prev) => {
      const next = new Set(prev);
      if (next.has(runId)) next.delete(runId);
      else next.add(runId);
      return next;
    });
  };

  const handleDeleteChat = async (chatId: string) => {
    if (deletingChatId) return;
    setPendingConfirm({ kind: "chat", id: chatId });
  };

  const runDeleteChat = async (chatId: string) => {
    setDeletingChatId(chatId);
    try {
      await hgApi.trashChat(chatId);
      await qc.invalidateQueries({ queryKey: ["chats"] });
      await qc.invalidateQueries({ queryKey: ["deleted-chats"] });
      if (path === `/chat/${encodeURIComponent(chatId)}`) {
        router.replace("/");
        return;
      }
    } finally {
      setDeletingChatId(null);
    }
  };

  const handleArchiveChat = async (chatId: string) => {
    if (archivingChatId) return;
    setArchivingChatId(chatId);
    try {
      await hgApi.archiveChat(chatId);
      await qc.invalidateQueries({ queryKey: ["chats"] });
      await qc.invalidateQueries({ queryKey: ["archived-chats"] });
      if (path === `/chat/${encodeURIComponent(chatId)}`) {
        router.replace("/");
      }
    } finally {
      setArchivingChatId(null);
    }
  };

  const handleDeleteSwarm = async (swarmRunId: string) => {
    if (deletingSwarmId) return;
    setPendingConfirm({ kind: "swarm", id: swarmRunId });
  };

  const runDeleteSwarm = async (swarmRunId: string) => {
    setDeletingSwarmId(swarmRunId);
    try {
      const result = await hgApi.trashSwarm(swarmRunId);
      await qc.invalidateQueries({ queryKey: ["chats"] });
      await qc.invalidateQueries({ queryKey: ["deleted-chats"] });
      await qc.invalidateQueries({ queryKey: ["swarm", swarmRunId] });
      const deletedChatIds = new Set(result.updated_chat_ids || []);
      if (
        path === `/swarm/${encodeURIComponent(swarmRunId)}` ||
        (path?.startsWith("/chat/") && deletedChatIds.has(decodeURIComponent(path.replace(/^\/chat\//, "").split("/")[0] || "")))
      ) {
        router.replace("/");
        return;
      }
    } finally {
      setDeletingSwarmId(null);
    }
  };

  const handleArchiveSwarm = async (swarmRunId: string) => {
    if (archivingSwarmId) return;
    setArchivingSwarmId(swarmRunId);
    try {
      await hgApi.archiveSwarm(swarmRunId);
      await qc.invalidateQueries({ queryKey: ["chats"] });
      await qc.invalidateQueries({ queryKey: ["archived-chats"] });
      await qc.invalidateQueries({ queryKey: ["swarm", swarmRunId] });
      if (path === `/swarm/${encodeURIComponent(swarmRunId)}`) {
        router.replace("/");
      }
    } finally {
      setArchivingSwarmId(null);
    }
  };

  return (
    <aside className="w-[320px] max-w-[84vw] border-r border-border/80 bg-bg/60 backdrop-blur flex flex-col">
      <div className="p-3">
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Icon name="search" className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <input
              className="w-full rounded-2xl bg-card/80 border border-border/70 py-2 pl-10 pr-3 outline-none focus:border-accent/60"
              placeholder="Search chats"
              value={q}
              onChange={e => setQ(e.target.value)}
            />
          </div>
          <button
            className="p-2 rounded-2xl bg-card/80 border border-border/70 hover:border-accent/60"
            onClick={() => openSwarmModal(null)}
            title="Run swarm"
          >
            <Icon name="zap" />
          </button>
          <button
            type="button"
            className="p-2 rounded-2xl bg-card/80 border border-border/70 hover:border-accent/60"
            onClick={() => setNewChatOpen(true)}
            title="New chat"
            aria-label="New chat"
          >
            <Icon name="plus" />
          </button>
        </div>
        <SwarmRunModal open={swarmOpen} preset={swarmPreset} onClose={() => closeSwarmModal()} />
        <NewChatModal
          open={newChatOpen}
          onClose={() => setNewChatOpen(false)}
          onCreated={(chatId) => {
            setNewChatOpen(false);
            navigate(`/chat/${encodeURIComponent(chatId)}`);
          }}
        />
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-3">
        {ungrouped.map((c) => {
          const href = `/chat/${encodeURIComponent(c.id)}`;
          const isActive = path === href;
          return (
            <div
              key={c.id}
              className={cn(
                "rounded-2xl px-3 py-3 mb-2 border border-transparent hover:bg-card/60 transition",
                isActive ? "bg-card/80 border-border/70" : ""
              )}
              role="link"
              tabIndex={0}
              onClick={activateRow(href)}
              onKeyDown={activateRow(href)}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <div className="font-semibold truncate">{c.title}</div>
                  <div className="text-xs text-muted truncate">{c.subtitle || ""}</div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="text-[11px] text-muted whitespace-nowrap">{relTime(c.updatedAt)}</div>
                  <button
                    type="button"
                    className="rounded-lg p-1 text-muted hover:text-text hover:bg-card/70"
                    onClick={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      void handleArchiveChat(c.id);
                    }}
                    disabled={archivingChatId === c.id}
                    aria-label={`Archive ${c.title}`}
                    title="Archive"
                  >
                    <Icon name="archive" className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    className="rounded-lg p-1 text-muted hover:text-text hover:bg-card/70"
                    onClick={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      void handleDeleteChat(c.id);
                    }}
                    disabled={deletingChatId === c.id}
                    aria-label={`Delete ${c.title}`}
                    title="Delete"
                  >
                    <Icon name="trash" className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          );
        })}
        {Array.from(swarms.entries()).map(([runId, members]) => {
          const orderedMembers = [...members].sort((a, b) => {
            if ((a.swarmRole === "orchestrator") !== (b.swarmRole === "orchestrator")) {
              return a.swarmRole === "orchestrator" ? -1 : 1;
            }
            return byLatest(a, b);
          });
          const orchestrator = orderedMembers.find((c) => c.swarmRole === "orchestrator");
          const swarmHref = `/swarm/${encodeURIComponent(runId)}`;
          const isSwarmActive = path === swarmHref;
          const isExpanded = isSwarmExpanded(runId);
          const label = orchestrator?.title || `Swarm (${orderedMembers.length})`;
          return (
            <div key={runId} className="mb-2">
              <div
                className={cn(
                  "rounded-2xl px-3 py-2 border border-transparent hover:bg-card/60 transition",
                  isSwarmActive ? "bg-card/80 border-border/70" : ""
                )}
                role="link"
                tabIndex={0}
                onClick={activateRow(swarmHref)}
                onKeyDown={activateRow(swarmHref)}
              >
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    data-swarm-toggle
                    className="p-0.5 rounded hover:bg-card/80"
                    aria-expanded={isExpanded}
                    onClick={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      toggleSwarm(runId);
                    }}
                  >
                    <Icon name="chevronDown" className={cn("w-4 h-4 text-muted transition-transform", !isExpanded && "-rotate-90")} />
                  </button>
                  <span className="font-semibold truncate flex-1">{label}</span>
                  <span className="text-[11px] text-muted">{orderedMembers.length}</span>
                  <button
                    type="button"
                    className="rounded-lg p-1 text-muted hover:text-text hover:bg-card/70"
                    onClick={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      void handleArchiveSwarm(runId);
                    }}
                    disabled={archivingSwarmId === runId}
                    aria-label={`Archive swarm ${label}`}
                    title="Archive swarm"
                  >
                    <Icon name="archive" className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    className="rounded-lg p-1 text-muted hover:text-text hover:bg-card/70"
                    onClick={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      void handleDeleteSwarm(runId);
                    }}
                    disabled={deletingSwarmId === runId}
                    aria-label={`Delete swarm ${label}`}
                    title="Delete swarm"
                  >
                    <Icon name="trash" className="h-4 w-4" />
                  </button>
                </div>
              </div>
              {isExpanded && (
                <div className="pl-5 pr-2 py-1 space-y-1">
                  {orderedMembers.map((c) => {
                    const href = `/chat/${encodeURIComponent(c.id)}`;
                    const isActive = path === href;
                    return (
                      <div
                        key={c.id}
                        className={cn(
                          "rounded-xl px-3 py-2 text-sm border border-transparent hover:bg-card/60 transition",
                          isActive ? "bg-card/80 border-border/70" : ""
                        )}
                        role="link"
                        tabIndex={0}
                        onClick={activateRow(href)}
                        onKeyDown={activateRow(href)}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex min-w-0 flex-1 items-center gap-2">
                            <span className="font-medium truncate">{c.title}</span>
                            {c.swarmRole ? (
                              <span className="rounded-full border border-border/70 px-2 py-0.5 text-[10px] uppercase tracking-wide text-muted">
                                {c.swarmRole}
                              </span>
                            ) : null}
                          </div>
                          <span className="flex items-center gap-2">
                            <span className="text-[11px] text-muted whitespace-nowrap">{relTime(c.updatedAt)}</span>
                            <button
                              type="button"
                              className="rounded-lg p-1 text-muted hover:text-text hover:bg-card/70"
                              onClick={(event) => {
                                event.preventDefault();
                                event.stopPropagation();
                                void handleArchiveChat(c.id);
                              }}
                              disabled={archivingChatId === c.id}
                              aria-label={`Archive ${c.title}`}
                              title="Archive"
                            >
                              <Icon name="archive" className="h-4 w-4" />
                            </button>
                            <button
                              type="button"
                              className="rounded-lg p-1 text-muted hover:text-text hover:bg-card/70"
                              onClick={(event) => {
                                event.preventDefault();
                                event.stopPropagation();
                                void handleDeleteChat(c.id);
                              }}
                              disabled={deletingChatId === c.id}
                              aria-label={`Delete ${c.title}`}
                              title="Delete"
                            >
                              <Icon name="trash" className="h-4 w-4" />
                            </button>
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
        {!allChats.length ? <div className="text-sm text-muted px-3 py-2">No chats.</div> : null}
      </div>

      <div className="p-3 border-t border-border/70 space-y-2">
        <div className="px-2 pt-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">Workspace</div>
        <HardNavLink
          href="/"
          className={cn(
            "block w-full text-left rounded-2xl px-3 py-2 text-sm border border-transparent hover:bg-card/60 transition",
            path === "/" ? "bg-card/80 border-border/70" : ""
          )}
        >
          Home
        </HardNavLink>
        <HardNavLink
          href="/approvals"
          className={cn(
            "block w-full text-left rounded-2xl px-3 py-2 text-sm border border-transparent hover:bg-card/60 transition",
            path?.startsWith("/approvals") ? "bg-card/80 border-border/70" : ""
          )}
        >
          Approvals
        </HardNavLink>
        <HardNavLink
          href="/steering"
          className={cn(
            "block w-full text-left rounded-2xl px-3 py-2 text-sm border border-transparent hover:bg-card/60 transition",
            path === "/steering" ? "bg-card/80 border-border/70" : ""
          )}
        >
          Entity steering
        </HardNavLink>
        {researchChatId ? (
          <HardNavLink
            href={`/research/${encodeURIComponent(researchChatId)}`}
            className={cn(
              "block w-full text-left rounded-2xl px-3 py-2 text-sm border border-transparent hover:bg-card/60 transition",
              path?.startsWith("/research/") ? "bg-card/80 border-border/70" : ""
            )}
          >
            Research workspace
          </HardNavLink>
        ) : null}
        <div className="px-2 pt-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">People + roles</div>
        {isPrincipal && tenant?.principal_id ? (
          <HardNavLink
            href={`/principals/${encodeURIComponent(tenant.principal_id ?? "")}`}
            className={cn(
              "block w-full text-left rounded-2xl px-3 py-2 text-sm border border-transparent hover:bg-card/60 transition",
              path?.startsWith("/principals") ? "bg-card/80 border-border/70" : ""
            )}
          >
            My availability
          </HardNavLink>
        ) : (
          <HardNavLink
            href="/principals"
            className={cn(
              "block w-full text-left rounded-2xl px-3 py-2 text-sm border border-transparent hover:bg-card/60 transition",
              path?.startsWith("/principals") ? "bg-card/80 border-border/70" : ""
            )}
          >
            Principals
          </HardNavLink>
        )}
        {canViewDiagnostics ? (
          <>
            <div className="px-2 pt-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">Observe + operate</div>
            <a
              href={operatorStatusHref}
              className="block rounded-2xl px-3 py-2 text-sm border border-transparent hover:bg-card/60 transition"
              title="Open operator status console"
            >
              Status console
            </a>
            <a
              href={operatorProofsHref}
              className="block rounded-2xl px-3 py-2 text-sm border border-transparent hover:bg-card/60 transition"
              title="Open operator proof viewer"
            >
              Proof runs
            </a>
            <a
              href={operatorSocialHref}
              className="block rounded-2xl px-3 py-2 text-sm border border-transparent hover:bg-card/60 transition"
              title="Open operator social ops"
            >
              Social ops
            </a>
          </>
        ) : null}
        {!isPrincipal && adminKey && canViewDiagnostics ? (
          <>
            <div className="px-2 pt-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">Admin</div>
            <HardNavLink
              href="/admin"
              className={cn(
                "block w-full text-left rounded-2xl px-3 py-2 text-sm border border-transparent hover:bg-card/60 transition",
                path?.startsWith("/admin") ? "bg-card/80 border-border/70" : ""
              )}
            >
              Admin
            </HardNavLink>
          </>
        ) : null}
        <div className="flex items-center justify-between">
          <div className="text-xs text-muted">Mobile feel</div>
          <div className="text-xs text-muted">PWA ready</div>
        </div>
      </div>
      <ConfirmDialog
        open={pendingConfirm?.kind === "chat"}
        title="Move chat to deleted items?"
        description="You can restore this chat for 30 days from deleted items."
        confirmLabel="Move to deleted"
        destructive
        onCancel={() => setPendingConfirm(null)}
        onConfirm={() => {
          const chatId = pendingConfirm?.kind === "chat" ? pendingConfirm.id : "";
          setPendingConfirm(null);
          if (chatId) void runDeleteChat(chatId);
        }}
      />
      <ConfirmDialog
        open={pendingConfirm?.kind === "swarm"}
        title="Move swarm to deleted items?"
        description="This moves the swarm run and all member chats to deleted items. You can restore them for 30 days."
        confirmLabel="Move to deleted"
        destructive
        onCancel={() => setPendingConfirm(null)}
        onConfirm={() => {
          const swarmRunId = pendingConfirm?.kind === "swarm" ? pendingConfirm.id : "";
          setPendingConfirm(null);
          if (swarmRunId) void runDeleteSwarm(swarmRunId);
        }}
      />
    </aside>
  );
}
