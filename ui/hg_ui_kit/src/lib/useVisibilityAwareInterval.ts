import { useEffect, useRef } from "react";

export type VisibilityAwareIntervalOptions = {
  enabled?: boolean;
  intervalMs: number;
  onTick: () => void;
  /** Pause polling while document is hidden (default true). */
  pauseWhenHidden?: boolean;
};

/**
 * Interval that respects Page Visibility — dashboards poll 15–60s and pause when hidden.
 */
export function useVisibilityAwareInterval({
  enabled = true,
  intervalMs,
  onTick,
  pauseWhenHidden = true,
}: VisibilityAwareIntervalOptions) {
  const onTickRef = useRef(onTick);
  onTickRef.current = onTick;

  useEffect(() => {
    if (!enabled || intervalMs <= 0) return undefined;
    let timer: ReturnType<typeof setInterval> | null = null;

    const clear = () => {
      if (timer) {
        clearInterval(timer);
        timer = null;
      }
    };

    const start = () => {
      clear();
      timer = setInterval(() => onTickRef.current(), intervalMs);
    };

    const sync = () => {
      if (!enabled) return;
      if (pauseWhenHidden && typeof document !== "undefined" && document.hidden) {
        clear();
        return;
      }
      start();
    };

    sync();
    const onVisibility = () => sync();
    if (typeof document !== "undefined") {
      document.addEventListener("visibilitychange", onVisibility);
    }
    return () => {
      clear();
      if (typeof document !== "undefined") {
        document.removeEventListener("visibilitychange", onVisibility);
      }
    };
  }, [enabled, intervalMs, pauseWhenHidden]);
}

/** React Query refetchInterval helper: returns false when tab hidden. */
export function visibilityAwareRefetchInterval(intervalMs: number): number | false {
  if (typeof document !== "undefined" && document.hidden) return false;
  return intervalMs;
}
