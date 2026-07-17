import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL || process.env.PLAYWRIGHT_CLIENT_UI_BASE_URL || "http://localhost:3000";
const port = Number(new URL(baseURL).port || 3000);
const artifactDir = process.env.PLAYWRIGHT_ARTIFACT_DIR;
const useProduction = !!process.env.E2E_USE_PRODUCTION;

// E2E against production: webServer runs "npm run start" (caller must run "npm run build" first).
// Otherwise: dev server for local iteration.
const webServerConfig = {
  command: useProduction ? "npm run start" : "npm run dev",
  port,
  reuseExistingServer: !process.env.CI,
};

export default defineConfig({
  testDir: "./src/e2e",
  timeout: 60_000,
  outputDir: artifactDir ? `${artifactDir}/test-results` : "test-results",
  use: {
    baseURL,
    screenshot: "on",
  },
  webServer: webServerConfig,
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "chromium-light", use: { ...devices["Desktop Chrome"], colorScheme: "light" } },
    { name: "chromium-dark", use: { ...devices["Desktop Chrome"], colorScheme: "dark" } },
    { name: "mobile", use: { ...devices["iPhone 14"] } },
    { name: "mobile-light", use: { ...devices["iPhone 14"], colorScheme: "light" } },
  ]
});
