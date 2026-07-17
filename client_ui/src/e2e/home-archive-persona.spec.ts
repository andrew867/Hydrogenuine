import { test, expect } from "@playwright/test";
import { loginWithOidc } from "./support/oidc";

test.describe("Home, persona modal, and archive flow", () => {
  test.setTimeout(120000);

  test("home shows welcome shell, persona modal loads, and archived chats can be restored", async ({ page }) => {
    await loginWithOidc(page);

    await page.goto("/");
    await expect(page.getByText("Hydrogenuine workspace")).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("One place to chat, fan out work, review proofs, and steer the run.")).toBeVisible({ timeout: 15000 });

    await page.locator("aside").getByRole("button", { name: /new chat/i }).first().click();
    const modal = page.locator("div.fixed.inset-0").filter({ has: page.getByText("New chat", { exact: true }) });
    await expect(modal).toBeVisible({ timeout: 10000 });
    await expect(modal.locator("#new-chat-persona")).toContainText("The Bayman", { timeout: 30000 });
    await expect(modal.locator("#new-chat-persona")).toContainText("Custom", { timeout: 30000 });

    await modal.getByRole("button", { name: "Close" }).click();

    const recentWork = page.getByText("Recent work").locator("xpath=..");
    const firstRecentChat = recentWork.getByRole("button").first();
    await expect(firstRecentChat).toBeVisible({ timeout: 15000 });
    await firstRecentChat.click();
    await expect(page).toHaveURL(/\/chat\//, { timeout: 15000 });
    const chatUrl = page.url();

    await page.locator("aside").getByRole("button", { name: /^Archive / }).first().click();
    await expect(page).toHaveURL(/\/$/, { timeout: 15000 });

    await page.goto("/settings");
    await expect(page.getByText("Archived chats & swarms")).toBeVisible({ timeout: 15000 });
    await page.getByRole("button", { name: "Open archive" }).click();
    const archivedCard = page.locator("div.rounded-2xl.border.border-border\\/70.bg-bg\\/40.p-3").filter({ hasText: /Archive test chat/ }).first();
    await expect(archivedCard).toBeVisible({ timeout: 15000 });
    await archivedCard.getByRole("button", { name: "Restore" }).click();

    await page.goto(chatUrl);
    await expect(page.getByText(/Archive test chat/).first()).toBeVisible({ timeout: 15000 });
  });

  test("home selection does not trap later page and chat navigation", async ({ page }) => {
    await loginWithOidc(page);

    await page.goto("/");
    const recentWork = page.getByText("Recent work").locator("xpath=..");
    const firstRecentChat = recentWork.getByRole("button").first();
    await expect(firstRecentChat).toBeVisible({ timeout: 15000 });
    await firstRecentChat.click();
    await expect(page).toHaveURL(/\/chat\//, { timeout: 15000 });
    const openedChatUrl = page.url();

    await page.locator("aside").getByRole("link", { name: "Approvals" }).first().click();
    await expect(page).toHaveURL(/\/approvals$/, { timeout: 15000 });
    await page.goto(openedChatUrl);
    await expect(page).toHaveURL(/\/chat\//, { timeout: 15000 });
  });
});
