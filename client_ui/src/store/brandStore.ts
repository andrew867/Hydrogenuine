/**
 * Pack 13 / U3: Host-derived branding (GET /v1/ui/brand). Applied on load with kit contrast guard.
 */

import { create } from "zustand";
import { applyBrand } from "hg_ui_kit";
import type { UiBrand } from "@/types/hg";

type BrandState = {
  brand: UiBrand | null;
  setBrand: (b: UiBrand | null) => void;
};

function resolvePalette(brand: UiBrand) {
  const palettes = brand.palettes;
  const dark = palettes?.dark;
  if (dark && typeof dark === "object") {
    return {
      accent: dark.accent || (brand.theme?.primaryColor as string | undefined),
      surfaceBase: dark.surfaceBase || (brand.theme?.backgroundColor as string | undefined),
      textPrimary: dark.textPrimary || (brand.theme?.textPrimary as string | undefined),
    };
  }
  const theme = brand.theme || {};
  return {
    accent: (theme.primaryColor as string | undefined) || (theme.accent as string | undefined),
    surfaceBase: (theme.backgroundColor as string | undefined) || (theme.surfaceBase as string | undefined),
    textPrimary: theme.textPrimary as string | undefined,
  };
}

function applyBrandToDocument(brand: UiBrand) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  const vars = applyBrand(resolvePalette(brand), { contrastGuard: true });
  Object.entries(vars).forEach(([key, value]) => {
    root.style.setProperty(key, value);
    if (key === "--hg-accent") root.style.setProperty("--accent", value);
    if (key === "--hg-surface-base") root.style.setProperty("--bg", value);
    if (key === "--hg-text-primary") root.style.setProperty("--text", value);
  });
  const favicon = brand.favicon_url;
  if (favicon) {
    let link = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
    if (!link) {
      link = document.createElement("link");
      link.rel = "icon";
      document.head.appendChild(link);
    }
    link.href = favicon.startsWith("http") ? favicon : `${window.location.origin}${favicon}`;
  }
}

export const useBrandStore = create<BrandState>((set) => ({
  brand: null,
  setBrand(b) {
    if (b) applyBrandToDocument(b);
    set({ brand: b });
  },
}));
