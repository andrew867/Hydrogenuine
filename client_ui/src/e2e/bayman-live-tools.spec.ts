import { test, expect } from "@playwright/test";
import fs from "fs";
import path from "path";
import { loginWithOidc } from "./support/oidc";

const apiBase = process.env.PLAYWRIGHT_HG_API_BASE || process.env.NEXT_PUBLIC_HG_API_BASE || "http://localhost:8080";

async function login(page: import("@playwright/test").Page) {
  await loginWithOidc(page);
}

function proofDir(): string {
  const repoRoot = path.resolve(process.cwd(), "..");
  return path.join(repoRoot, "docs", "proofs", "out", "20260306_bayman_live_tools");
}

async function createBaymanChat(request: import("@playwright/test").APIRequestContext): Promise<string> {
  const headers = {
    "Content-Type": "application/json",
  };
  const personasResponse = await request.get(`${apiBase}/api/v1/personas`, { headers });
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
    headers,
    data: {
      title: "Bayman live tools",
      fingerprint_id: bayman.fingerprint_id,
      ...(skinId ? { skin_id: skinId } : {}),
    },
  });
  expect(createResponse.ok()).toBeTruthy();
  const createPayload = await createResponse.json();
  expect(createPayload?.chat_id).toBeTruthy();
  return String(createPayload.chat_id);
}

test.describe("Bayman live tools", () => {
  test("new chat uses live weather and fetched VOCM headlines", async ({ page, request }) => {
    test.setTimeout(240000);
    const root = proofDir();
    const screenshotDir = path.join(root, "artifacts", "screenshots", "desktop");
    fs.mkdirSync(screenshotDir, { recursive: true });
    const shot = async (name: string) => {
      await page.screenshot({ path: path.join(screenshotDir, name), fullPage: true });
    };

    await login(page);
    const chatId = await createBaymanChat(page.request);
    await page.goto(`/chat/${encodeURIComponent(chatId)}`);
    await expect(page).toHaveURL(new RegExp(`/chat/${chatId}$`), { timeout: 30000 });

    const composer = page.getByPlaceholder("Message HG…");
    await expect(composer).toBeVisible({ timeout: 15000 });
    const sendButton = page.getByRole("button", { name: "Send" }).first();
    const streamingCursor = page.locator(".animate-pulse");

    await composer.fill("How is the weather today around town? Give it in your own words.");
    await sendButton.click();
    await expect(page.getByText(/Sending your message|Sending…|Sent|Agent responding/i).first()).toBeVisible({ timeout: 15000 });
    await expect(streamingCursor).toHaveCount(0, { timeout: 120000 });
    const weatherReply = page.locator("div.prose").last();
    await expect(weatherReply).toBeVisible({ timeout: 120000 });
    await expect(weatherReply).toContainText(/\S+/, { timeout: 120000 });
    await shot("01-bayman-live-weather.png");

    const newsChatId = await createBaymanChat(page.request);
    await page.goto(`/chat/${encodeURIComponent(newsChatId)}`);
    await expect(page).toHaveURL(new RegExp(`/chat/${newsChatId}$`), { timeout: 30000 });

    const newsComposer = page.getByPlaceholder("Message HG…");
    await expect(newsComposer).toBeVisible({ timeout: 15000 });
    const newsSendButton = page.getByRole("button", { name: "Send" }).first();
    await newsComposer.fill("Can you search online and find me the top VOCM news stories of the week?");
    await expect(newsSendButton).toBeEnabled({ timeout: 120000 });
    await newsSendButton.click();
    await expect(streamingCursor).toHaveCount(0, { timeout: 120000 });
    const newsReply = page.locator("div.prose").last();
    await expect(newsReply).toBeVisible({ timeout: 120000 });
    await expect(newsReply).toContainText(/\S+/, { timeout: 120000 });
    const sourceCards = page.locator('a[href*="vocm.com"]');
    await expect(sourceCards.first()).toBeVisible({ timeout: 120000 });
    await expect(page.getByText("Sources").last()).toBeVisible({ timeout: 30000 });
    await shot("02-bayman-live-news.png");

    const weatherText = ((await weatherReply.textContent()) || "").trim();
    const newsText = ((await newsReply.textContent()) || "").trim();
    const sourceUrls = await sourceCards.evaluateAll((links) =>
      links.map((link) => (link as HTMLAnchorElement).href).filter(Boolean)
    );
    const summary = {
      weather_prompt: "How is the weather today around town? Give it in your own words.",
      weather_reply: weatherText,
      news_prompt: "Can you search online and find me the top VOCM news stories of the week?",
      news_reply: newsText,
      source_urls: sourceUrls,
      screenshots: [
        "artifacts/screenshots/desktop/01-bayman-live-weather.png",
        "artifacts/screenshots/desktop/02-bayman-live-news.png",
      ],
    };
    fs.writeFileSync(path.join(root, "summary.json"), JSON.stringify(summary, null, 2), "utf8");

    expect(weatherText.length).toBeGreaterThan(40);
    expect(newsText.length).toBeGreaterThan(40);
    expect(sourceUrls.some((url) => url.includes("vocm.com"))).toBeTruthy();
  });
});
