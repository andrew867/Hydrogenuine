import React, { useEffect, useMemo, useState } from "react";
import { Modal } from "./Overlay";
import { Input } from "./Input";
import { PaletteAction, searchActions } from "../lib/fuzzyMatch";

export function CommandPalette({
  open,
  onClose,
  actions,
  onQueryChange,
}: {
  open: boolean;
  onClose: () => void;
  actions: PaletteAction[];
  onQueryChange?: (query: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const results = useMemo(() => searchActions(actions, query), [actions, query]);

  useEffect(() => {
    if (!open) {
      setQuery("");
      setActiveIndex(0);
    }
  }, [open]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  const runActive = () => {
    const action = results[activeIndex];
    if (!action) return;
    action.run();
    onClose();
  };

  return (
    <Modal open={open} onClose={onClose}>
      <div style={{ padding: 16 }} data-testid="hg-command-palette">
        <Input
          autoFocus
          placeholder="Search commands…"
          value={query}
          onChange={(e) => {
            const next = e.target.value;
            setQuery(next);
            onQueryChange?.(next);
          }}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setActiveIndex((i) => Math.min(i + 1, results.length - 1));
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setActiveIndex((i) => Math.max(i - 1, 0));
            } else if (e.key === "Enter") {
              e.preventDefault();
              runActive();
            }
          }}
        />
        <ul style={{ listStyle: "none", padding: 0, marginTop: 12, maxHeight: 320, overflow: "auto" }}>
          {results.map((action, index) => (
            <li key={action.id}>
              <button
                type="button"
                className="hg-btn"
                data-testid={`hg-palette-action-${action.id}`}
                style={{
                  width: "100%",
                  justifyContent: "flex-start",
                  background: index === activeIndex ? "var(--hg-accent-subtle)" : undefined,
                }}
                onClick={() => {
                  action.run();
                  onClose();
                }}
              >
                {action.label}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </Modal>
  );
}
