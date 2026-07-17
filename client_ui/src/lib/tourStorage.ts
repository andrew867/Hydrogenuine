const TOUR_KEY_PREFIX = "hg-guided-tour-v1";

export function tourStorageKey(userId: string): string {
  const id = String(userId || "anonymous").trim() || "anonymous";
  return `${TOUR_KEY_PREFIX}:${id}`;
}

export function isTourDismissed(userId: string): boolean {
  if (typeof window === "undefined") return true;
  try {
    return window.localStorage.getItem(tourStorageKey(userId)) === "dismissed";
  } catch {
    return false;
  }
}

export function dismissTour(userId: string): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(tourStorageKey(userId), "dismissed");
  } catch {
    // ignore quota errors
  }
}

export function resetTourDismissal(userId: string): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(tourStorageKey(userId));
  } catch {
    // ignore
  }
}
