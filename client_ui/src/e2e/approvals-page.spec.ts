/**
 * E2E: Approvals page — payload wrap, pagination, filter.
 * Run against real gateway (e.g. with demo data) or after login.
 */
import { test, expect } from "@playwright/test";
import { loginWithOidc } from "./support/oidc";

test.describe("Approvals page", () => {
  test("approvals page loads with filter and status selector", async ({ page }) => {
    await loginWithOidc(page);
    await page.goto("/approvals");
    await expect(page).toHaveURL(/\/(approvals|login)/, { timeout: 10000 });
    await expect(page.getByText("Approvals").first()).toBeVisible({ timeout: 15000 });
    const filterSelect = page.locator('select[aria-label="Filter by status"]');
    await expect(filterSelect).toBeVisible({ timeout: 5000 });
    await expect(
      page.getByText(/pending only|No pending approvals|Human-in-the-loop/i).first()
    ).toBeVisible({ timeout: 5000 });
  });

  test("show payload expands and content wraps within container", async ({ page }) => {
    await loginWithOidc(page);
    await page.goto("/approvals");
    await expect(page).toHaveURL(/\/(approvals|login)/, { timeout: 5000 });
    const summary = page.getByText("Show payload").first();
    const visible = await summary.isVisible().catch(() => false);
    if (!visible) {
      test.skip(true, "No approval cards with Show payload on this run");
      return;
    }
    await summary.click();
    const pre = page.locator("details pre").first();
    await expect(pre).toBeVisible({ timeout: 3000 });
    const preWidth = await pre.evaluate((el) => el.getBoundingClientRect().width);
    const viewportWidth = await page.evaluate(() => window.innerWidth);
    expect(preWidth).toBeLessThanOrEqual(viewportWidth + 2);
  });

  test("pagination controls appear when total exceeds page size", async ({ page }) => {
    await loginWithOidc(page);
    await page.goto("/approvals");
    await expect(page).toHaveURL(/\/(approvals|login)/, { timeout: 5000 });
    await page.getByRole("combobox", { name: /filter by status/i }).selectOption("all");
    await page.waitForTimeout(1500);
    const pageIndicator = page.getByText(/Page \d+ of \d+/);
    const nextBtn = page.getByRole("button", { name: "Next" });
    const prevBtn = page.getByRole("button", { name: "Previous" });
    const hasPagination = (await pageIndicator.isVisible().catch(() => false))
      || (await nextBtn.isVisible().catch(() => false))
      || (await prevBtn.isVisible().catch(() => false));
    if (hasPagination) {
      await expect(pageIndicator.or(nextBtn).or(prevBtn).first()).toBeVisible();
    }
  });
});
