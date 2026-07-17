/**
 * E2E: Run weather swarm job from client UI and capture screenshots of entities (10 tasks) in parallel.
 * Saves to proof bundle artifacts/screenshots when SWARM_WEATHER_PROOF_DIR is set (path relative to repo root).
 * Requires: gateway + API running, client UI. Run from client_ui:
 *   SWARM_WEATHER_PROOF_DIR=docs/proofs/out/YYYYMMDD_HHMMSS_swarm_weather_10_real npm run e2e -- swarm-weather-screenshots
 */
import path from "path";
import fs from "fs";
import { test, expect } from "@playwright/test";
import { loginWithOidc } from "./support/oidc";

const REPO_ROOT = path.resolve(process.cwd(), "..");
const adminKey = process.env.E2E_ADMIN_KEY || "demo-admin-key";
const operatorKey = process.env.E2E_OPERATOR_KEY || "demo-api-key";
const apiBase = process.env.PLAYWRIGHT_API_BASE || "http://localhost:8080";
const seededChatId = process.env.PLAYWRIGHT_CHAT_ID || "";
const seededChatTitle = process.env.PLAYWRIGHT_CHAT_TITLE || "";
const proofDir = process.env.SWARM_WEATHER_PROOF_DIR
  ? path.join(REPO_ROOT, process.env.SWARM_WEATHER_PROOF_DIR)
  : null;
const desktopDir = proofDir ? path.join(proofDir, "artifacts", "screenshots", "desktop") : null;
const mobileDir = proofDir ? path.join(proofDir, "artifacts", "screenshots", "mobile") : null;

async function ensureLoggedIn(page: any) {
  await loginWithOidc(page);
}

test.describe("Swarm weather proof screenshots", () => {
  test("persona chat auto-swarm weather summary @ desktop", async ({ page }) => {
    if (!desktopDir) {
      test.skip(true, "SWARM_WEATHER_PROOF_DIR not set");
      return;
    }
    fs.mkdirSync(desktopDir, { recursive: true });

    await fetch(`${apiBase}/v1/tenants/me/settings`, {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${adminKey}`,
        "X-API-Key": adminKey,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ first_turn_approval_required: false }),
    });

    const chatTitle = seededChatTitle || `Tesla weather proof ${Date.now()}`;
    const prompt = "Tesla, have five agents check the weather in British Columbia, Alberta, Saskatchewan, Manitoba, and Ontario in their own words, then summarize the differences here.";
    const createRes = await fetch(`${apiBase}/v1/chats`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${operatorKey}`,
        "X-API-Key": operatorKey,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ title: chatTitle, fingerprint_id: "nikola_tesla" }),
    });
    expect(createRes.ok).toBeTruthy();
    const createBody = await createRes.json();
    const createdChatId = createBody.chat_id as string;
    expect(createdChatId).toBeTruthy();
    const sendRes = await fetch(`${apiBase}/v1/chats/${createdChatId}/messages`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${operatorKey}`,
        "X-API-Key": operatorKey,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ content: prompt }),
    });
    expect(sendRes.ok).toBeTruthy();

    await ensureLoggedIn(page);
    await expect(page.locator("aside").getByRole("link", { name: new RegExp(chatTitle, "i") }).first()).toBeVisible({ timeout: 20000 });
    await page.locator("aside").getByRole("link", { name: new RegExp(chatTitle, "i") }).first().click();
    await expect(page).toHaveURL(new RegExp(`/chat/${createdChatId}`), { timeout: 15000 });
    await page.screenshot({
      path: path.join(desktopDir, "swarm-weather-00-persona-chat-created.png"),
    });
    await page.screenshot({
      path: path.join(desktopDir, "swarm-weather-01-prompt-composed.png"),
    });

    const toolCard = page.getByText(/Spawned 5 weather agents|swarm.run/i).first();
    await expect(toolCard).toBeVisible({ timeout: 60000 });
    await page.screenshot({
      path: path.join(desktopDir, "swarm-weather-03-parent-swarm-tool-card.png"),
    });

    await expect(page.getByText(/British Columbia|Alberta|Saskatchewan|Manitoba|Ontario/).last()).toBeVisible({ timeout: 120000 });
    await page.screenshot({
      path: path.join(desktopDir, "swarm-weather-04-parent-summary.png"),
    });
  });

  test("weather job: tasks filled and run result @ desktop", async ({ page }) => {
    if (!desktopDir) {
      test.skip(true, "SWARM_WEATHER_PROOF_DIR not set");
      return;
    }
    fs.mkdirSync(desktopDir, { recursive: true });

    await page.goto("/");
    await expect(page.getByText("Hydrogenuine")).toBeVisible({ timeout: 10000 });
    await page.getByRole("button", { name: /run swarm/i }).click();
    await expect(page.getByRole("heading", { name: /run swarm/i })).toBeVisible();

    await page.getByText("Weather job (10 provinces)").click();
    const textarea = page.locator("form textarea").last();
    await expect(textarea).toContainText("Ontario", { timeout: 5000 });
    await expect(textarea).toContainText("Quebec");

    await page.screenshot({
      path: path.join(desktopDir, "swarm-weather-01-tasks-filled.png"),
    });

    await page.locator("form").getByRole("button", { name: /run swarm|running/i }).click();
    const created = page.getByText(/Created \d+ chat/);
    const error = page.getByText(/failed|error/i);
    await expect(created.or(error)).toBeVisible({ timeout: 60000 });

    await page.screenshot({
      path: path.join(desktopDir, "swarm-weather-02-result.png"),
    });
  });

  test("weather job: tasks filled and run result @ mobile", async ({ page }) => {
    if (!mobileDir) {
      test.skip(true, "SWARM_WEATHER_PROOF_DIR not set");
      return;
    }
    fs.mkdirSync(mobileDir, { recursive: true });

    await page.goto("/");
    await expect(page.getByText("Hydrogenuine")).toBeVisible({ timeout: 10000 });
    await page.getByRole("button", { name: /run swarm/i }).click();
    await expect(page.getByRole("heading", { name: /run swarm/i })).toBeVisible();

    await page.getByText("Weather job (10 provinces)").click();
    const textarea = page.locator("form textarea").last();
    await expect(textarea).toContainText("Ontario", { timeout: 5000 });

    await page.screenshot({
      path: path.join(mobileDir, "swarm-weather-01-tasks-filled.png"),
    });

    await page.locator("form").getByRole("button", { name: /run swarm|running/i }).click();
    const created = page.getByText(/Created \d+ chat/);
    const error = page.getByText(/failed|error/i);
    await expect(created.or(error)).toBeVisible({ timeout: 60000 });

    await page.screenshot({
      path: path.join(mobileDir, "swarm-weather-02-result.png"),
    });
  });
});
