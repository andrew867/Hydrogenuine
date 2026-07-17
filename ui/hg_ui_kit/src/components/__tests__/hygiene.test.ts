import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(__dirname, "../../../../../");

describe("U-A3 product API hygiene", () => {
  it("product api.js uses only product v1 endpoints", () => {
    const source = readFileSync(resolve(root, "product_console/ui/src/lib/api.js"), "utf8");
    expect(source).not.toMatch(/\/api\/v1/);
    expect(source).not.toMatch(/\bAPI_KEY\b/);
    expect(source).not.toMatch(/eventsStreamUrl/);
    expect(source).toContain("/api/product/v1");
  });
});

describe("U-A5 deleted symbol grep (source)", () => {
  it("removed client dead modules are gone", () => {
    const paths = [
      "client_ui/src/lib/steeringApi.ts",
      "client_ui/src/server/mockDb.ts",
    ];
    for (const rel of paths) {
      expect(() => readFileSync(resolve(root, rel), "utf8")).toThrow();
    }
  });

  it("operator api.js does not reference legacy key storage", () => {
    const source = readFileSync(resolve(root, "operator_console/ui/src/lib/api.js"), "utf8");
    expect(source).not.toMatch(/oc_api_key/);
    expect(source).not.toMatch(/oc_admin_key/);
    expect(source).not.toMatch(/loginWithKeys/);
    expect(source).not.toMatch(/import\.meta\.env\.VITE_API_KEY/);
    expect(source).not.toMatch(/\?api_key=/);
    expect(source).toContain("stream_token");
  });
});
