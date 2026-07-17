import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { TimeAgo } from "../TimeAgo";
import { setTimeZoneOverride } from "../../lib/timezone";

describe("U-K7 TimeAgo timezone override", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-06-09T18:00:00Z"));
    setTimeZoneOverride("America/New_York");
  });

  afterEach(() => {
    setTimeZoneOverride("");
    vi.useRealTimers();
  });

  it("renders relative time with override-aware absolute title", () => {
    render(<TimeAgo value="2026-06-09T17:30:00Z" />);
    const el = screen.getByTestId("hg-time-ago");
    expect(el.textContent).toMatch(/minute|hour|ago/i);
    expect(el.getAttribute("title")).toContain("2026");
  });
});
