import { expect, test } from "@playwright/test";

const OIDC_USER = process.env.E2E_OIDC_USER || "demo-operator";
const OIDC_PASSWORD = process.env.E2E_OIDC_PASSWORD || "demo-operator";
const AUTH_ME_URL = process.env.E2E_AUTH_ME_URL || "http://localhost:8080/v1/auth/me";

test.describe("Client SSO login", () => {
  test("completes Keycloak SSO and stays logged in", async ({ page }) => {
    await page.goto("/login?logged_out=1", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("button", { name: /continue with sso/i })).toBeVisible();
    await expect(page.getByText(/api key/i)).toHaveCount(0);
    await page.screenshot({ path: "test-results/client-oidc-login-start.png", fullPage: true });

    await Promise.all([
      page.waitForURL(/realms\/hg\/protocol\/openid-connect\/auth/, { timeout: 20000 }),
      page.getByRole("button", { name: /continue with sso/i }).click(),
    ]);

    await expect(page.locator('input[name="username"]')).toBeVisible({ timeout: 20000 });
    await page.locator('input[name="username"]').fill(OIDC_USER);
    await page.locator('input[name="password"]').fill(OIDC_PASSWORD);

    await Promise.all([
      page.waitForURL(/localhost:3001|127\.0\.0\.1:3001/, { timeout: 30000 }),
      page.locator("#kc-login").click(),
    ]);

    await expect(page).toHaveURL(/\/(#\/)?$/, { timeout: 30000 });
    await expect(page.getByText(/operator console|hydrogenuine/i).or(page.getByText(/go to app/i)).first()).toBeVisible({ timeout: 15000 });

    const authMe = await page.evaluate(async (url) => {
      const res = await fetch(url, { credentials: "include" });
      return { status: res.status, body: await res.text() };
    }, AUTH_ME_URL);
    expect(authMe.status, authMe.body).toBe(200);

    await page.screenshot({ path: "test-results/client-oidc-login-success.png", fullPage: true });
  });
});
