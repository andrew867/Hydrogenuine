import { describe, expect, it } from "vitest";
import { fetchSession } from "../useSession";
import { parseSessionPayload } from "../sessionTypes";
import { sessionExpiryState } from "../sessionExpiry";

describe("U-K10 useSession", () => {
  it("parses gateway /auth/me payloads", () => {
    const session = parseSessionPayload({
      tenant_id: "acme",
      principal_id: "p-1",
      roles: ["operator", "superadmin"],
      expires_at: "2030-01-01T00:00:00Z",
      impersonating: true,
      impersonation_tenant_id: "beta",
    });
    expect(session?.tenant_id).toBe("acme");
    expect(session?.roles).toContain("superadmin");
    expect(session?.impersonating).toBe(true);
  });

  it("fetchSession returns null on 401", async () => {
    const fetchImpl = async () => new Response(null, { status: 401 });
    await expect(fetchSession("http://example.test/v1/auth/me", fetchImpl)).resolves.toBeNull();
  });

  it("fetchSession memoizes roles from payload", async () => {
    const fetchImpl = async () =>
      new Response(
        JSON.stringify({
          tenant_id: "default",
          principal_id: "demo",
          roles: ["tenant_admin"],
          expires_at: "2030-01-01T00:00:00Z",
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    const session = await fetchSession("http://example.test/v1/auth/me", fetchImpl);
    expect(session?.roles).toEqual(["tenant_admin"]);
    expect(parseSessionPayload(session)).toEqual(session);
  });

  it("sessionExpiryState warns before expiry", () => {
    const soon = new Date(Date.now() + 60_000).toISOString();
    expect(
      sessionExpiryState(
        { tenant_id: "t", principal_id: "p", roles: ["operator"], expires_at: soon },
        Date.now(),
        120,
      ),
    ).toBe("warning");
  });
});
