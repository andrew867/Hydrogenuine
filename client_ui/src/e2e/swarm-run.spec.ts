/**
 * E2E: Swarm run UI and weather job.
 * Requires gateway at NEXT_PUBLIC_HG_API_BASE with personas. Run: npx playwright test swarm-run
 */
import { test, expect } from "@playwright/test";
import { loginWithOidc } from "./support/oidc";

async function ensureLoggedIn(page: import("@playwright/test").Page) {
  await loginWithOidc(page);
  // Shell loaded: brand name, composer, sidebar link, or Run swarm button
  await expect(
    page
      .getByText("Hydrogenuine")
      .or(page.getByPlaceholder(/message hg/i))
      .or(page.locator("aside").getByRole("link", { name: /chat|swarm/i }))
      .or(page.getByRole("button", { name: /run swarm/i }))
      .first()
  ).toBeVisible({ timeout: 15000 });
}

test.describe("Swarm run", () => {
  test("opens swarm modal from sidebar", async ({ page }) => {
    test.setTimeout(120000);
    await ensureLoggedIn(page);
    const swarmBtn = page.getByRole("button", { name: /run swarm/i });
    await swarmBtn.first().click();
    await expect(page.getByRole("heading", { name: /run swarm/i })).toBeVisible();
    await expect(page.getByText("Single brief")).toBeVisible();
    await expect(page.getByText("One brief per agent")).toBeVisible();
    await expect(page.getByText("Weather job (10 provinces)")).toBeVisible();
  });

  test("weather preset fills 10 province tasks", async ({ page }) => {
    test.setTimeout(120000);
    await ensureLoggedIn(page);
    await page.getByRole("button", { name: /run swarm/i }).first().click();
    await expect(page.getByRole("heading", { name: /run swarm/i })).toBeVisible();
    await page.getByText("Weather job (10 provinces)").click();
    // Preset fills the tasks field; wait for province names to appear
    await expect(page.getByText("Ontario").first()).toBeVisible({ timeout: 8000 });
    await expect(page.getByText("Quebec").first()).toBeVisible({ timeout: 2000 });
    const textarea = page.locator("#swarm-tasks-input").or(page.getByPlaceholder(/Task 1/));
    await expect(textarea.first()).toContainText("Ontario");
  });

  test("submit shows result or error", async ({ page }) => {
    test.setTimeout(180000);
    await ensureLoggedIn(page);
    await page.getByRole("button", { name: /run swarm/i }).first().click();
    await expect(page.getByRole("heading", { name: /run swarm/i })).toBeVisible();
    await page.getByPlaceholder(/e\.g\. Research the top local stories/i).fill("Hello");
    await page.locator("form").getByRole("button", { name: /run swarm|running/i }).click();
    // Wait for run to finish: success, error, or approval message.
    const created = page.getByText(/Created \d+ chat(\(s\))?/);
    const error = page.getByText(/failed|error|Swarm run|network|timeout/i);
    const approval = page.getByText(/approval.*pending/i);
    await expect
      .poll(
        async () => {
          for (const locator of [created, error, approval]) {
            if (await locator.first().isVisible().catch(() => false)) {
              return true;
            }
          }
          return false;
        },
      { timeout: 120000 }
      )
      .toBe(true);
  });

  test("swarm detail shows aggregate status without opening every chat", async ({ page }) => {
    test.setTimeout(180000);
    await ensureLoggedIn(page);
    await page.getByRole("button", { name: /run swarm/i }).first().click();
    await expect(page.getByRole("heading", { name: /run swarm/i })).toBeVisible();
    await page.getByText("Weather job (10 provinces)").click();
    await page.locator("form").getByRole("button", { name: /run swarm|running/i }).click();

    const created = page.getByText(/Created \d+ chat\(s\)/i);
    const approval = page.getByText(/approval.*pending/i);
    const error = page.getByText(/failed|error|Swarm run|network|timeout/i);
    await expect
      .poll(
        async () => {
          for (const locator of [created, approval, error]) {
            if (await locator.first().isVisible().catch(() => false)) {
              return true;
            }
          }
          return false;
        },
        { timeout: 120000 }
      )
      .toBe(true);
    const swarmOverviewLink = page.getByRole("link", { name: /open swarm overview/i });
    await expect(swarmOverviewLink).toBeVisible({ timeout: 15000 });
    await swarmOverviewLink.click();
    await expect(page.getByText("Participants").first()).toBeVisible({ timeout: 15000 });
  });
});
