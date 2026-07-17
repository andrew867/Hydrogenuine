const STORAGE_KEY = "hg.ui.timezone.override";
const STORAGE_PROFILE_TZ = "hg.ui.timezone.profile";
const EVENT_NAME = "hg:timezone-change";

export function getBrowserTimeZone(): string {
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    return tz && String(tz).trim() ? String(tz).trim() : "UTC";
  } catch {
    return "UTC";
  }
}

export function getTimeZoneOverride(): string | null {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return value && String(value).trim() ? String(value).trim() : null;
  } catch {
    return null;
  }
}

export function setTimeZoneOverride(value: string): void {
  try {
    const normalized = value && String(value).trim() ? String(value).trim() : "";
    if (!normalized) localStorage.removeItem(STORAGE_KEY);
    else localStorage.setItem(STORAGE_KEY, normalized);
  } catch {
    // no-op
  }
  try {
    window.dispatchEvent(new CustomEvent(EVENT_NAME));
  } catch {
    // no-op
  }
}

export function getProfileTimeZone(): string | null {
  try {
    const value = localStorage.getItem(STORAGE_PROFILE_TZ);
    return value && String(value).trim() ? String(value).trim() : null;
  } catch {
    return null;
  }
}

export function setProfileTimeZone(value: string): void {
  try {
    const normalized = value && String(value).trim() ? String(value).trim() : "";
    if (!normalized) localStorage.removeItem(STORAGE_PROFILE_TZ);
    else localStorage.setItem(STORAGE_PROFILE_TZ, normalized);
  } catch {
    // no-op
  }
  try {
    window.dispatchEvent(new CustomEvent(EVENT_NAME));
  } catch {
    // no-op
  }
}

export function getEffectiveTimeZone(): string {
  return getTimeZoneOverride() || getProfileTimeZone() || getBrowserTimeZone();
}

function toDate(value: unknown): Date | null {
  if (value == null) return null;
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value;
  if (typeof value === "number" && Number.isFinite(value)) {
    const ms = value > 10_000_000_000 ? value : value * 1000;
    const d = new Date(ms);
    return Number.isNaN(d.getTime()) ? null : d;
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) return null;
    const numeric = Number(trimmed);
    if (Number.isFinite(numeric)) {
      const ms = numeric > 10_000_000_000 ? numeric : numeric * 1000;
      const d = new Date(ms);
      return Number.isNaN(d.getTime()) ? null : d;
    }
    const d = new Date(trimmed);
    return Number.isNaN(d.getTime()) ? null : d;
  }
  return null;
}

export function formatRelativeTime(value: unknown, now = Date.now()): string {
  const d = toDate(value);
  if (!d) return "—";
  const diffSec = Math.round((d.getTime() - now) / 1000);
  const abs = Math.abs(diffSec);
  const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
  if (abs < 60) return rtf.format(diffSec, "second");
  if (abs < 3600) return rtf.format(Math.round(diffSec / 60), "minute");
  if (abs < 86400) return rtf.format(Math.round(diffSec / 3600), "hour");
  return rtf.format(Math.round(diffSec / 86400), "day");
}

export function subscribeTimeZoneChange(handler: (tz: string) => void): () => void {
  if (typeof window === "undefined") return () => {};
  const wrapped = () => handler(getEffectiveTimeZone());
  window.addEventListener(EVENT_NAME, wrapped);
  return () => window.removeEventListener(EVENT_NAME, wrapped);
}
