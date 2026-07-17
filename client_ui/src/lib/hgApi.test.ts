/**
 * Unit tests: hgApi endpoint key class metadata and tenant/principal behavior.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { hgApi, hgApiKeyClass } from "./hgApi";

vi.mock("@/lib/http", () => ({ hgFetch: vi.fn() }));

import { hgFetch } from "@/lib/http";

describe("hgApiKeyClass", () => {
  it("assigns operator to tenant and chat endpoints", () => {
    expect(hgApiKeyClass.getTenantMe).toBe("operator");
    expect(hgApiKeyClass.getTenantUsage).toBe("operator");
    expect(hgApiKeyClass.listChats).toBe("operator");
    expect(hgApiKeyClass.listPrincipals).toBe("operator");
  });

  it("assigns admin to admin endpoints", () => {
    expect(hgApiKeyClass.listTenantsAdmin).toBe("admin");
    expect(hgApiKeyClass.patchTenantQuotas).toBe("admin");
    expect(hgApiKeyClass.adminPing).toBe("admin");
  });
});

describe("hgApi tenant and principal", () => {
  beforeEach(() => {
    vi.mocked(hgFetch).mockReset();
  });

  it("getTenantMe returns TenantInfo with role and principal_id when present", async () => {
    vi.mocked(hgFetch).mockResolvedValue({
      tenant_id: "default",
      environment: "prod",
      limits: {},
      usage: {},
      role: "principal",
      principal_id: "p1",
    });
    const out = await hgApi.getTenantMe();
    expect(out).not.toBeNull();
    expect(out!.role).toBe("principal");
    expect(out!.principal_id).toBe("p1");
    expect(vi.mocked(hgFetch)).toHaveBeenCalledWith("/v1/tenants/me", { keyClass: "operator" });
  });

  it("getTenantMe returns operator role when API omits role", async () => {
    vi.mocked(hgFetch).mockResolvedValue({
      tenant_id: "default",
      environment: "prod",
      limits: {},
      usage: {},
    });
    const out = await hgApi.getTenantMe();
    expect(out?.role).toBeUndefined();
  });

  it("listPrincipals uses include_disabled query when true", async () => {
    vi.mocked(hgFetch).mockResolvedValue({ principals: [] });
    await hgApi.listPrincipals(true);
    expect(vi.mocked(hgFetch)).toHaveBeenCalledWith("/v1/principals?include_disabled=true", { keyClass: "operator" });
  });

  it("listPrincipals omits query when includeDisabled false or undefined", async () => {
    vi.mocked(hgFetch).mockResolvedValue({ principals: [] });
    await hgApi.listPrincipals();
    expect(vi.mocked(hgFetch)).toHaveBeenCalledWith("/v1/principals", { keyClass: "operator" });
  });

  it("updatePrincipalAvailability sends disabled in body", async () => {
    vi.mocked(hgFetch).mockResolvedValue(undefined);
    await hgApi.updatePrincipalAvailability("p1", { disabled: true });
    expect(vi.mocked(hgFetch)).toHaveBeenCalledWith(
      "/v1/principals/p1/availability",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ disabled: true }),
        keyClass: "operator",
      })
    );
  });

  it("getChatTraits returns effective traits plus override map", async () => {
    vi.mocked(hgFetch).mockResolvedValue({
      ok: true,
      traits: { "communication.directness": 0.9, "reasoning_style.systems_first": 0.8 },
      trait_overrides: { "communication.directness": 0.9 },
    });
    const out = await hgApi.getChatTraits("chat-1");
    expect(out.traits["communication.directness"]).toBe(0.9);
    expect(out.traitOverrides).toEqual({ "communication.directness": 0.9 });
  });

  it("putChatTraits returns refreshed effective traits plus override map", async () => {
    vi.mocked(hgFetch).mockResolvedValue({
      ok: true,
      traits: { "communication.directness": 0.7 },
      trait_overrides: { "communication.directness": 0.7 },
    });
    const out = await hgApi.putChatTraits("chat-1", { "communication.directness": 0.7 });
    expect(out.traits["communication.directness"]).toBe(0.7);
    expect(vi.mocked(hgFetch)).toHaveBeenCalledWith(
      "/v1/chats/chat-1/traits",
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({ traits: { "communication.directness": 0.7 } }),
        keyClass: "operator",
      })
    );
  });

  it("listChats forwards deleted filters", async () => {
    vi.mocked(hgFetch).mockResolvedValue({ chats: [] });
    await hgApi.listChats({ includeDeleted: true, deletedOnly: true, includeArchived: true });
    expect(vi.mocked(hgFetch)).toHaveBeenCalledWith(
      "/v1/chats?include_archived=true&include_deleted=true&deleted_only=true",
      { keyClass: "operator" }
    );
  });
});
