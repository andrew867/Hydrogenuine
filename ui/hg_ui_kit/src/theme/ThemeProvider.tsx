import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { applyBrand, type BrandPalette } from "../tokens/tokens";
import { readStoredDensity, readStoredMode, writeStoredDensity, writeStoredMode } from "./themeStorage";

export type ThemeMode = "light" | "dark" | "system";
export type Density = "comfortable" | "compact";

type ThemeContextValue = {
  mode: ThemeMode;
  resolved: "light" | "dark";
  density: Density;
  setMode: (mode: ThemeMode) => void;
  setDensity: (density: Density) => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

function readSystemDark(): boolean {
  if (typeof window === "undefined") return true;
  if (typeof window.matchMedia !== "function") return true;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export type ThemeProviderProps = {
  children: React.ReactNode;
  defaultMode?: ThemeMode;
  defaultDensity?: Density;
  brand?: BrandPalette;
};

export function ThemeProvider({
  children,
  defaultMode = "dark",
  defaultDensity = "comfortable",
  brand,
}: ThemeProviderProps) {
  const [mode, setModeState] = useState<ThemeMode>(() => readStoredMode(defaultMode));
  const [density, setDensityState] = useState<Density>(() => readStoredDensity(defaultDensity));
  const [systemDark, setSystemDark] = useState(readSystemDark);
  const resolved: "light" | "dark" = mode === "system" ? (systemDark ? "dark" : "light") : mode;

  const setMode = useCallback((next: ThemeMode) => {
    setModeState(next);
    writeStoredMode(next);
  }, []);

  const setDensity = useCallback((next: Density) => {
    setDensityState(next);
    writeStoredDensity(next);
  }, []);

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return undefined;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => setSystemDark(mq.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("dark", resolved === "dark");
    root.setAttribute("data-hg-theme", resolved);
    root.setAttribute("data-hg-density", density);
    if (brand) {
      const vars = applyBrand(brand, { contrastGuard: true });
      Object.entries(vars).forEach(([k, v]) => root.style.setProperty(k, v));
    }
  }, [resolved, density, brand]);

  const value = useMemo(
    () => ({ mode, resolved, density, setMode, setDensity }),
    [mode, resolved, density],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}
