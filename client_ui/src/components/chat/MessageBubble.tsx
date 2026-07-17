"use client";

import React, { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { HgMessage } from "@/types/hg";
import { cn } from "@/lib/cn";
import { relTime } from "@/lib/time";
import { Badge } from "@/components/ui/Badge";
import { ToolCard } from "@/components/tools/ToolCard";
import { Icon } from "@/components/ui/Icon";
import { CitationChips } from "@/components/documents/CitationChips";
import { SourceEvidenceCards } from "@/components/chat/SourceEvidenceCards";
import type { Citation } from "@/types/hg";

export function MessageBubble({
  msg,
  isStreaming,
  streamTextRef,
  streamTick,
  onCopy,
  onRetry,
  onWhyClick,
  onCitationClick,
}: {
  msg: HgMessage;
  isStreaming?: boolean;
  /** Ref-based token stream (B12): avoids React re-render per token. */
  streamTextRef?: React.MutableRefObject<string>;
  streamTick?: number;
  onCopy?: (text: string) => void;
  onRetry?: () => void;
  onWhyClick?: () => void;
  onCitationClick?: (c: Citation) => void;
}) {
  const isUser = msg.role === "user";
  const isTool = msg.role === "tool";
  const [copied, setCopied] = useState(false);
  const streamBodyRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!isStreaming || !streamTextRef || !streamBodyRef.current) return;
    streamBodyRef.current.textContent = streamTextRef.current;
  }, [isStreaming, streamTextRef, streamTick]);

  const handleCopy = () => {
    if (msg.content && onCopy) {
      onCopy(msg.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } else if (msg.content && typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(msg.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (isTool && msg.tool) {
    return (
      <div className="flex justify-center">
        <ToolCard tool={msg.tool} when={msg.createdAt} />
      </div>
    );
  }

  const showActions = (msg.content || isStreaming) && (onCopy || onRetry || onWhyClick);
  const canRetry = !isUser && onRetry && !isStreaming;
  const canWhy = !isUser && !!onWhyClick && !isStreaming;

  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[92%] sm:max-w-[70%] rounded-3xl px-4 py-3 border shadow-soft",
          isUser ? "bg-accent/15 border-accent/25" : "bg-card/80 border-border/70"
        )}
      >
        <div className="flex items-center justify-between gap-2 mb-2">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge tone={isUser ? "accent" : "neutral"}>{isUser ? "You" : "HG"}</Badge>
            {msg.deliveryState === "pending" ? <Badge tone="warning">Pending</Badge> : null}
            {msg.deliveryState === "accepted" ? <Badge tone="neutral">Sent</Badge> : null}
            {msg.deliveryState === "responding" ? <Badge tone="neutral">Processing</Badge> : null}
            {msg.deliveryState === "error" ? <Badge tone="danger">Failed</Badge> : null}
            {msg.citations?.length ? <Badge tone="neutral">{msg.citations.length} cite</Badge> : null}
            {msg.approvalsRequired ? <Badge tone="warning">Approval required</Badge> : null}
            {!isUser && !msg.approvalsRequired && msg.content ? <Badge tone="neutral">Policy</Badge> : null}
          </div>
          <div className="flex items-center gap-1">
            {showActions ? (
              <div className="flex items-center gap-0.5">
                {msg.content || isStreaming ? (
                  <button
                    type="button"
                    onClick={handleCopy}
                    className="p-1.5 rounded-xl text-muted hover:text-text hover:bg-bg/50 transition"
                    title={copied ? "Copied" : "Copy"}
                    aria-label={copied ? "Copied" : "Copy"}
                  >
                    <Icon name="copy" className="h-4 w-4" />
                    {copied ? <span className="sr-only">Copied</span> : null}
                  </button>
                ) : null}
                {canRetry ? (
                  <button
                    type="button"
                    onClick={() => onRetry?.()}
                    className="p-1.5 rounded-xl text-muted hover:text-text hover:bg-bg/50 transition"
                    title="Retry"
                    aria-label="Retry"
                  >
                    <Icon name="refresh" className="h-4 w-4" />
                  </button>
                ) : null}
                {canWhy ? (
                  <button
                    type="button"
                    onClick={() => onWhyClick?.()}
                    className="p-1.5 rounded-xl text-muted hover:text-text hover:bg-bg/50 transition"
                    title="Why this reply"
                    aria-label="Why this reply"
                  >
                    <Icon name="star" className="h-4 w-4" />
                  </button>
                ) : null}
              </div>
            ) : null}
            <div className="text-[11px] text-muted">{relTime(msg.createdAt)}</div>
          </div>
        </div>

        <div className="prose prose-invert prose-p:my-2 prose-pre:bg-bg/60 prose-pre:border prose-pre:border-border/70 prose-pre:rounded-2xl max-w-none">
          {isStreaming && streamTextRef ? (
            <div ref={streamBodyRef} className="whitespace-pre-wrap break-words" />
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content || ""}</ReactMarkdown>
          )}
          {isStreaming ? (
            <span
              className="inline-block w-0.5 h-5 ml-0.5 bg-accent rounded-sm animate-pulse shadow-[0_0_8px_2px_rgba(120,235,255,0.5)]"
              aria-hidden
            />
          ) : null}
        </div>

        {msg.citations?.length ? (
          <CitationChips citations={msg.citations} onCitationClick={onCitationClick} />
        ) : null}
        {msg.sourceEvidence?.length ? <SourceEvidenceCards sources={msg.sourceEvidence} /> : null}
      </div>
    </div>
  );
}
