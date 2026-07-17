import { describe, expect, it } from "vitest";
import { visibilityAwareRefetchInterval } from "../useVisibilityAwareInterval";

describe("useVisibilityAwareInterval (U-K9)", () => {
  it("visibilityAwareRefetchInterval returns false when document is hidden", () => {
    const original = Object.getOwnPropertyDescriptor(document, "hidden");
    Object.defineProperty(document, "hidden", { configurable: true, value: true });
    expect(visibilityAwareRefetchInterval(30_000)).toBe(false);
    Object.defineProperty(document, "hidden", { configurable: true, value: false });
    expect(visibilityAwareRefetchInterval(30_000)).toBe(30_000);
    if (original) Object.defineProperty(document, "hidden", original);
  });
});
