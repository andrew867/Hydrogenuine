import { useCallback, useEffect, useRef, useState } from "react";
import { parseSseChunk, type SseFrame } from "./sseParse";

export type ChannelEvent = {
  id?: string;
  type: string;
  data: unknown;
  raw: string;
};

export type UseEventChannelOptions = {
  streamUrl: string;
  headers?: Record<string, string> | (() => Record<string, string>);
  enabled?: boolean;
  replay?: boolean;
  onEvent?: (event: ChannelEvent) => void;
};

function parseChannelEvent(frame: SseFrame): ChannelEvent | null {
  let data: unknown = frame.data;
  try {
    data = JSON.parse(frame.data);
  } catch {
    // keep raw string
  }
  return {
    id: frame.id,
    type: frame.event,
    data,
    raw: frame.data,
  };
}

export function useEventChannel({
  streamUrl,
  headers,
  enabled = true,
  replay = true,
  onEvent,
}: UseEventChannelOptions) {
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastEventId, setLastEventId] = useState<string | null>(null);
  const lastEventIdRef = useRef<string | null>(null);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const handleFrame = useCallback((frame: SseFrame) => {
    if (frame.id) {
      lastEventIdRef.current = frame.id;
      setLastEventId(frame.id);
    }
    const event = parseChannelEvent(frame);
    if (event) onEventRef.current?.(event);
    return event;
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
          const requestHeaders: Record<string, string> = { ...resolvedHeaders };
          if (lastEventIdRef.current) {
            requestHeaders["Last-Event-ID"] = lastEventIdRef.current;
          }
          const response = await fetch(url.toString(), {
            method: "GET",
            headers: requestHeaders,
            credentials: "include",
            cache: "no-store",
            signal: abort.signal,
          });
          if (!response.ok || !response.body) {
            throw new Error(`Event channel HTTP ${response.status}`);
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
            const parsed = parseSseChunk(buffer, handleFrame);
            buffer = parsed.remainder;
          }
          buffer += decoder.decode();
          parseSseChunk(buffer, handleFrame);
        } catch (err) {
          if (abort.signal.aborted) break;
          setConnected(false);
          setError(err instanceof Error ? err.message : "Event channel error");
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
  }, [enabled, handleFrame, headers, replay, streamUrl]);

  return { connected, error, lastEventId };
}
