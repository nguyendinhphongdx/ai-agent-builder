import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config for AgentForge E2E (P3.4 MVP).
 *
 * Three projects (Chromium / Firefox / WebKit) so we catch
 * vendor-specific bugs early. CI runs them in parallel; locally
 * `pnpm e2e` defaults to Chromium for speed (filter via
 * `--project=chromium`).
 *
 * webServer block boots `next dev` so devs don't have to start
 * the FE manually. Backend must already be reachable at
 * NEXT_PUBLIC_API_URL — we assume a local stack via
 * `docker compose up` or equivalent.
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? "github" : "html",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
    video: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "firefox", use: { ...devices["Desktop Firefox"] } },
    { name: "webkit", use: { ...devices["Desktop Safari"] } },
  ],
  webServer: process.env.CI
    ? undefined
    : {
        command: "pnpm dev",
        url: "http://localhost:3000",
        reuseExistingServer: true,
        timeout: 120_000,
      },
});
