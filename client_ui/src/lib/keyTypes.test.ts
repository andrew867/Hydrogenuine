/**
 * Unit tests: key types and helpers.
 */

import { describe, it, expect } from "vitest";
import { maskKey, newRequestId } from "./keyTypes";

describe("keyTypes", () => {
  describe("maskKey", () => {
    it("masks short key", () => {
      expect(maskKey("ab")).toBe("••••");
    });
    it("shows last 4 chars", () => {
      expect(maskKey("secretkey1234")).toBe("••••1234");
    });
    it("handles empty", () => {
      expect(maskKey("")).toBe("••••");
    });
  });

  describe("newRequestId", () => {
    it("returns a string", () => {
      expect(typeof newRequestId()).toBe("string");
    });
    it("returns UUID-like format", () => {
      const id = newRequestId();
      expect(id).toMatch(/^[0-9a-f-]{36}$/);
    });
  });
});
