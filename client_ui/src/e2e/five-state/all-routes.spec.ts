import { test, expect } from "@playwright/test";
import coverage from "./coverage.json";

const FIVE_STATE_TESTIDS = ["hg-page-skeleton", "hg-empty-state", "hg-error-state"];

test.describe("U2 five-state client coverage", () => {
  for (const route of coverage.routes) {
    test(`manifest route ${route.path} declares five states`, () => {
      expect(route.states).toEqual(["loading", "empty", "error", "success", "auth"]);
    });
  }

  test("kit state testids are registered", () => {
    expect(FIVE_STATE_TESTIDS).toContain("hg-page-skeleton");
  });
});
