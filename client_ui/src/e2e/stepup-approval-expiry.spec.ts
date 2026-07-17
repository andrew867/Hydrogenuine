import { test, expect } from "@playwright/test";
import { loginWithOidc } from "./support/oidc";
import { execFileSync } from "node:child_process";

const operatorKey = process.env.E2E_OPERATOR_KEY || "demo-api-key";
const gatewayBaseUrl = process.env.PLAYWRIGHT_GATEWAY_BASE_URL || "http://localhost:8080";
const apiBase = process.env.PLAYWRIGHT_API_BASE || "http://localhost:8080";
const fixedSecret = "JBSWY3DPEHPK3PXP";

function currentTotp(secret: string): string {
  return execFileSync("python", ["-c", "import pyotp,sys; print(pyotp.TOTP(sys.argv[1]).now())", secret], {
    encoding: "utf8",
  }).trim();
}

test.describe("Step-up approval expiry", () => {
  test("expired session token re-prompts, verifies, and clears the approval card", async ({ page, request }) => {
    test.setTimeout(180000);

    await loginWithOidc(page);
    await expect(page).toHaveURL(/\/($|chat\/|approvals|settings)/, { timeout: 15000 });

    const authMeResponse = await page.request.get(`${gatewayBaseUrl}/v1/auth/me`);
    expect(authMeResponse.ok()).toBeTruthy();
    const authMe = await authMeResponse.json();
    const principalId = String(authMe?.principal_id || "").trim();
    expect(principalId).toBeTruthy();

    const enrollResponse = await request.post(`${gatewayBaseUrl}/v1/auth/stepup/enroll`, {
      headers: { Authorization: `Bearer ${operatorKey}` },
      data: { user_id: principalId, secret: fixedSecret },
    });
    expect(enrollResponse.ok()).toBeTruthy();

    const createChatResponse = await request.post(`${apiBase}/v1/chats`, {
      headers: {
        Authorization: `Bearer ${operatorKey}`,
        "X-API-Key": operatorKey,
        "Content-Type": "application/json",
      },
      data: {
        title: `Playwright step-up ${Date.now()}`,
        fingerprint_id: "nikola_tesla",
        skin_id: "nikola_tesla_skin",
      },
    });
    expect(createChatResponse.ok()).toBeTruthy();
    const createdChat = (await createChatResponse.json()) as { chat_id?: string };
    const chatId = String(createdChat.chat_id || "").trim();
    expect(chatId).toBeTruthy();

    const approvalTitle = "Approve tool: social.moltbook.create_post";
    const toolInvokeResponse = await request.post(`${apiBase}/v1/chats/${encodeURIComponent(chatId)}/messages`, {
      headers: {
        Authorization: `Bearer ${operatorKey}`,
        "X-API-Key": operatorKey,
        "Content-Type": "application/json",
      },
      data: {
        tool_invoke: {
          tool_name: "social.moltbook.create_post",
          inputs: {
            submolt: "general",
            title: `Playwright step-up ${Date.now()}`,
            content: "Step-up proof content",
          },
        },
      },
    });
    expect(toolInvokeResponse.status()).toBe(202);
    const toolInvokeBody = (await toolInvokeResponse.json()) as { pending_approval_id?: string };
    const pendingApprovalId = String(toolInvokeBody.pending_approval_id || "").trim();
    expect(pendingApprovalId).toBeTruthy();

    await page.evaluate((key) => {
      window.sessionStorage.setItem("hg_operator_key", key);
    }, operatorKey);
    await page.goto("/approvals");
    await page.evaluate(() => {
      window.sessionStorage.setItem("hg_stepup_token", "expired-token");
      window.sessionStorage.setItem("hg_stepup_verified_at", "2020-01-01T00:00:00.000Z");
    });
    await page.reload();

    const approvalCard = page.getByText(approvalTitle, { exact: true }).first();
    await expect(approvalCard).toBeVisible({ timeout: 20000 });
    await approvalCard.click();
    await page.getByRole("button", { name: /^approve$/i }).first().click();

    await expect(page.getByText(/step-up authentication required/i)).toBeVisible({ timeout: 10000 });
    await page.getByPlaceholder("123456").fill(currentTotp(fixedSecret));
    await page.getByRole("button", { name: /approve with step-up/i }).click();

    await expect.poll(
      async () => {
        const approvalsResponse = await page.request.get(`${gatewayBaseUrl}/v1/approvals?status=all`);
        if (!approvalsResponse.ok()) return "";
        const approvals = (await approvalsResponse.json()) as { approvals?: Array<{ id?: string; status?: string }> };
        const item = (approvals.approvals || []).find((entry) => entry.id === pendingApprovalId);
        return item?.status || "";
      },
      { timeout: 30000 }
    ).toBe("approved");

    await page.reload();
    await expect(page.locator("text=" + approvalTitle)).toHaveCount(0, { timeout: 20000 });
  });
});
