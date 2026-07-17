import { describe, expect, it, beforeEach } from "vitest";
import { dismissTour, isTourDismissed, resetTourDismissal, tourStorageKey } from "./tourStorage";

describe("tourStorage", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("tracks dismissal per user", () => {
    expect(tourStorageKey("alice")).toBe("hg-guided-tour-v1:alice");
    expect(isTourDismissed("alice")).toBe(false);
    dismissTour("alice");
    expect(isTourDismissed("alice")).toBe(true);
    expect(isTourDismissed("bob")).toBe(false);
    resetTourDismissal("alice");
    expect(isTourDismissed("alice")).toBe(false);
  });
});
