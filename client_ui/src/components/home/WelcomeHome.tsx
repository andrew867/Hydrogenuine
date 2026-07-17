"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { hgApi } from "@/lib/hgApi";
import { NewChatModal } from "@/components/chat/NewChatModal";
import { useKeyRingStore } from "@/store/keyRingStore";
import { useUiStore } from "@/store/uiStore";
import { env } from "@/lib/env";
import { operatorHashUrl } from "@/lib/operatorLinks";
import { visibilityAwareRefetchInterval } from "hg_ui_kit";
import { GuidedTour } from "@/components/onboarding/GuidedTour";

const SAMPLE_PROMPTS = [
  "Check the weather around town and summarize the outlook.",
  "Read my attached file, split it into sections, and summarize each one before giving me the big picture.",
  "Search for the latest local headlines and give me the important ones in plain English.",
];

const WORKSPACE_LANES = [
  {
    title: "Talk",
    detail: "Start a clean conversation, pick a persona, and keep work moving inside one live thread.",
    cta: "Start a new chat",
    kind: "internal",
    action: "new-chat",
  },
  {
    title: "Swarm",
    detail: "Fan work out across multiple entities when you want parallel perspectives or faster decomposition.",
    cta: "Show swarm controls",
    kind: "internal",
    action: "swarm",
  },
  {
    title: "Current events",
    detail: "One-click preset swarm: three agents research today's headlines from distinct angles.",
    cta: "Start current events swarm",
    kind: "internal",
    action: "current-events-swarm",
  },
  {
    title: "Research",
    detail: "Upload documents, run retrieval-backed work, and turn messy material into structured outputs.",
    cta: "Open document workflow",
    kind: "internal",
    action: "document-start",
  },
  {
    title: "Approvals",
    detail: "Review blocked actions and see what needs a human decision before the system continues.",
    cta: "Go to approvals",
    kind: "internal",
    href: "/approvals",
  },
  {
    title: "Proofs + Status",
    detail: "Jump to the operator surfaces for proofs, status, timeline, and system-level investigation.",
    cta: "Open status console",
    kind: "external",
    href: operatorHashUrl("/status"),
  },
  {
    title: "Social Ops",
    detail: "Supervise browser-backed social accounts, approvals, session state, and notification checks.",
    cta: "Open social ops",
    kind: "external",
    href: operatorHashUrl("/social"),
  },
];

