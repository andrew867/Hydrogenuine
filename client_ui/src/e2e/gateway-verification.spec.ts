/**
 * E2E: Verify hg_client_ui against real gateway.
 * Requires gateway at NEXT_PUBLIC_HG_API_BASE (e.g. http://localhost:8000) with HG_GATEWAY_DEV=1.
 * Run: npx playwright test gateway-verification
 */
import { test, expect } from "@playwright/test";

const oidcUser = process.env.E2E_OIDC_USER || "demo-operator";
const oidcPassword = process.env.E2E_OIDC_PASSWORD || "demo-operator";

async function login(page: import("@playwright/test").Page) {
  await page.goto("/login?logged_out=1", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("button", { name: /continue with sso/i })).toBeVisible({ timeout: 15000 });
  await page.getByRole("button", { name: /continue with sso/i }).click();
  await expect(page.locator('input[name="username"]')).toBeVisible({ timeout: 20000 });
  await page.locator('input[name="username"]').fill(oidcUser);
  await page.locator('input[name="password"]').fill(oidcPassword);
  await page.locator('#kc-login').click();
  await expect(page).toHaveURL(/localhost:3001|127\.0\.0\.1:3001/, { timeout: 30000 });
}

test.describe("Gateway verification", () => {
  test("logged-out shell does not leak sidebar chats or right panel", async ({ page }) => {
    await page.goto("/login?logged_out=1");
    await expect(page.getByRole("button", { name: /continue with sso/i })).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/api key/i)).toHaveCount(0);
    await expect(page.locator("aside")).toHaveCount(0);
    await expect(page.getByText("No chats.")).toHaveCount(0);
    await expect(page.getByText("Could not load agents.")).toHaveCount(0);
    await expect(page.getByText("Agents, tool timeline, documents, safety and approvals")).toHaveCount(0);
  });

  test("loads app and shows Hydrogenuine", async ({ page }) => {
    await login(page);
    await page.goto("/");
    await expect(
      page.getByText("Hydrogenuine").or(page.getByRole("button", { name: /continue with sso/i })).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("can open chat and see composer or key-required", async ({ page }) => {
    await login(page);
    await page.goto("/");
    await page.waitForTimeout(2000);
    const composer = page.locator("textarea, [contenteditable=true], input[type=text]").first();
    const keyRequired = page.getByText(/key required/i);
    const approvalsLink = page.getByRole("link", { name: /approvals/i });
    await expect(composer.or(keyRequired).or(approvalsLink).first()).toBeVisible({ timeout: 10000 });
  });

  test("approvals page loads", async ({ page }) => {
    await login(page);
    await page.goto("/approvals");
    await expect(page).toHaveURL(/\/(approvals|login)/, { timeout: 5000 });
    if (page.url().includes("/login")) {
      await expect(page.getByRole("button", { name: /continue with sso/i }).or(page.getByText("Approvals")).first()).toBeVisible({ timeout: 5000 });
    } else {
      await expect(page.getByText("Approvals").first()).toBeVisible({ timeout: 10000 });
    }
  });

  test("invalid chat route keeps session and shows calm empty agent state", async ({ page }) => {
    await login(page);
    await page.goto("/chat/not-a-real-chat");
    await expect(page).toHaveURL(/\/chat\/not-a-real-chat/, { timeout: 10000 });
    await expect(page.getByRole("button", { name: "Toggle details" })).toBeEnabled({ timeout: 10000 });
    await page.getByRole("button", { name: "Toggle details" }).click();
    await expect(page.getByText("Details")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Could not load agents.")).toHaveCount(0);
    await expect(page.getByText("No agents reported.")).toBeVisible({ timeout: 10000 });
  });
});
