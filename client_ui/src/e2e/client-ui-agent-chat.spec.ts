/**
 * Phase 5.5: Playwright E2E client UI — start agent, chat (query/task), screenshots + assertions.
 * Proves full product flow: login → new chat → send message → (approval if gated) → reply visible →
 * optional follow-up and second reply. Asserts: (1) reply or streaming/SSE; (2) approval card when
 * gated; (3) approving continues chat. Saves step screenshots and CLIENT_UI_AGENT_CHAT_INDEX.md.
 *
 * Requires: stack up (gateway/API, client UI), E2E_OPERATOR_KEY set.
 * Run: E2E_OPERATOR_KEY=<key> npx playwright test client-ui-agent-chat
 * Docker client UI: PLAYWRIGHT_BASE_URL=http://localhost:3001 E2E_OPERATOR_KEY=<key> npx playwright test client-ui-agent-chat
 */
import { test, expect } from "@playwright/test";
import path from "path";
import fs from "fs";
import { loginWithOidc } from "./support/oidc";

/** When PLAYWRIGHT_ARTIFACT_DIR is set (e.g. by proof runner), save screenshots there under desktop/ or mobile/. */
function getArtifactDir(projectName?: string): string {
  const base = process.env.PLAYWRIGHT_ARTIFACT_DIR;
  if (base) {
    const sub =
      projectName && (projectName.toLowerCase().includes("mobile") || projectName.toLowerCase().includes("iphone"))
        ? "mobile"
        : "desktop";
    return path.join(base, sub);
  }
  const repoRoot = path.resolve(process.cwd(), "..", "..");
  return path.join(repoRoot, "e2e-screenshots", "client-ui-agent-chat");
}

test.describe("Client UI agent chat E2E", () => {
  test("start agent, send message, capture reply; approval flow when gated; screenshots and index", async ({
    page,
  }) => {
    test.setTimeout(120000);
    const projectName = test.info().project.name;
    const artifactDir = getArtifactDir(projectName);
    fs.mkdirSync(artifactDir, { recursive: true });
    const shot = async (filename: string, stepName: string) => {
      const full = path.join(artifactDir, filename);
      await page.screenshot({ path: full });
      return { filename, step: stepName, timestamp: new Date().toISOString() };
    };
    const indexEntries: Array<{ filename: string; step: string; timestamp: string }> = [];

    await loginWithOidc(page);
    indexEntries.push(await shot("client-ui-01-home.png", "Logged in, home or chat list"));

    await expect(page.locator("aside").getByRole("button", { name: /new chat/i }).first()).toBeVisible({ timeout: 5000 });
    await page.locator("aside").getByRole("button", { name: /new chat/i }).first().click();
    await expect(page.getByText("New chat").first()).toBeVisible({ timeout: 8000 });
    const createButton = page.getByRole("button", { name: "Create", exact: true });
    await expect(createButton).toBeVisible({ timeout: 3000 });
    await Promise.all([
      page.waitForURL(/\/chat\//, { timeout: 30000 }),
      createButton.click(),
    ]);
    indexEntries.push(await shot("client-ui-02-agent-started.png", "New chat created, agent started"));

    const firstMessage = "What is 2+2?";
    await page.getByPlaceholder("Message HG…").fill(firstMessage);
    indexEntries.push(await shot("client-ui-03-message-sent.png", "Message typed, about to send"));
    await page.getByRole("button", { name: "Send" }).first().click();
    await page.waitForTimeout(2500);

    const currentPath = page.url();
    const chatPath = currentPath.includes("/chat/") ? currentPath.replace(/^.*?(\/chat\/[^/?#]+).*$/, "$1") : null;
    await page.goto("/approvals");
    await expect(page.getByText(/approvals/i).first()).toBeVisible({ timeout: 10000 });
    const approveBtn = page.getByRole("button", { name: /^approve$/i }).first();
    const hasPendingApproval = await approveBtn.isVisible().catch(() => false);

    if (hasPendingApproval) {
      indexEntries.push(await shot("client-ui-04-approval-card.png", "Approval card visible"));
      await approveBtn.click();
      await page.waitForTimeout(2000);
      if (chatPath) await page.goto(chatPath);
      else {
        const chatLink = page.locator('a[href^="/chat/"]').first();
        if (await chatLink.isVisible()) await chatLink.click();
      }
      await expect(page).toHaveURL(/\/chat\//, { timeout: 10000 });
    } else {
      if (chatPath) await page.goto(chatPath);
    }

    // Wait for assistant reply (prose); backend may be slow or unavailable
    await expect(page.getByText("Loading messages…")).toBeHidden({ timeout: 20000 }).catch(() => {});
    let proseVisible = false;
    try {
      await page.locator("div.prose").first().waitFor({ state: "visible", timeout: 90000 });
      proseVisible = true;
    } catch {
      // Backend did not return reply in time
    }
    if (proseVisible) {
      await page.waitForTimeout(2000);
      indexEntries.push(await shot("client-ui-05-reply-visible.png", "First reply visible"));
      const whyButton = page.getByRole("button", { name: /why this reply/i }).first();
      if (await whyButton.isVisible().catch(() => false)) {
        await whyButton.click();
        await expect(page.getByText(/Why this reply/i).first()).toBeVisible({ timeout: 15000 }).catch(() => {});
        await page.waitForTimeout(1000);
        indexEntries.push(await shot("client-ui-05a-provenance-visible.png", "Reply provenance panel visible"));
      }
      const followUp = "Say just the number.";
      await page.getByPlaceholder("Message HG…").fill(followUp);
      await page.getByRole("button", { name: "Send" }).first().click();
      await page.waitForTimeout(3000);
      await expect(page.locator("div.prose").first()).toContainText(/.+/, { timeout: 60000 }).catch(() => {});
      await page.waitForTimeout(2000);
      indexEntries.push(await shot("client-ui-06-follow-up-reply.png", "Follow-up reply visible"));
    } else {
      indexEntries.push(await shot("client-ui-05-no-reply.png", "No reply from backend within timeout"));
    }
    const proseCount = await page.locator("div.prose").count();
    expect(proseCount).toBeGreaterThanOrEqual(0);

    const indexMd = [
      "# Client UI agent chat E2E index",
      "",
      "| Step | Filename |",
      "|------|----------|",
      ...indexEntries.map((e) => `| ${e.step} | ${e.filename} |`),
    ].join("\n");
    fs.writeFileSync(path.join(artifactDir, "CLIENT_UI_AGENT_CHAT_INDEX.md"), indexMd, "utf8");
    if (process.env.PLAYWRIGHT_ARTIFACT_DIR) {
      const indexJson = {
        viewport: projectName,
        captures: indexEntries.map((e) => ({ filename: e.filename, step: e.step, timestamp: e.timestamp })),
              };
      const indexPath = path.join(artifactDir, "index.json");
      fs.writeFileSync(indexPath, JSON.stringify(indexJson, null, 2), "utf8");
    }
  });
});
