import { useCallback, useEffect, useState } from "react";

export type ConsentStatus = {
  ok?: boolean;
  subject_id?: string;
  effective_class?: string;
  recognition_active?: boolean;
  surface_enabled?: boolean;
  active_grants?: Array<Record<string, unknown>>;
};

export type UseConsentIndicatorOptions = {
  statusUrl: string;
  subjectId: string;
  headers?: Record<string, string> | (() => Record<string, string>);
  enabled?: boolean;
  pollMs?: number;
};

export function useConsentIndicator({
  statusUrl,
  subjectId,
  headers,
  enabled = true,
  pollMs = 15000,
}: UseConsentIndicatorOptions) {
  const [status, setStatus] = useState<ConsentStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!enabled || !subjectId) {
      setStatus(null);
      setLoading(false);
      return;
    }
    setError(null);
    try {
      const hdrs = typeof headers === "function" ? headers() : headers || {};
      const url = new URL(statusUrl, window.location.origin);
      url.searchParams.set("subject_id", subjectId);
      const res = await fetch(url.toString(), { headers: hdrs, credentials: "include" });
      if (!res.ok) {
        throw new Error(`consent_status_${res.status}`);
      }
      const body = (await res.json()) as ConsentStatus;
      setStatus(body);
    } catch (err) {
      setError(err instanceof Error ? err.message : "consent_status_failed");
      setStatus(null);
    } finally {
      setLoading(false);
    }
  }, [enabled, headers, statusUrl, subjectId]);

  useEffect(() => {
    setLoading(true);
    load();
    if (!enabled || pollMs <= 0) return undefined;
    const timer = window.setInterval(load, pollMs);
    return () => window.clearInterval(timer);
  }, [enabled, load, pollMs]);

  const recognitionActive = Boolean(status?.recognition_active);
  const effectiveClass = status?.effective_class || "none";

  return {
    status,
    loading,
    error,
    recognitionActive,
    effectiveClass,
    refresh: load,
  };
}
