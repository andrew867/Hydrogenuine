"use client";

import React from "react";
import { useKeyRingStore } from "@/store/keyRingStore";
import { useRouter } from "next/navigation";

/**
 * Pack 13: Persistent banner when using impersonation token. "Stop impersonating" clears token and reloads.
 */
export function ImpersonationBanner() {
  const { impersonationToken, impersonationTenantId, setImpersonationToken } = useKeyRingStore();
  const router = useRouter();

  if (!impersonationToken) return null;

  const stopImpersonating = () => {
    setImpersonationToken(null, null);
    router.refresh();
    window.location.reload();
  };

  return (
    <div className="flex items-center justify-between gap-2 px-3 py-1.5 bg-amber-500/20 border-b border-amber-500/40 text-amber-900 dark:text-amber-100 text-sm">
      <span>Impersonating tenant: <strong>{impersonationTenantId ?? "—"}</strong></span>
      <button
        type="button"
        onClick={stopImpersonating}
        className="px-2 py-1 rounded bg-amber-500/30 hover:bg-amber-500/50 font-medium"
      >
        Stop impersonating
      </button>
    </div>
  );
}
