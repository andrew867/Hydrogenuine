function canonicalizeLoopbackBase(baseUrl: string, fallback: string): string {
  const base = (baseUrl || fallback).replace(/\/$/, "");
  try {
    const parsed = new URL(base);
    if (typeof window !== "undefined") {
      const currentHost = window.location.hostname;
      const loopbackHosts = new Set(["localhost", "127.0.0.1", "::1"]);
      if (currentHost && loopbackHosts.has(parsed.hostname) && loopbackHosts.has(currentHost) && parsed.hostname !== currentHost) {
        parsed.hostname = currentHost;
      }
    }
    return parsed.toString().replace(/\/$/, "");
  } catch {
    return base;
  }
}

export const env = {
  apiBase: canonicalizeLoopbackBase(process.env.NEXT_PUBLIC_HG_API_BASE || "", "http://localhost:8080"),
  sseUrl: process.env.NEXT_PUBLIC_HG_SSE_URL || "",
  wsUrl: process.env.NEXT_PUBLIC_HG_WS_URL || "",
  demoMode: process.env.NEXT_PUBLIC_HG_DEMO_MODE === "true",
  /** When true, allow X-Tenant-ID override in UI (dev only). */
  devTenantHeader: process.env.NEXT_PUBLIC_HG_DEV_TENANT_HEADER === "true",
  /** E2E: persist keys to sessionStorage so full reload (e.g. page.goto) keeps auth. */
  e2ePersistKeys: process.env.NEXT_PUBLIC_E2E_PERSIST_KEYS === "true",
  /** Operator UI Proof Viewer URL (link from client UI for proof runs). */
  operatorProofsUrl: process.env.NEXT_PUBLIC_OPERATOR_PROOFS_URL || "http://localhost:5173/#/proofs",
};
