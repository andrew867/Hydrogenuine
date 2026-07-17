// Agent Zero Workbench API client for the browser panel.
//
// Uses the gateway cookie session (credentials:"include") — the panel never holds
// or logs a raw token; the gateway derives the operator identity from the verified
// session. All calls are governed /v1/workbench/* endpoints; none performs an
// external effect.

import { parseSseChunk, type SseFrame } from "./sseParse";

export type WorkbenchRunPayload = {
  run_id: string;
  operator_subject: string;
  status: string;
  risk_level: string;
  request_text: string;
  external_effects_enabled: boolean;
  artifact_ids: string[];
  progress_event_ids: string[];
  subagent_lane_ids: string[];
};

export type TimelinePayload = {
  run_id: string;
  receipts: Array<Record<string, unknown>>;
  chain: { ok: boolean; count: number; run_id: string | null; failures: string[] };
};

export type SettingChangePayload = {
  change_id: string;
  applied: boolean;
  hold_reason: string;
  setting: string;
};

// Thrown when a governed setting change is HELD (403) pending step-up.
export class SettingHeldError extends Error {
  reason: string;
  setting: string;
  change_id: string;
  constructor(detail: { reason?: string; setting?: string; change_id?: string }) {
    super(`setting_change_held: ${detail.reason ?? ""}`);
    this.name = "SettingHeldError";
    this.reason = detail.reason ?? "";
    this.setting = detail.setting ?? "";
    this.change_id = detail.change_id ?? "";
  }
}

export class WorkbenchApiError extends Error {
  status: number;
  code: string;
  constructor(status: number, code: string) {
    super(`workbench_api_error ${status}: ${code}`);
    this.name = "WorkbenchApiError";
    this.status = status;
    this.code = code;
  }
}

export type WorkbenchApiOptions = {
  baseUrl?: string; // default "" (same origin)
  fetchImpl?: typeof fetch;
};

async function req(
  fetchImpl: typeof fetch,
  method: string,
  url: string,
  body?: unknown,
): Promise<unknown> {
  const res = await fetchImpl(url, {
    method,
    credentials: "include",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 403) {
    const detail = await res.json().catch(() => ({}));
    const d = (detail as { detail?: Record<string, string> }).detail ?? {};
    if (d.code === "setting_change_held") throw new SettingHeldError(d);
    throw new WorkbenchApiError(403, d.code ?? "forbidden");
  }
  if (res.status === 401) throw new WorkbenchApiError(401, "unauthenticated");
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new WorkbenchApiError(res.status, JSON.stringify(detail));
  }
  return res.json();
}

// Compute the sha256 content_hash of a file in the browser — the raw bytes never
// leave the client; only {filename,size,content_hash} is sent.
export async function hashFile(file: Blob): Promise<string> {
  const buf = await file.arrayBuffer();
  const digest = await crypto.subtle.digest("SHA-256", buf);
  const hex = Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
  return `sha256:${hex}`;
}

export type UploadedArtifactPayload = {
  artifact_id: string;
  run_id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  content_hash: string;
  source: string;
  stored_path_ref: string | null;
  label: string;
  receipt_hash: string;
  stored: boolean;
  external_storage: boolean;
};

// Upload the real file BYTES via multipart/form-data. The browser sends the raw
// file (the server computes the authoritative sha256 and stores it in a bounded
// local artifact store); the optional expectedHash — computed via hashFile — is
// sent as an expectation the server verifies, never as authority. We deliberately
// do NOT set Content-Type so the browser adds the multipart boundary itself.
export async function uploadArtifactBytes(
  fetchImpl: typeof fetch,
  base: string,
  runId: string,
  file: Blob,
  opts: { filename?: string; expectedHash?: string; sensitivity?: string; label?: string } = {},
): Promise<UploadedArtifactPayload> {
  const form = new FormData();
  const name = opts.filename ?? (file as File).name ?? "upload.bin";
  form.append("file", file, name);
  if (opts.expectedHash) form.append("expected_sha256", opts.expectedHash);
  if (opts.sensitivity) form.append("sensitivity", opts.sensitivity);
  if (opts.label) form.append("label", opts.label);
  const res = await fetchImpl(`${base}/v1/workbench/runs/${runId}/artifacts/upload`, {
    method: "POST",
    credentials: "include",
    body: form,
  });
  if (res.status === 401) throw new WorkbenchApiError(401, "unauthenticated");
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    const code = (detail as { detail?: string }).detail ?? String(res.status);
    throw new WorkbenchApiError(res.status, typeof code === "string" ? code : JSON.stringify(code));
  }
  return (await res.json()) as UploadedArtifactPayload;
}

