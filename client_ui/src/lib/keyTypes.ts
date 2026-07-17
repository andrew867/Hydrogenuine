/**
 * Key classes for HG API: operator (tenant-scoped), admin (admin endpoints only), service (explicit per-action).
 */

export type KeyClass = "operator" | "admin" | "service";

export type KeyMeta = {
  baseUrl: string;
  label: string; // e.g. "prod" | "sandbox" | "local"
  lastUsedAt: string; // ISO
  lastUsedEndpointClass?: KeyClass;
};

export function maskKey(key: string): string {
  if (!key || key.length <= 4) return "••••";
  return "••••" + key.slice(-4);
}

export function newRequestId(): string {
  return typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, c => {
        const r = (Math.random() * 16) | 0;
        const v = c === "x" ? r : (r & 0x3) | 0x8;
        return v.toString(16);
      });
}
