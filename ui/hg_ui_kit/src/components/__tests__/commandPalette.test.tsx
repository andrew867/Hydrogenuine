import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { CommandPalette } from "../CommandPalette";
import { searchActions, type PaletteAction } from "../../lib/fuzzyMatch";

describe("U-K8 CommandPalette", () => {
  const actions: PaletteAction[] = [
    { id: "runs", label: "Go to Runs", keywords: ["operate"], recency: 10, run: vi.fn() },
    { id: "approvals", label: "Open Approvals", recency: 100, run: vi.fn() },
  ];

  it("ranks fuzzy matches with recency", () => {
    const ranked = searchActions(actions, "app");
    expect(ranked[0]?.id).toBe("approvals");
  });

  it("invokes action on Enter", () => {
    const run = vi.fn();
    const paletteActions = [{ id: "home", label: "Home", run }];
    render(<CommandPalette open onClose={() => {}} actions={paletteActions} />);
    const input = screen.getByPlaceholderText("Search commands…");
    fireEvent.change(input, { target: { value: "hom" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(run).toHaveBeenCalled();
  });
});
