import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useConsentIndicator } from "../useConsentIndicator";

describe("useConsentIndicator", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        json: async () => ({
          ok: true,
          subject_id: "user-1",
          effective_class: "session",
          recognition_active: true,
          surface_enabled: true,
        }),
      })) as unknown as typeof fetch
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("reports recognition active when status says so", async () => {
    const { result } = renderHook(() =>
      useConsentIndicator({
        statusUrl: "http://localhost:8080/api/v1/consent/status",
        subjectId: "user-1",
        pollMs: 0,
      })
    );
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.recognitionActive).toBe(true);
    expect(result.current.effectiveClass).toBe("session");
  });

  it("stays inactive when disabled", async () => {
    const { result } = renderHook(() =>
      useConsentIndicator({
        statusUrl: "http://localhost:8080/api/v1/consent/status",
        subjectId: "user-1",
        enabled: false,
        pollMs: 0,
      })
    );
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.recognitionActive).toBe(false);
    expect(fetch).not.toHaveBeenCalled();
  });
});