export function WelcomeHome() {
  const router = useRouter();
  const [newChatOpen, setNewChatOpen] = React.useState(false);
  const [startingPrompt, setStartingPrompt] = React.useState<string | null>(null);
  const { restored, operatorKey, impersonationToken, browserSession, locked } = useKeyRingStore();
  const setSidebarOpen = useUiStore((s) => s.setSidebarOpen);
  const openSwarmModal = useUiStore((s) => s.openSwarmModal);
  const ready = env.demoMode || (restored && !locked && (!!operatorKey || !!impersonationToken || !!browserSession));
  const { data: chats = [] } = useQuery({
    queryKey: ["chats"],
    queryFn: () => hgApi.listChats(),
    enabled: ready,
    refetchInterval: visibilityAwareRefetchInterval(30_000),
  });

  const handleQuickPrompt = async (prompt: string) => {
    setStartingPrompt(prompt);
    try {
      const created = await hgApi.createChat("New chat");
      await hgApi.sendMessage(created.chat_id, prompt);
      router.push(`/chat/${encodeURIComponent(created.chat_id)}`);
    } finally {
      setStartingPrompt(null);
    }
  };

  const handleDocumentStart = async () => {
    const created = await hgApi.createChat("Document review");
    router.push(`/research/${encodeURIComponent(created.chat_id)}`);
  };

  const handleLane = async (lane: (typeof WORKSPACE_LANES)[number]) => {
    if (lane.action === "new-chat") {
      setNewChatOpen(true);
      return;
    }
    if (lane.action === "document-start") {
      await handleDocumentStart();
      return;
    }
    if (lane.action === "swarm") {
      openSwarmModal(null);
      setSidebarOpen(true);
      return;
    }
    if (lane.action === "current-events-swarm") {
      openSwarmModal("current-events");
      return;
    }
    if (lane.kind === "internal" && lane.href) {
      router.push(lane.href);
      return;
    }
    if (lane.kind === "external" && lane.href && typeof window !== "undefined") {
      window.open(lane.href, "_blank", "noopener,noreferrer");
    }
  };

  return (
    <div className="min-h-full bg-[radial-gradient(circle_at_top,#19313d,transparent_50%),linear-gradient(180deg,rgba(9,18,24,0.96),rgba(8,12,16,1))]">
      <div className="mx-auto flex min-h-full max-w-6xl flex-col gap-8 px-6 py-10">
        <section className="rounded-[32px] border border-border/70 bg-card/40 p-8 shadow-soft backdrop-blur">
          <div className="flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <div className="mb-4 inline-flex items-center gap-3 rounded-full border border-accent/30 bg-accent/10 px-4 py-2 text-sm text-accent">
                <span className="inline-flex h-9 w-9 items-center justify-center rounded-2xl border border-accent/30 bg-bg/60 font-semibold">hg</span>
                Hydrogenuine workspace
              </div>
              <h1 className="text-4xl font-semibold tracking-tight text-text sm:text-5xl">One place to chat, fan out work, review proofs, and steer the run.</h1>
              <p className="mt-4 max-w-2xl text-base text-muted">
                Start a clean chat, hand the system a document, or launch a multi-agent job. This home screen replaces the old blind redirect and gives you a real starting point.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <button
                type="button"
                className="rounded-2xl border border-accent/40 bg-accent/15 px-5 py-4 text-left hover:bg-accent/20"
                onClick={() => setNewChatOpen(true)}
              >
                <div className="text-sm font-semibold">New chat</div>
                <div className="mt-1 text-sm text-muted">Pick a persona, skin, and start from scratch.</div>
              </button>
              <button
                type="button"
                className="rounded-2xl border border-border/70 bg-bg/40 px-5 py-4 text-left hover:bg-card/70"
                onClick={() => void handleDocumentStart()}
              >
                <div className="text-sm font-semibold">Add files</div>
                <div className="mt-1 text-sm text-muted">Open a fresh document chat and upload attachments.</div>
              </button>
            </div>
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-[28px] border border-border/70 bg-card/40 p-6">
            <div className="mb-3 text-sm font-semibold uppercase tracking-[0.16em] text-muted">Try these</div>
            <div className="grid gap-3">
              {SAMPLE_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => void handleQuickPrompt(prompt)}
                  disabled={startingPrompt === prompt}
                  className="rounded-2xl border border-border/70 bg-bg/40 px-4 py-4 text-left hover:bg-card/70 disabled:opacity-60"
                >
                  <div className="text-sm text-text">{prompt}</div>
                  <div className="mt-2 text-xs text-muted">
                    {startingPrompt === prompt ? "Starting…" : "Creates a chat, sends the first turn, then opens the live conversation."}
                  </div>
                </button>
              ))}
            </div>
          </div>
          <div className="rounded-[28px] border border-border/70 bg-card/40 p-6">
            <div className="mb-3 text-sm font-semibold uppercase tracking-[0.16em] text-muted">Recent work</div>
            <div className="space-y-3">
              {chats.slice(0, 6).map((chat) => (
                <button
                  key={chat.id}
                  type="button"
                  onClick={() => router.push(`/chat/${encodeURIComponent(chat.id)}`)}
                  className="w-full rounded-2xl border border-border/70 bg-bg/40 px-4 py-3 text-left hover:bg-card/70"
                >
                  <div className="truncate font-medium">{chat.title}</div>
                  <div className="mt-1 text-xs text-muted">{new Date(chat.updatedAt).toLocaleString()}</div>
                </button>
              ))}
              {!chats.length ? <div className="rounded-2xl border border-dashed border-border/70 px-4 py-6 text-sm text-muted">No active chats yet. Start with a sample prompt or open a fresh chat.</div> : null}
            </div>
          </div>
        </section>

        <section className="rounded-[28px] border border-border/70 bg-card/40 p-6">
          <div className="mb-3 text-sm font-semibold uppercase tracking-[0.16em] text-muted">Workspace map</div>
          <div className="grid gap-3 lg:grid-cols-3">
            {WORKSPACE_LANES.map((lane) => (
              <button
                key={lane.title}
                type="button"
                onClick={() => void handleLane(lane)}
                className="rounded-2xl border border-border/70 bg-bg/40 px-4 py-4 text-left hover:bg-card/70"
              >
                <div className="text-xs font-semibold uppercase tracking-[0.14em] text-accent">{lane.title}</div>
                <div className="mt-2 text-sm text-muted">{lane.detail}</div>
                <div className="mt-4 text-sm font-medium text-text">{lane.cta}</div>
              </button>
            ))}
          </div>
        </section>

        <NewChatModal
          open={newChatOpen}
          onClose={() => setNewChatOpen(false)}
          onCreated={(chatId) => {
            setNewChatOpen(false);
            router.push(`/chat/${encodeURIComponent(chatId)}`);
          }}
        />
        {ready ? (
          <GuidedTour
            userId={browserSession?.principal_id || operatorKey?.value?.slice(0, 12) || "demo"}
          />
        ) : null}
      </div>
    </div>
  );
}
