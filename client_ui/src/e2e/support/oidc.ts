import { expect } from "@playwright/test";

export type OidcLoginOptions = {
  username?: string;
  password?: string;
  returnUrl?: string;
};

function resolvedValue(value: string | null | undefined, fallback: string): string {
  const trimmed = String(value || "").trim();
  return trimmed || fallback;
}

export async function loginWithOidc(page: import("@playwright/test").Page, options: OidcLoginOptions = {}): Promise<void> {
  const username = resolvedValue(options.username ?? process.env.E2E_OIDC_USER, "demo-operator");
  const password = resolvedValue(options.password ?? process.env.E2E_OIDC_PASSWORD, username);
  const returnUrl = options.returnUrl || "/";

  await page.goto(`/login?logged_out=1&returnUrl=${encodeURIComponent(returnUrl)}`, { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle").catch(() => undefined);
  await page.waitForTimeout(1000);
  await expect(page.getByRole("button", { name: /continue with sso/i })).toBeVisible({ timeout: 15000 });
  await expect(page.getByText(/api key/i)).toHaveCount(0);

  await Promise.all([
    page.waitForURL(/realms\/hg\/protocol\/openid-connect\/auth/, { timeout: 60000 }),
    page.getByRole("button", { name: /continue with sso/i }).click(),
  ]);

  await expect(page.locator('input[name="username"]')).toBeVisible({ timeout: 20000 });
  await page.locator('input[name="username"]').fill(username);
  await page.locator('input[name="password"]').fill(password);

  await Promise.all([
    page.waitForURL(/localhost:(3000|3001|3002|3003)|127\.0\.0\.1:(3000|3001|3002|3003)/, { timeout: 30000 }),
    page.locator("#kc-login").click(),
  ]);

  await expect(page).not.toHaveURL(/\/login(?:\?|$)/, { timeout: 30000 });
}
