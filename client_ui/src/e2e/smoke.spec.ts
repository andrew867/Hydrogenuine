import { test, expect } from "@playwright/test";

test("loads app shell", async ({ page }) => {
  await page.goto("/");
  // App shows either Hydrogenuine (logged-in shell) or the SSO login form
  await expect(
    page.getByText("Hydrogenuine").or(page.getByRole("button", { name: /continue with sso/i })).or(page.getByRole("button", { name: /log in/i })).first()
  ).toBeVisible({ timeout: 10000 });
});
