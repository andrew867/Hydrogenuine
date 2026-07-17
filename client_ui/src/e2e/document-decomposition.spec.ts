import fs from "fs";
import path from "path";
import { test, expect } from "@playwright/test";
import { loginWithOidc } from "./support/oidc";

const REPO_ROOT = path.resolve(process.cwd(), "..");
const operatorKey = process.env.E2E_OPERATOR_KEY || "demo-api-key";
const adminKey = process.env.E2E_ADMIN_KEY || "demo-admin-key";
const apiBase = process.env.PLAYWRIGHT_API_BASE || "http://localhost:8080";
const proofDir = process.env.DOC_DECOMP_PROOF_DIR
  ? path.join(REPO_ROOT, process.env.DOC_DECOMP_PROOF_DIR)
  : path.join(REPO_ROOT, "docs", "proofs", "out", "document_decomposition_ui_proof");
const screenshotDir = path.join(proofDir, "artifacts", "screenshots", "desktop");
const fixturePath = path.join(process.cwd(), "src", "e2e", "fixtures", "five_chapters.docx");

async function ensureLoggedIn(page: import("@playwright/test").Page) {
  await loginWithOidc(page);
  await expect(page.getByText("Hydrogenuine").first()).toBeVisible({ timeout: 15000 });
}

test.describe("Document decomposition UI proof", () => {
  test("uploads a five-chapter document and reduces five agent summaries into the parent chat", async ({ page }) => {
    test.setTimeout(420000);
    fs.mkdirSync(screenshotDir, { recursive: true });

    await fetch(`${apiBase}/v1/tenants/me/settings`, {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${adminKey}`,
        "X-API-Key": adminKey,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ first_turn_approval_required: false }),
    });

    await ensureLoggedIn(page);
    const title = `Document fanout ${Date.now()}`;
    const createResponse = await page.request.post(`${apiBase}/v1/chats`, {
      headers: {
        Authorization: `Bearer ${operatorKey}`,
        "X-API-Key": operatorKey,
        "Content-Type": "application/json",
      },
      data: { title, fingerprint_id: "nikola_tesla", skin_id: "nikola_tesla_skin" },
    });
    expect(createResponse.ok()).toBeTruthy();
    const createdPayload = (await createResponse.json()) as { chat_id?: string };
    const createdChatId = String(createdPayload.chat_id || "").trim();
    expect(createdChatId).toBeTruthy();
    await page.goto(`/chat/${encodeURIComponent(createdChatId)}`);
    await expect(page).toHaveURL(new RegExp(`/chat/${createdChatId}`), { timeout: 15000 });
    await page.screenshot({ path: path.join(screenshotDir, "document-decomp-02-chat-created.png") });

    const detailsToggle = page.getByRole("button", { name: "Toggle details" });
    await detailsToggle.click();

    await page.locator('input[type="file"]').setInputFiles(fixturePath);
    await expect(page.getByText(/is attached and parsed/i)).toBeVisible({ timeout: 60000 });
    await expect(page.locator('[title="five_chapters.docx"]').first()).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("parsed").first()).toBeVisible({ timeout: 15000 });
    await page.screenshot({ path: path.join(screenshotDir, "document-decomp-03-document-uploaded.png") });

    const prompt = "Tesla, get five agents to read the five chapters of the attached document and summarize the main differences in one answer here.";
    const composer = page.getByPlaceholder("Message HG…");
    await composer.fill(prompt);
    await page.screenshot({ path: path.join(screenshotDir, "document-decomp-04-prompt-ready.png") });
    await page.getByRole("button", { name: "Send" }).click();
    await expect(page.getByText(/sending/i).first()).toBeVisible({ timeout: 15000 });

    await expect(page.getByText(/spawned 5 document agents/i)).toBeVisible({ timeout: 120000 });
    await page.screenshot({ path: path.join(screenshotDir, "document-decomp-05-fanout-started.png") });
    await page.reload();
    await page.screenshot({ path: path.join(screenshotDir, "document-decomp-06-parent-summary.png") });
  });
});
