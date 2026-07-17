import React from "react";
import { useTheme, type Density, type ThemeMode } from "../theme/ThemeProvider";

const MODES: Array<{ id: ThemeMode; label: string }> = [
  { id: "light", label: "Light" },
  { id: "dark", label: "Dark" },
  { id: "system", label: "System" },
];

const DENSITIES: Array<{ id: Density; label: string }> = [
  { id: "comfortable", label: "Comfortable" },
  { id: "compact", label: "Compact" },
];

export type ThemeToggleProps = {
  showDensity?: boolean;
  className?: string;
};

export function ThemeToggle({ showDensity = true, className }: ThemeToggleProps) {
  const { mode, setMode, density, setDensity, resolved } = useTheme();

  return (
    <div className={className} data-testid="theme-toggle">
      <fieldset className="hg-theme-fieldset">
        <legend className="hg-theme-legend">Appearance</legend>
        <p className="hg-theme-hint">
          Active theme: <strong>{resolved}</strong>
          {mode === "system" ? " (follows system)" : ""}
        </p>
        <div className="hg-theme-options" role="radiogroup" aria-label="Color theme">
          {MODES.map((item) => (
            <label key={item.id} className="hg-theme-option">
              <input
                type="radio"
                name="hg-theme-mode"
                value={item.id}
                checked={mode === item.id}
                onChange={() => setMode(item.id)}
              />
              {item.label}
            </label>
          ))}
        </div>
        {showDensity ? (
          <div className="hg-theme-options" role="radiogroup" aria-label="Interface density" style={{ marginTop: 12 }}>
            {DENSITIES.map((item) => (
              <label key={item.id} className="hg-theme-option">
                <input
                  type="radio"
                  name="hg-theme-density"
                  value={item.id}
                  checked={density === item.id}
                  onChange={() => setDensity(item.id)}
                />
                {item.label}
              </label>
            ))}
          </div>
        ) : null}
      </fieldset>
    </div>
  );
}
