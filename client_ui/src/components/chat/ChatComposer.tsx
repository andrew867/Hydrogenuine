"use client";

import React from "react";
import { Icon } from "@/components/ui/Icon";
import { InjectionBlockedBadge } from "@/components/chat/InjectionBlockedBadge";

type SendErrorDetail = {
  code?: string;
  message?: string;
  assessment?: { score: number; recommended_action: string; indicator_ids?: string[]; indicators?: string[] };
};

export function ChatComposer({
  chatId,
  sendState = "idle",
  liveToolEvents = [],
  onSend: onSubmitMessage,
}: {
  chatId: string;
  sendState?: "idle" | "sending" | "accepted" | "responding" | "error";
  liveToolEvents?: Array<{ id: string; name: string; status: "running" | "ok" | "error"; detail?: string }>;
  onSend?: (content: string) => Promise<void>;
}) {
  const [text, setText] = React.useState("");
  const [injectionBlocked, setInjectionBlocked] = React.useState<SendErrorDetail["assessment"] | null>(null);
  const awaitingResponse = sendState === "sending" || sendState === "accepted" || sendState === "responding";

  const onSend = async () => {
    const t = text.trim();
    if (!t || awaitingResponse) return;
    const previousText = text;
    setInjectionBlocked(null);
    setText("");
    try {
      if (onSubmitMessage) {
        await onSubmitMessage(t);
      }
    } catch (err) {
      setText(previousText);
      const typed = err as Error & { detail?: SendErrorDetail };
      if (typed.detail?.code === "prompt_injection_blocked" && typed.detail?.assessment) {
        setInjectionBlocked(typed.detail.assessment);
      } else {
        setInjectionBlocked(null);
      }
    }
  };

  const liveLabel =
    sendState === "sending"
      ? "Sending…"
      : sendState === "accepted"
        ? "Accepted. Waiting for agent…"
        : sendState === "responding"
          ? "Agent responding…"
          : sendState === "error"
            ? "Send failed"
            : "";
  const buttonLabel =
    sendState === "sending"
      ? "Sending…"
      : sendState === "accepted"
        ? "Waiting"
        : sendState === "responding"
          ? "Waiting"
          : "Send";
  const placeholder = awaitingResponse ? "Waiting for entity response…" : "Message HG…";
  const helperLabel = awaitingResponse
    ? "Waiting for the current reply before sending another turn"
    : "Enter to send, Shift+Enter for newline";
  const activeTool = [...liveToolEvents].reverse().find((item) => item.status === "running");

  return (
    <div className="p-3 flex flex-col gap-2">
      {injectionBlocked && (
        <InjectionBlockedBadge
          message="Message rejected due to prompt-injection policy."
          assessment={injectionBlocked}
          onDismiss={() => setInjectionBlocked(null)}
        />
      )}
      {activeTool ? (
        <div className="rounded-2xl border border-border/70 bg-card/40 px-3 py-2 text-xs text-muted">
          Working: <span className="text-text">{activeTool.name}</span>
        </div>
      ) : null}
      <div className="flex items-end gap-2">
      <div className="flex-1 rounded-2xl border border-border/70 bg-card/60 overflow-hidden">
        <textarea
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder={placeholder}
          rows={1}
          className="w-full resize-none bg-transparent outline-none px-3 py-3 text-sm leading-6 max-h-40"
          disabled={awaitingResponse}
          onKeyDown={e => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void onSend();
            }
          }}
        />
        <div className="px-3 pb-2 text-[11px] text-muted flex items-center justify-between">
          <span>{helperLabel}</span>
          {liveLabel ? <span className={sendState === "error" ? "text-red-500" : "text-accent"}>{liveLabel}</span> : <span />}
        </div>
      </div>
      <button
        onClick={() => void onSend()}
        className={`h-12 min-w-12 rounded-2xl border transition flex items-center justify-center shadow-soft px-3 ${
          awaitingResponse
            ? "bg-card/70 border-border/70 text-muted cursor-not-allowed"
            : "bg-accent/15 border-accent/30 hover:bg-accent/20 active:scale-[0.98]"
        }`}
        aria-label={awaitingResponse ? "Waiting for reply" : "Send"}
        title={awaitingResponse ? "Waiting for entity response" : "Send message"}
        disabled={awaitingResponse || !text.trim()}
      >
        <span className={`flex items-center gap-2 ${awaitingResponse ? "text-muted" : "text-accent"}`}>
          <Icon name={awaitingResponse ? "close" : "send"} className={sendState === "responding" ? "animate-pulse" : ""} />
          <span className="text-xs font-medium">{buttonLabel}</span>
        </span>
      </button>
      </div>
    </div>
  );
}
