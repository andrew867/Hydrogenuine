import type { HgSession } from "./sessionTypes";

export type SessionExpiryState = "ok" | "warning" | "expired";

export function sessionExpiryState(
  session: HgSession | null,
  nowMs = Date.now(),
  warnBeforeSec = 120,
): SessionExpiryState {
  if (!session?.expires_at) return "ok";
  const exp = Date.parse(session.expires_at);
  if (!Number.isFinite(exp)) return "ok";
  if (exp <= nowMs) return "expired";
  if (exp - nowMs <= warnBeforeSec * 1000) return "warning";
  return "ok";
}

export function minutesUntilExpiry(session: HgSession | null, nowMs = Date.now()): number | null {
  if (!session?.expires_at) return null;
  const exp = Date.parse(session.expires_at);
  if (!Number.isFinite(exp)) return null;
  return Math.max(0, Math.ceil((exp - nowMs) / 60_000));
}

export function preserveReturnUrl(currentHref: string): string {
  try {
    const url = new URL(currentHref);
    return `${url.pathname}${url.search}${url.hash}`;
  } catch {
    return currentHref;
  }
}

export function buildLoginHref(loginPath: string, returnUrl: string): string {
  const joiner = loginPath.includes("?") ? "&" : "?";
  return `${loginPath}${joiner}returnUrl=${encodeURIComponent(returnUrl)}`;
}
