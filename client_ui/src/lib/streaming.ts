/**
 * Authenticated chat stream client.
 * Uses fetch + SSE parsing so operator auth headers work across origins.
 */

import { env } from "@/lib/env";
import { getHeaders } from "@/lib/keyRing";
import type { Citation, SourceEvidence } from "@/types/hg";

export type StreamEvent =
  | { type: "message.delta"; delta: string; agentId?: string }
  | { type: "message.final"; messageId: string; chatId: string; content: string; citations?: Citation[]; sourceEvidence?: SourceEvidence[] }
  | { type: "agent.status"; agentId: string; label: string; status: string; thought?: string }
  | { type: "agent.thinking"; agentId: string; thought: string }
  | { type: "steering_applied"; profileIds: string[]; strength?: number }
  | { type: "tool.start"; name: string }
  | { type: "tool.result"; name: string; result: unknown }
  | { type: "approval.created"; approval: unknown }
  | { type: "ping" | "pong" };

export type StreamEventHandler = (event: StreamEvent) => void;

/**
 * Build SSE URL for a chat: env.apiBase + /v1/chats/:id/stream (or env.sseUrl if it points at stream root)
 */
function streamUrl(chatId: string): string {
  const base = (env.apiBase || "").replace(/\/$/, "");
  return `${base}/v1/chats/${encodeURIComponent(chatId)}/stream`;
}

/**
 * Open EventSource for the chat stream and forward parsed events to the handler.
 * Returns a close function.
 */
function emitParsedEvent(eventType: string, rawData: string, onEvent: StreamEventHandler): void {
  try {
    const data = JSON.parse(rawData || "{}");
    if (eventType === "message.delta") {
      onEvent({ type: "message.delta", delta: data.delta ?? "", agentId: data.agent_id });
    } else if (eventType === "message.final") {
      onEvent({
        type: "message.final",
        messageId: data.message_id,
        chatId: data.chat_id,
        content: data.content ?? "",
        citations: Array.isArray(data.citations) ? data.citations : undefined,
        sourceEvidence: Array.isArray(data.sources) ? data.sources : Array.isArray(data.sourceEvidence) ? data.sourceEvidence : undefined,
      });
    } else if (eventType === "agent.status") {
      onEvent({
        type: "agent.status",
        agentId: data.agent_id ?? data.agentId,
        label: data.label ?? "",
        status: data.status ?? "idle",
        thought: data.thought,
      });
    } else if (eventType === "agent.thinking") {
      onEvent({ type: "agent.thinking", agentId: data.agent_id ?? data.agentId, thought: data.thought ?? "" });
    } else if (eventType === "steering_applied") {
      onEvent({ type: "steering_applied", profileIds: data.profile_ids ?? [], strength: data.strength });
    } else if (eventType === "tool.start") {
      onEvent({ type: "tool.start", name: data.name ?? data.tool_name ?? "tool" });
    } else if (eventType === "tool.result") {
      onEvent({ type: "tool.result", name: data.name ?? data.tool_name ?? "tool", result: data.result ?? data });
    } else if (eventType === "approval.created") {
      onEvent({ type: "approval.created", approval: data.approval ?? data });
    } else if (eventType === "ping") {
      onEvent({ type: "ping" });
    } else if (data.delta !== undefined) {
      onEvent({ type: "message.delta", delta: data.delta, agentId: data.agent_id });
    } else if (data.message_id) {
      onEvent({
        type: "message.final",
        messageId: data.message_id,
        chatId: data.chat_id,
        content: data.content ?? "",
        citations: Array.isArray(data.citations) ? data.citations : undefined,
        sourceEvidence: Array.isArray(data.sources) ? data.sources : Array.isArray(data.sourceEvidence) ? data.sourceEvidence : undefined,
      });
    } else if (data.agent_id !== undefined || data.agentId !== undefined) {
      onEvent({
        type: "agent.status",
        agentId: data.agent_id ?? data.agentId,
        label: data.label ?? "",
        status: data.status ?? "idle",
        thought: data.thought,
      });
    } else if (data.tool_name || data.name) {
      onEvent({ type: "tool.result", name: data.name ?? data.tool_name, result: data.result ?? data });
    }
  } catch {
    // ignore parse errors
  }
}

function parseSSEChunk(buffer: string, onEvent: StreamEventHandler): string {
  let remainder = buffer.replace(/\r\n/g, "\n");
  while (true) {
    const boundary = remainder.indexOf("\n\n");
    if (boundary < 0) break;
    const frame = remainder.slice(0, boundary);
    remainder = remainder.slice(boundary + 2);
    const lines = frame.split(/\r?\n/);
    let eventType = "message";
    const dataLines: string[] = [];
    for (const line of lines) {
      if (!line || line.startsWith(":")) continue;
      if (line.startsWith("event:")) {
        eventType = line.slice(6).trim() || "message";
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trimStart());
      }
    }
    if (dataLines.length > 0) emitParsedEvent(eventType, dataLines.join("\n"), onEvent);
  }
  return remainder;
}

export function openSSE(chatId: string, onEvent: StreamEventHandler): () => void {
  const url = streamUrl(chatId);
  const abort = new AbortController();
  const auth = getHeaders("operator", { baseUrl: env.apiBase || undefined, skipEnvCheck: false });
  const headers: Record<string, string> = {};
  if (auth.ok) Object.assign(headers, auth.headers);
  try {
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (timezone) headers["X-HG-Timezone"] = timezone;
  } catch {}

  void (async () => {
    try {
      const response = await fetch(url, {
        method: "GET",
        headers,
        cache: "no-store",
        signal: abort.signal,
      });
      if (!response.ok || !response.body) return;
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        buffer = parseSSEChunk(buffer, onEvent);
      }
      buffer += decoder.decode();
      parseSSEChunk(buffer, onEvent);
    } catch {
      // ignore aborted/disconnected streams; polling remains as fallback
    }
  })();

  return () => {
    abort.abort();
  };
}
