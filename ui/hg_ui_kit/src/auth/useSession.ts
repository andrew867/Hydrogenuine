import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { parseSessionPayload, type HgSession } from "./sessionTypes";

export type UseSessionOptions = {
  meUrl: string;
  enabled?: boolean;
  fetchImpl?: typeof fetch;
};

export type UseSessionResult = {
  session: HgSession | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<HgSession | null>;
};

export async function fetchSession(
  meUrl: string,
  fetchImpl: typeof fetch = fetch,
): Promise<HgSession | null> {
  const res = await fetchImpl(meUrl, { credentials: "include" });
  if (res.status === 401) return null;
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return parseSessionPayload(await res.json());
}

export function useSession({
  meUrl,
  enabled = true,
  fetchImpl = fetch,
}: UseSessionOptions): UseSessionResult {
  const [session, setSession] = useState<HgSession | null>(null);
  const [loading, setLoading] = useState(Boolean(enabled));
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(true);

  const refresh = useCallback(async () => {
    if (!enabled) {
      setSession(null);
      setLoading(false);
      return null;
    }
    setLoading(true);
    setError(null);
    try {
      const next = await fetchSession(meUrl, fetchImpl);
      if (mounted.current) setSession(next);
      return next;
    } catch (err) {
      if (mounted.current) {
        setError(err instanceof Error ? err.message : "Session fetch failed");
        setSession(null);
      }
      return null;
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, [enabled, fetchImpl, meUrl]);

  useEffect(() => {
    mounted.current = true;
    void refresh();
    return () => {
      mounted.current = false;
    };
  }, [refresh]);

  return useMemo(() => ({ session, loading, error, refresh }), [session, loading, error, refresh]);
}
