export const TOKEN_PATHS = [
  "fingerprint_schema_version",
  "cognitive_fingerprint",
  "lineage",
  "interaction_rules",
] as const;

export type BrandPalette = {
  accent?: string;
  surfaceBase?: string;
  textPrimary?: string;
};

export type ApplyBrandOptions = {
  contrastGuard?: boolean;
  warn?: (message: string) => void;
};

function hexToRgb(hex: string): [number, number, number] | null {
  const m = hex.replace("#", "").match(/^([0-9a-f]{6})$/i);
  if (!m) return null;
  const n = parseInt(m[1], 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function relativeLuminance([r, g, b]: [number, number, number]): number {
  const s = [r, g, b].map((v) => {
    const c = v / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * s[0] + 0.7152 * s[1] + 0.0722 * s[2];
}

export function contrastRatio(foreground: string, background: string): number {
  const fg = hexToRgb(foreground);
  const bg = hexToRgb(background);
  if (!fg || !bg) return 21;
  const l1 = relativeLuminance(fg);
  const l2 = relativeLuminance(bg);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

export function applyBrand(
  brand: BrandPalette,
  options: ApplyBrandOptions = {},
): Record<string, string> {
  const guard = options.contrastGuard !== false;
  const surface = brand.surfaceBase || "#0b0f14";
  let accent = brand.accent || "#6cc5ff";
  if (guard && contrastRatio(accent, surface) < 4.5) {
    const adjusted = "#9dd9ff";
    options.warn?.(`brand accent failed contrast; adjusted ${accent} -> ${adjusted}`);
    accent = adjusted;
  }
  return {
    "--hg-accent": accent,
    "--hg-surface-base": surface,
    ...(brand.textPrimary ? { "--hg-text-primary": brand.textPrimary } : {}),
  };
}

export const semanticTokenPairs = [
  { text: "--hg-text-primary", surface: "--hg-surface-base" },
  { text: "--hg-text-secondary", surface: "--hg-surface-raised" },
  { text: "--hg-text-muted", surface: "--hg-surface-raised" },
  { text: "--hg-accent", surface: "--hg-surface-base" },
] as const;
