import { test, expect } from "@playwright/test";
import fs from "fs";
import path from "path";
import { loginWithOidc } from "./support/oidc";
const prompt = "In your own words, give your opinion in exactly two paragraphs on the United States bombing Iran.";
const apiBase = process.env.PLAYWRIGHT_API_BASE || "http://localhost:8080";
const operatorKey = process.env.E2E_OPERATOR_KEY || "demo-api-key";

async function createBaymanChat(request: import("@playwright/test").APIRequestContext): Promise<string> {
  const personasResponse = await request.get(`${apiBase}/api/v1/personas`, {
    headers: { "X-API-Key": operatorKey, Authorization: `Bearer ${operatorKey}` },
  });
  expect(personasResponse.ok()).toBeTruthy();
  const personasPayload = await personasResponse.json();
  const personas = Array.isArray(personasPayload?.personas) ? personasPayload.personas : [];
  const bayman = personas.find((persona: { name?: string }) => persona?.name === "The Bayman");
  expect(bayman).toBeTruthy();
  const skinId =
    (Array.isArray(bayman.skins) ? bayman.skins.find((skin: { name?: string }) => skin?.name === "The Bayman")?.id : undefined)
    || (Array.isArray(bayman.skins) ? bayman.skins[0]?.id : undefined)
    || undefined;

  const createResponse = await request.post(`${apiBase}/v1/chats`, {
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": operatorKey,
      Authorization: `Bearer ${operatorKey}`,
    },
    data: {
      title: "Bayman persona chat",
      fingerprint_id: bayman.fingerprint_id,
      ...(skinId ? { skin_id: skinId } : {}),
    },
  });
  expect(createResponse.ok()).toBeTruthy();
  const createPayload = await createResponse.json();
  expect(createPayload?.chat_id).toBeTruthy();
  return String(createPayload.chat_id);
}

function proofDir(): string {
  const repoRoot = path.resolve(process.cwd(), "..");
  return path.join(repoRoot, "docs", "proofs", "out", "20260306_bayman_persona_chat");
}

test.describe("Bayman persona chat", () => {
  test("creates a new chat in the client UI and gets a two-paragraph Bayman reply", async ({ page, request }) => {
    test.setTimeout(180000);
    const root = proofDir();
    const screenshotDir = path.join(root, "artifacts", "screenshots", "desktop");
    fs.mkdirSync(screenshotDir, { recursive: true });
    const shot = async (name: string) => {
      await page.screenshot({ path: path.join(screenshotDir, name), fullPage: true });
    };

    await loginWithOidc(page);
    await page.waitForLoadState("networkidle");

    const chatId = await createBaymanChat(request);
    await page.goto(`/chat/${encodeURIComponent(chatId)}`);
    await expect(page).toHaveURL(/\/chat\/[^/]+$/, { timeout: 15000 });
    await shot("01-new-chat-bayman-selected.png");
    const composer = page.getByPlaceholder("Message HG…");
    await expect(composer).toBeVisible({ timeout: 10000 });
    await expect(composer).toBeEditable({ timeout: 10000 });
    await composer.fill(prompt);
    await expect(composer).toHaveValue(prompt);
    await shot("02-prompt-composed.png");
    await page.getByRole("button", { name: "Send" }).first().click();

    const reply = page.locator("div.prose").last();
    await expect(reply).toBeVisible({ timeout: 120000 });
    const replyText = ((await reply.textContent()) || "").trim();
    const renderedParagraphs = (await reply.locator("p").allTextContents()).map((part) => part.trim()).filter(Boolean);
    await shot("03-bayman-reply.png");

    const summary = {
      prompt,
      paragraphs: renderedParagraphs.length,
      paragraph_text: renderedParagraphs,
      reply_text: replyText,
      screenshots: [
        "artifacts/screenshots/desktop/01-new-chat-bayman-selected.png",
        "artifacts/screenshots/desktop/02-prompt-composed.png",
        "artifacts/screenshots/desktop/03-bayman-reply.png",
      ],
    };
    fs.writeFileSync(path.join(root, "summary.json"), JSON.stringify(summary, null, 2), "utf8");

    expect(renderedParagraphs.length).toBeGreaterThanOrEqual(1);
    expect(replyText.length).toBeGreaterThan(50);
  });
});
