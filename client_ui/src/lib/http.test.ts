import { beforeEach, describe, expect, it, vi } from "vitest";
import { hgFetch } from "./http";
import { useKeyRingStore } from "@/store/keyRingStore";

describe("hgFetch", () => {
  beforeEach(() => {
    useKeyRingStore.getState().lock();
    useKeyRingStore.getState().unlock();
    useKeyRingStore.getState().setOperatorKey("demo-api-key");
    vi.restoreAllMocks();
  });

  it("does not send Content-Type on GET requests without a body", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ ok: true }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await hgFetch("/v1/tenants/me", { keyClass: "operator" });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe("GET");
    expect((init.headers as Record<string, string>)["Content-Type"]).toBeUndefined();
    expect((init.headers as Record<string, string>)["Authorization"]).toBe("Bearer demo-api-key");
    expect((init.headers as Record<string, string>)["X-API-Key"]).toBeUndefined();
    expect((init.headers as Record<string, string>)["X-HG-Timezone"]).toBeTruthy();
  });

  it("sends Content-Type on JSON requests with a body", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ ok: true }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await hgFetch("/v1/chats", {
      method: "POST",
      body: JSON.stringify({ title: "Test" }),
      keyClass: "operator",
    });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe("POST");
    expect((init.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
    expect((init.headers as Record<string, string>)["Authorization"]).toBe("Bearer demo-api-key");
    expect((init.headers as Record<string, string>)["X-API-Key"]).toBeUndefined();
  });
});
