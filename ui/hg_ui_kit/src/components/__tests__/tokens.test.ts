import { describe, expect, it, vi } from "vitest";
import { applyBrand, contrastRatio, semanticTokenPairs } from "../../tokens/tokens";

const LIGHT = {
  "--hg-text-primary": "#0f172a",
  "--hg-surface-base": "#f4f6fb",
  "--hg-text-secondary": "#475569",
  "--hg-surface-raised": "#ffffff",
  "--hg-text-muted": "#64748b",
  "--hg-accent": "#0369a1",
};

const DARK = {
  "--hg-text-primary": "#e6e8ef",
  "--hg-surface-base": "#0b0f14",
  "--hg-text-secondary": "#b8c0d0",
  "--hg-surface-raised": "#121826",
  "--hg-text-muted": "#9aa3b2",
  "--hg-accent": "#6cc5ff",
};

function pairContrast(palette: Record<string, string>, textVar: string, surfaceVar: string): number {
  return contrastRatio(palette[textVar], palette[surfaceVar]);
}

describe("U-K1 token contrast", () => {
  it("light theme semantic pairs meet WCAG 4.5:1", () => {
    for (const pair of semanticTokenPairs) {
      expect(pairContrast(LIGHT, pair.text, pair.surface)).toBeGreaterThanOrEqual(4.5);
    }
  });

  it("dark theme semantic pairs meet WCAG 4.5:1", () => {
    for (const pair of semanticTokenPairs) {
      expect(pairContrast(DARK, pair.text, pair.surface)).toBeGreaterThanOrEqual(4.5);
    }
  });
});

describe("U-K2 brand override guard", () => {
  it("adjusts failing accent and logs warning", () => {
    const warn = vi.fn();
    const vars = applyBrand({ accent: "#333333", surfaceBase: "#0b0f14" }, { warn });
    expect(warn).toHaveBeenCalled();
    expect(contrastRatio(vars["--hg-accent"], "#0b0f14")).toBeGreaterThanOrEqual(4.5);
  });
});
