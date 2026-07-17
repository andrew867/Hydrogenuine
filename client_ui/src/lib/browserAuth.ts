import { env } from "@/lib/env";
import type { BrowserSession } from "@/store/keyRingStore";
import { useKeyRingStore } from "@/store/keyRingStore";

function gatewayV1(path: string): string {
  const base = env.apiBase.replace(/\/$/, "");
  return `${base}/v1${path}`;
}

export async function fetchBrowserAuthConfig(): Promise<{
  oidc_enabled: boolean;
  supports_key_exchange_login: boolean;
}> {
  const res = await fetch(gatewayV1("/auth/config"), { credentials: "include" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function refreshBrowserSession(): Promise<BrowserSession | null> {
  const res = await fetch(gatewayV1("/auth/me"), { credentials: "include" });
  if (res.status === 401) {
    useKeyRingStore.getState().setBrowserSession(null);
    return null;
  }
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = (await res.json()) as BrowserSession;
  useKeyRingStore.getState().setBrowserSession(data);
  return data;
}

export async function loginBrowserSessionWithKeys(operatorKey?: string | null, adminKey?: string | null): Promise<BrowserSession> {
  const res = await fetch(gatewayV1("/auth/session/login"), {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      operator_key: operatorKey || null,
      admin_key: adminKey || null,
    }),
  });
  const ct = res.headers.get("content-type") || "";
  if (!res.ok) {
    const txt = ct.includes("application/json") ? JSON.stringify(await res.json()) : await res.text();
    throw new Error(`HTTP ${res.status}: ${txt}`);
  }
  const data = (await res.json()) as BrowserSession;
  useKeyRingStore.getState().setBrowserSession(data);
  return data;
}

export async function logoutBrowserSession(): Promise<void> {
  await fetch(gatewayV1("/auth/logout"), {
    method: "POST",
    credentials: "include",
  });
  useKeyRingStore.getState().setBrowserSession(null);
}

export function startOidcLogin(frontendRedirectUri: string): void {
  window.location.assign(`${gatewayV1("/auth/oidc/start")}?frontend_redirect_uri=${encodeURIComponent(frontendRedirectUri)}`);
}

export function startOidcLogout(frontendRedirectUri: string): void {
  window.location.assign(`${gatewayV1("/auth/oidc/logout")}?frontend_redirect_uri=${encodeURIComponent(frontendRedirectUri)}`);
}
