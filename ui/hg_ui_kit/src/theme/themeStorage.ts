import type { Density, ThemeMode } from "./ThemeProvider";

const MODE_KEY = "hg-theme-mode";
const DENSITY_KEY = "hg-theme-density";

export function readStoredMode(fallback: ThemeMode): ThemeMode {
  if (typeof window === "undefined") return fallback;
  const value = window.localStorage.getItem(MODE_KEY);
  if (value === "light" || value === "dark" || value === "system") return value;
  return fallback;
}

export function writeStoredMode(mode: ThemeMode): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(MODE_KEY, mode);
}

export function readStoredDensity(fallback: Density): Density {
  if (typeof window === "undefined") return fallback;
  const value = window.localStorage.getItem(DENSITY_KEY);
  if (value === "comfortable" || value === "compact") return value;
  return fallback;
}

export function writeStoredDensity(density: Density): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(DENSITY_KEY, density);
}
