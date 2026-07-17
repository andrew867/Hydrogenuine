import { test, expect } from "@playwright/test";
import { loginWithOidc } from "./support/oidc";
const apiBase = process.env.E2E_API_BASE || "http://localhost:8080";
const operatorKey = process.env.E2E_OPERATOR_KEY || "demo-api-key";

async function login(page: import("@playwright/test").Page) {
  await loginWithOidc(page);
}

async function api<T>(request: import("@playwright/test").APIRequestContext, route: string, init?: { method?: string; data?: unknown }) {
  const response =
    init?.method && init.method !== "GET"
      ? await request.fetch(`${apiBase}${route}`, {
          method: init.method,
          data: init.data,
          headers: { "X-API-Key": operatorKey, Authorization: `Bearer ${operatorKey}` },
        })
      : await request.get(`${apiBase}${route}`, {
          headers: { "X-API-Key": operatorKey, Authorization: `Bearer ${operatorKey}` },
        });
  expect(response.ok(), `API ${route} should succeed`).toBeTruthy();
  if (response.status() === 204) return undefined as T;
  return (await response.json()) as T;
}

test.describe("Swarm workspace UX", () => {
  test("drilldown preserves returnUrl across swarm and chat", async ({ page, request }) => {
    test.setTimeout(180000);

    await login(page);
    const run = await api<{ chat_ids: string[]; swarm_run_id?: string }>(request, "/v1/swarm/run", {
      method: "POST",
      data: {
        task: "Inspect this drilldown flow without losing return context.",
        count: 2,
        fingerprint_id: "nikola_tesla",
      },
    });
    expect(run.chat_ids?.length ?? 0).toBeGreaterThan(0);
    expect(run.swarm_run_id).toBeTruthy();
    const chatId = run.chat_ids[0];
    const swarmRunId = run.swarm_run_id!;
    await expect.poll(async () => {
      const workspace = await api<{ members?: Array<unknown>; counts?: { active?: number; queued?: number; completed?: number; error?: number } }>(
        request,
        `/v1/swarms/${encodeURIComponent(swarmRunId)}`
      );
      return (workspace.members?.length ?? 0) + (workspace.counts?.active ?? 0) + (workspace.counts?.queued ?? 0);
    }, { timeout: 120000 }).toBeGreaterThan(0);
    await page.goto(`/swarm/${encodeURIComponent(swarmRunId)}?returnUrl=${encodeURIComponent(`/chat/${chatId}`)}`);
    await expect(page.getByText("Participants").first()).toBeVisible({ timeout: 15000 });
    await expect(page.getByRole("link", { name: "Back to origin" })).toHaveAttribute("href", `/chat/${chatId}`);
    await page.goto(`/chat/${encodeURIComponent(chatId)}?returnUrl=${encodeURIComponent(`/swarm/${swarmRunId}`)}`);
    await expect(page.getByRole("link", { name: "Back to origin" })).toHaveAttribute("href", `/swarm/${swarmRunId}`);
  });
});