export type WorkbenchStreamOptions = {
  baseUrl?: string;
  fetchImpl?: typeof fetch;
  sinceSeq?: number;
  signal?: AbortSignal;
  onEvent: (frame: SseFrame) => void;
};

// Open a FINITE SSE catch-up stream over fetch + ReadableStream (not EventSource,
// which cannot send the cookie header in jsdom and carries no Last-Event-ID
// control here). Reuses the tested parseSseChunk. The stream is observation only:
// callers refresh the authoritative timeline on each frame — a frame never
// authorizes anything. Resolves when the server closes (after its `end` frame);
// throws WorkbenchApiError on a non-OK response so callers can fall back to poll.
export async function openWorkbenchStream(
  runId: string,
  opts: WorkbenchStreamOptions,
): Promise<void> {
  const base = opts.baseUrl ?? "";
  const f = opts.fetchImpl ?? fetch;
  const q = opts.sinceSeq != null ? `?since_seq=${opts.sinceSeq}` : "";
  const res = await f(`${base}/v1/workbench/runs/${runId}/events/stream${q}`, {
    credentials: "include",
    headers: { Accept: "text/event-stream" },
    signal: opts.signal,
  });
  if (res.status === 401) throw new WorkbenchApiError(401, "unauthenticated");
  if (res.status === 403) throw new WorkbenchApiError(403, "forbidden");
  if (!res.ok || !res.body) throw new WorkbenchApiError(res.status, "stream_unavailable");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  const drain = (chunk: string) => {
    const { remainder } = parseSseChunk<null>(chunk, (frame) => {
      opts.onEvent(frame);
      return null;
    });
    buffer = remainder;
  };
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    drain(buffer);
  }
  buffer += decoder.decode();
  if (buffer.trim()) drain(buffer.endsWith("\n\n") ? buffer : buffer + "\n\n");
}

export function createWorkbenchApi(opts: WorkbenchApiOptions = {}) {
  const base = opts.baseUrl ?? "";
  const f = opts.fetchImpl ?? fetch;
  const runs = `${base}/v1/workbench/runs`;
  return {
    createRun: (request_text: string, extra: Record<string, unknown> = {}) =>
      req(f, "POST", runs, { request_text, ...extra }) as Promise<WorkbenchRunPayload>,
    listRuns: () => req(f, "GET", runs) as Promise<{ runs: WorkbenchRunPayload[] }>,
    getRun: (id: string) =>
      req(f, "GET", `${runs}/${id}`) as Promise<WorkbenchRunPayload>,
    getTimeline: (id: string) =>
      req(f, "GET", `${runs}/${id}/timeline`) as Promise<TimelinePayload>,
    addArtifact: (id: string, meta: { filename: string; size_bytes: number; content_hash: string; mime_type?: string }) =>
      req(f, "POST", `${runs}/${id}/artifacts`, meta) as Promise<Record<string, unknown>>,
    uploadArtifact: (id: string, file: Blob, up: { filename?: string; expectedHash?: string; sensitivity?: string; label?: string } = {}) =>
      uploadArtifactBytes(f, base, id, file, up),
    openStream: (id: string, so: Omit<WorkbenchStreamOptions, "baseUrl" | "fetchImpl">) =>
      openWorkbenchStream(id, { ...so, baseUrl: base, fetchImpl: f }),
    addProgress: (id: string, ev: { event_type: string; subagent_lane_id?: string; persona?: string; detail?: string }) =>
      req(f, "POST", `${runs}/${id}/progress`, ev) as Promise<Record<string, unknown>>,
    addSteering: (id: string, text: string) =>
      req(f, "POST", `${runs}/${id}/steering`, { text }) as Promise<Record<string, unknown>>,
    changeSetting: (id: string, change: { setting: string; action_class: string; old_value: string; new_value: string }) =>
      req(f, "POST", `${runs}/${id}/settings`, change) as Promise<SettingChangePayload>,
  };
}

export type WorkbenchApi = ReturnType<typeof createWorkbenchApi>;
