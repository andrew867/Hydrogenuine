import { useCallback, useEffect, useRef, useState } from "react";
import type { NotificationItem } from "../components/NotificationBell";
import { parseSseChunk, type SseFrame } from "./sseParse";

export type StreamNotificationPayload = {
  id?: string;
  title?: string;
  href?: string;
  type?: string;
  created_at?: string;
  createdAt?: string;
};

export function parseNotificationPayload(raw: string): NotificationItem | null {
  try {
    const payload = JSON.parse(raw) as StreamNotificationPayload;
    const id = payload.id || `notification-${Date.now()}`;
    const title = payload.title || payload.type || "Notification";
    return {
      id,
      title,
      href: payload.href,
      createdAt: payload.created_at || payload.createdAt,
    };
  } catch {
    return null;
  }
}

function parseNotificationFrame(frame: SseFrame): NotificationItem | null {
  if (frame.event !== "notification") return null;
  return parseNotificationPayload(frame.data);
}

export function parseNotificationSseChunk(buffer: string): { remainder: string; notifications: NotificationItem[] } {
  const parsed = parseSseChunk(buffer, parseNotificationFrame);
  return { remainder: parsed.remainder, notifications: parsed.items };
}

export type UseNotificationStreamOptions = {
  streamUrl: string;
  headers?: Record<string, string> | (() => Record<string, string>);
  enabled?: boolean;
  replay?: boolean;
};

export function useNotificationStream({
  streamUrl,
  headers,
  enabled = true,
  replay = true,
}: UseNotificationStreamOptions) {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const seenRef = useRef<Set<string>>(new Set());

  const upsert = useCallback((incoming: NotificationItem[]) => {
    if (!incoming.length) return;
    setItems((prev) => {
      const next = [...prev];
      for (const item of incoming) {
        if (seenRef.current.has(item.id)) continue;
        seenRef.current.add(item.id);
        next.unshift(item);
      }
      return next.slice(0, 50);
    });
  }, []);

  useEffect(() => {
    if (!enabled || !streamUrl) return undefined;
    const abort = new AbortController();
    let reconnectDelay = 1000;

    const run = async () => {
      while (!abort.signal.aborted) {
        try {
          const url = new URL(streamUrl, typeof window !== "undefined" ? window.location.origin : "http://localhost");
          if (replay) url.searchParams.set("replay", "true");
          const resolvedHeaders = typeof headers === "function" ? headers() : (headers ?? {});
          const response = await fetch(url.toString(), {
            method: "GET",
            headers: resolvedHeaders,
            credentials: "include",
            cache: "no-store",
            signal: abort.signal,
          });
          if (!response.ok || !response.body) {
            throw new Error(`Notification stream HTTP ${response.status}`);
          }
          setConnected(true);
          setError(null);
          reconnectDelay = 1000;
          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = "";
          while (!abort.signal.aborted) {
            const { value, done } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const parsed = parseNotificationSseChunk(buffer);
            buffer = parsed.remainder;
            upsert(parsed.notifications);
          }
          buffer += decoder.decode();
          const tail = parseNotificationSseChunk(buffer);
          upsert(tail.notifications);
        } catch (err) {
          if (abort.signal.aborted) break;
          setConnected(false);
          setError(err instanceof Error ? err.message : "Notification stream error");
          await new Promise((resolve) => setTimeout(resolve, reconnectDelay));
          reconnectDelay = Math.min(reconnectDelay * 2, 30_000);
        }
      }
    };

    void run();
    return () => {
      abort.abort();
      setConnected(false);
    };
  }, [enabled, headers, replay, streamUrl, upsert]);

  const dismiss = useCallback((id: string) => {
    setItems((prev) => prev.filter((item) => item.id !== id));
  }, []);

  return { items, connected, error, dismiss };
}
