/**
 * Unit tests: KeyRing routing, key class, lock, and header builder.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { getHeaders, recordKeyUse } from "./keyRing";
import { restoreKeysFromSessionStorage, useKeyRingStore } from "../store/keyRingStore";

describe("keyRing", () => {
  beforeEach(() => {
    useKeyRingStore.getState().lock();
    useKeyRingStore.getState().unlock();
    useKeyRingStore.getState().clearStepupToken();
    window.sessionStorage.clear();
  });

  it("returns locked when store is locked", () => {
    useKeyRingStore.getState().lock();
    const result = getHeaders("operator");
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.reason).toBe("locked");
    }
  });

  it("returns no_key when operator key missing", () => {
    useKeyRingStore.getState().unlock();
    useKeyRingStore.getState().setAdminKey("admin1");
    const result = getHeaders("operator");
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.reason).toBe("no_key");
    }
  });

  it("returns headers with Authorization for operator key", () => {
    useKeyRingStore.getState().unlock();
    useKeyRingStore.getState().setOperatorKey("op-key");
    const result = getHeaders("operator");
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.headers["Authorization"]).toBe("Bearer op-key");
      expect(result.headers["X-API-Key"]).toBeUndefined();
      expect(result.headers["X-Request-ID"]).toBeDefined();
    }
  });

  it("returns X-Admin-Key for admin key class", () => {
    useKeyRingStore.getState().unlock();
    useKeyRingStore.getState().setAdminKey("admin-key");
    const result = getHeaders("admin");
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.headers["X-Admin-Key"]).toBe("admin-key");
      expect(result.headers["X-Request-ID"]).toBeDefined();
    }
  });

  it("does not send admin key for operator request", () => {
    useKeyRingStore.getState().unlock();
    useKeyRingStore.getState().setOperatorKey("op");
    useKeyRingStore.getState().setAdminKey("adm");
    const result = getHeaders("operator");
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.headers["X-Admin-Key"]).toBeUndefined();
      expect(result.headers["Authorization"]).toBe("Bearer op");
    }
  });

  it("recordKeyUse does not throw", () => {
    useKeyRingStore.getState().unlock();
    useKeyRingStore.getState().setOperatorKey("op");
    expect(() => recordKeyUse("operator")).not.toThrow();
  });

  it("persists and restores step-up token from session storage", () => {
    window.sessionStorage.setItem("hg_stepup_token", "stepup-demo");
    window.sessionStorage.setItem("hg_stepup_verified_at", "2026-03-07T00:00:00.000Z");

    restoreKeysFromSessionStorage(useKeyRingStore.getState, {
      setOperatorKey: useKeyRingStore.getState().setOperatorKey,
      setAdminKey: useKeyRingStore.getState().setAdminKey,
      setServiceKey: useKeyRingStore.getState().setServiceKey,
      setStepupToken: useKeyRingStore.getState().setStepupToken,
      setBrowserSession: useKeyRingStore.getState().setBrowserSession,
    });

    expect(useKeyRingStore.getState().stepupToken).toBe("stepup-demo");
    expect(useKeyRingStore.getState().stepupVerifiedAt).toBe("2026-03-07T00:00:00.000Z");
  });

  it("lock clears the stored step-up token", () => {
    useKeyRingStore.getState().setStepupToken("stepup-demo");
    useKeyRingStore.getState().lock();

    expect(useKeyRingStore.getState().stepupToken).toBeNull();
    expect(window.sessionStorage.getItem("hg_stepup_token")).toBeNull();
  });

  it("allows operator requests when browser session exists without operator key", () => {
    useKeyRingStore.getState().setBrowserSession({
      tenant_id: "default",
      principal_id: "operator",
      roles: ["operator"],
      expires_at: "2026-03-09T00:00:00Z",
    });
    const result = getHeaders("operator");
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.headers["Authorization"]).toBeUndefined();
      expect(result.headers["X-Request-ID"]).toBeDefined();
    }
  });
});
