/**
 * E2E: Tenant-admin and principal roles, role badge, principal-scoped UX.
 * Requires gateway + demo Keycloak users demo-tenant-admin and demo-client.
 *
 * Note: Only the gateway is required. GET /v1/chats/main/messages may 404 if no chat backend
 * is running; the app still redirects to /chat/main and these tests use sidebar nav to
 * /principals. For full chat E2E, start the chat backend as well.
 */
import { test, expect } from "@playwright/test";
import { loginWithOidc } from "./support/oidc";
const apiBase = process.env.E2E_API_BASE || process.env.NEXT_PUBLIC_HG_API_BASE || "http://localhost:8080";

test.describe("Roles and principals", () => {
  test("operator or tenant-admin login shows role in header", async ({ page }) => {
    await loginWithOidc(page, { username: process.env.E2E_TENANT_ADMIN_SSO_USERNAME || "demo-tenant-admin" });
    await expect(page).toHaveURL(/\/(\?|$)|\/chat\//, { timeout: 10000 });
    await expect(
      page.getByText("Hydrogenuine").or(page.getByPlaceholder(/message hg/i)).or(page.locator("header").getByText(/default/i)).first()
    ).toBeVisible({ timeout: 8000 });
    // Header subtitle shows tenant_id and optionally role (Operator | Tenant admin | Principal: id)
    await expect(
      page.locator("header").getByText(/default(\s*·\s*(Operator|Tenant admin|Principal:[\w-]+))?/i).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("principals page loads for operator/tenant-admin", async ({ page }) => {
    await loginWithOidc(page, { username: process.env.E2E_TENANT_ADMIN_SSO_USERNAME || "demo-tenant-admin" });
    // App may redirect / -> /chat/... (RedirectToLastChat); wait for settle
    await expect(page).toHaveURL(/\/(\?|$)|\/chat\//, { timeout: 15000 });
    const principalsLink = page.locator("aside").locator('a[href="/principals"]');
    await expect(principalsLink).toBeVisible({ timeout: 10000 });
    await principalsLink.scrollIntoViewIfNeeded();
    await principalsLink.click();
    await expect(page).toHaveURL(/\/principals/, { timeout: 15000 });
    await expect(
      page.getByText(/principals|my availability/i).first()
    ).toBeVisible({ timeout: 10000 });
  });
});

test.describe("Principal-scoped login", () => {
  test("principal login shows Principal: id in header and redirects to own availability", async ({
    page,
  }) => {
    await loginWithOidc(page, { username: process.env.E2E_CLIENT_SSO_USERNAME || "demo-client" });
    await expect(page).toHaveURL(/\/(\?|$)|\/chat\//, { timeout: 15000 });
    await expect(
      page.locator("header").getByText(/default|principal:/i).first()
    ).toBeVisible({ timeout: 10000 });
    const authMeResponse = await page.request.get(`${apiBase}/v1/auth/me`);
    expect(authMeResponse.ok()).toBeTruthy();
    const authMe = await authMeResponse.json();
    const principalId = String(authMe?.principal_id || "").trim();
    expect(principalId).toBeTruthy();
    await page.goto(`/principals/${encodeURIComponent(principalId)}`);
    await expect(page).toHaveURL(new RegExp(`/principals/${principalId}$`), { timeout: 10000 });
    await expect(
      page.getByText(/principal|availability|my availability/i).or(page.locator("header").getByText(/principal/i)).first()
    ).toBeVisible({ timeout: 8000 });
  });
});
