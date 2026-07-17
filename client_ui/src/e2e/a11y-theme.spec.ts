import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const ROUTES = ["/login", "/offline", "/system"];

async function applyTheme(page: import("@playwright/test").Page, theme: "light" | "dark") {
  await page.addInitScript((mode) => {
    window.localStorage.setItem("hg-theme-mode", mode);
    document.documentElement.classList.toggle("dark", mode === "dark");
    document.documentElement.setAttribute("data-hg-theme", mode);
  }, theme);
}

for (const theme of ["dark", "light"] as const) {
  test.describe(`a11y (${theme})`, () => {
    for (const route of ROUTES) {
      test(`${route} has no serious/critical axe violations`, async ({ page }) => {
        await applyTheme(page, theme);
        await page.goto(route, { waitUntil: "domcontentloaded" });
        await page.waitForTimeout(500);
        const results = await new AxeBuilder({ page })
          .disableRules(["color-contrast"])
          .analyze();
        const blocking = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
        expect(blocking, JSON.stringify(blocking, null, 2)).toHaveLength(0);
      });
    }
  });
}

test("skip link focuses main content on login shell", async ({ page }) => {
  await page.goto("/login?logged_out=1");
  await page.keyboard.press("Tab");
  const skip = page.getByRole("link", { name: /skip to main content/i });
  await expect(skip).toBeVisible();
  await skip.click();
  await expect(page).toHaveURL(/#main-content$/);
  await expect(page.locator("#main-content")).toBeVisible();
});
