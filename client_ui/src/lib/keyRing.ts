/**
 * KeyRing: routes requests by key class; builds headers for hgFetch.
 * Uses keyRingStore for state. Call getHeaders(keyClass, requestBaseUrl) to get headers;
 * if requestBaseUrl differs from key's bound baseUrl, returns null unless crossEnvConfirmedUntil > now.
 */

import type { KeyClass } from "./keyTypes";
import { newRequestId } from "./keyTypes";
import { useKeyRingStore } from "@/store/keyRingStore";

export type { KeyClass };

export type GetHeadersOptions = {
  /** Base URL for this request (for environment binding check). */
  baseUrl?: string;
  /** Skip cross-environment check (after user confirmed). */
  skipEnvCheck?: boolean;
};

export type GetHeadersResult =
  | { ok: true; headers: Record<string, string>; requestId: string }
  | { ok: false; reason: "locked" | "no_key" | "cross_env_blocked" };

/**
 * Get headers for a request. Uses key class to select key from store.
 * Returns requestId for correlation. Records lastRequestId in store for error display.
 */
export function getHeaders(
  keyClass: KeyClass,
  options: GetHeadersOptions = {}
): GetHeadersResult {
  const state = useKeyRingStore.getState();
  if (state.locked) return { ok: false, reason: "locked" };

  // Pack 13: When impersonation token is set, operator requests use Bearer only (no X-API-Key)
  if (keyClass === "operator" && state.impersonationToken) {
    const requestId = newRequestId();
    state.setLastRequestId(requestId);
    const headers: Record<string, string> = {
      "X-Request-ID": requestId,
      "Authorization": `Bearer ${state.impersonationToken}`,
    };
    return { ok: true, headers, requestId };
  }

  let entry =
    keyClass === "operator"
      ? state.operatorKey
      : keyClass === "admin"
        ? state.adminKey
        : state.serviceKey;

  // Demo / out-of-box: when no operator key is set, use NEXT_PUBLIC_DEMO_OPERATOR_KEY if set (e.g. by docker-compose.demo).
  if (keyClass === "operator" && !entry && typeof process !== "undefined" && process.env.NEXT_PUBLIC_DEMO_OPERATOR_KEY) {
    const demoKey = process.env.NEXT_PUBLIC_DEMO_OPERATOR_KEY.trim();
    if (demoKey) {
      const base = (process.env.NEXT_PUBLIC_HG_API_BASE || "http://localhost:8080").replace(/\/$/, "");
      entry = { value: demoKey, meta: { baseUrl: base, label: "Demo", lastUsedAt: "" } };
    }
  }

  if (!entry) {
    if (state.browserSession) {
      const requestId = newRequestId();
      state.setLastRequestId(requestId);
      return { ok: true, headers: { "X-Request-ID": requestId }, requestId };
    }
    return { ok: false, reason: "no_key" };
  }

  const requestBaseUrl = (options.baseUrl || "").replace(/\/$/, "") || undefined;
  const keyBaseUrl = entry.meta.baseUrl.replace(/\/$/, "");
  const crossEnv = requestBaseUrl && keyBaseUrl && requestBaseUrl !== keyBaseUrl;
  if (crossEnv && !options.skipEnvCheck && state.crossEnvConfirmedUntil < Date.now()) {
    return { ok: false, reason: "cross_env_blocked" };
  }

  const requestId = newRequestId();
  state.setLastRequestId(requestId);

  const headers: Record<string, string> = {
    "X-Request-ID": requestId,
  };

  if (keyClass === "operator") {
    headers["Authorization"] = `Bearer ${entry.value}`;
  } else if (keyClass === "admin") {
    headers["X-Admin-Key"] = entry.value;
  } else {
    headers["X-Service-Key"] = entry.value;
  }

  if (state.tenantOverride) {
    headers["X-Tenant-ID"] = state.tenantOverride;
  }

  return { ok: true, headers, requestId };
}

/**
 * Record that a key was used for a request (updates lastUsedAt in store).
 */
export function recordKeyUse(keyClass: KeyClass): void {
  useKeyRingStore.getState().recordUse(keyClass);
}
