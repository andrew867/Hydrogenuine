/**
 * HG API HTTP client. Uses KeyRing for auth headers by key class.
 * Generates X-Request-ID per request; stores last request id for error display.
 */

import { env } from "@/lib/env";
import type { KeyClass } from "@/lib/keyTypes";
import { getHeaders, recordKeyUse } from "@/lib/keyRing";
import { useKeyRingStore } from "@/store/keyRingStore";

export type HgFetchOptions = RequestInit & {
  /** Key class for this request (default: operator). */
  keyClass?: KeyClass;
};

export async function hgFetch<T>(path: string, init?: HgFetchOptions): Promise<T> {
  const keyClass: KeyClass = init?.keyClass ?? "operator";
  const { method, body, headers: initHeaders, ...rest } = init ?? {};

  const base = env.demoMode ? "" : env.apiBase;
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;

  const isFormData = typeof body === "object" && body !== null && (body as FormData).constructor?.name === "FormData";
  let headers: Record<string, string> = {};
  if (!isFormData && body !== undefined && body !== null) headers["Content-Type"] = "application/json";

  if (!env.demoMode) {
    const result = getHeaders(keyClass, {
      baseUrl: base || undefined,
      skipEnvCheck: false,
    });
    if (!result.ok) {
      if (result.reason === "locked") throw new Error("Session locked. Unlock in Settings to continue.");
      if (result.reason === "no_key")
        throw new Error(keyClass === "operator" ? "Operator key required. Add key in Settings." : `This action requires a ${keyClass} key. Add it in Settings.`);
      if (result.reason === "cross_env_blocked")
        throw new Error("Request blocked: key is bound to a different environment. Confirm in Settings to proceed.");
      throw new Error("Unable to build request headers.");
    }
    headers = { ...headers, ...result.headers };
    recordKeyUse(keyClass);
  }
  try {
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (timezone) headers["X-HG-Timezone"] = timezone;
  } catch {}

  const res = await fetch(url, {
    ...rest,
    method: method ?? "GET",
    body,
    headers: { ...headers, ...(initHeaders as Record<string, string>) },
    cache: "no-store",
    credentials: "include",
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    let code: string | undefined;
    let message: string | undefined;
    let detail: unknown;
    try {
      const body = JSON.parse(text) as { code?: string; message?: string; detail?: unknown };
      // FastAPI returns { detail: { code, message, ... } } for HTTPException
      const d = body.detail && typeof body.detail === "object" ? (body.detail as Record<string, unknown>) : null;
      code = (d?.code as string) ?? body.code;
      message = (d?.message as string) ?? body.message;
      detail = d ?? body.detail;
    } catch {
      message = text.slice(0, 400) || res.statusText;
    }
    const err = new Error(message ?? `HTTP ${res.status} ${res.statusText}`) as Error & {
      status?: number;
      requestId?: string;
      code?: string;
      detail?: unknown;
    };
    err.status = res.status;
    err.code = code;
    err.detail = detail;
    const reqId = res.headers.get("X-Request-ID") || useKeyRingStore.getState().lastRequestId;
    if (reqId) err.requestId = reqId;
    throw err;
  }

  if (res.status === 204) return undefined as unknown as T;
  return (await res.json()) as T;
}

/** Fetch URL as blob (e.g. file download). Uses same auth as hgFetch. */
export async function hgFetchBlob(path: string, init?: HgFetchOptions): Promise<Blob> {
  const keyClass: KeyClass = init?.keyClass ?? "operator";
  const { method, body, headers: initHeaders, ...rest } = init ?? {};

  const base = env.demoMode ? "" : env.apiBase;
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;

  let headers: Record<string, string> = {};
  if (!env.demoMode) {
    const result = getHeaders(keyClass, { baseUrl: base || undefined, skipEnvCheck: false });
    if (!result.ok) {
      if (result.reason === "locked") throw new Error("Session locked. Unlock in Settings to continue.");
      if (result.reason === "no_key") throw new Error(keyClass === "operator" ? "Operator key required. Add key in Settings." : `This action requires a ${keyClass} key. Add it in Settings.`);
      throw new Error("Unable to build request headers.");
    }
    headers = { ...result.headers };
    recordKeyUse(keyClass);
  }
  try {
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (timezone) headers["X-HG-Timezone"] = timezone;
  } catch {}

  const res = await fetch(url, {
    ...rest,
    method: method ?? "GET",
    body,
    headers: { ...headers, ...(initHeaders as Record<string, string>) },
    cache: "no-store",
    credentials: "include",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text.slice(0, 200) || res.statusText);
  }
  return res.blob();
}
