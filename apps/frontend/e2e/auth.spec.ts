import { expect, test } from "@playwright/test";

/**
 * Tier-1 smoke: signup → verify → first-login redirect.
 *
 * Uses a randomised email per run so we never collide with
 * existing accounts. The backend's mail provider is mocked in
 * the test environment (returns the verification code via
 * /api/internal/last-verification-code or similar) — adapt the
 * code-fetch step once that endpoint exists in test mode.
 *
 * MVP scope: assert the form renders + submits without 5xx.
 * Full end-to-end (real email + verify click) lands when the
 * test mail capture endpoint is in.
 */
test.describe("Auth flow", () => {
  test("sign-up form renders and accepts submit", async ({ page, request }) => {
    await page.goto("/auth/signup");

    const email = `e2e-${Date.now()}@example.com`;
    await page.getByLabel(/email/i).fill(email);
    await page.getByLabel(/password/i, { exact: true }).fill("Sup3rSecret!");
    // Optional fields tolerated — fill if present.
    const nameField = page.getByLabel(/full name|name/i);
    if (await nameField.count()) {
      await nameField.first().fill("E2E Tester");
    }

    const [response] = await Promise.all([
      page.waitForResponse((r) => r.url().includes("/auth/") && r.request().method() === "POST"),
      page.getByRole("button", { name: /sign up|create account|register/i }).click(),
    ]);
    // Don't pin the exact status — providers vary on whether
    // they 200 (verify-email-required) vs 201 vs 302. We just
    // care the backend accepted the payload.
    expect(response.status()).toBeLessThan(500);

    // Cleanup hook — purge the test account so re-runs stay
    // deterministic. Optional; ignored when the endpoint isn't
    // present.
    await request.delete(`/api/internal/test/users/${email}`).catch(() => null);
  });

  test("login form rejects bogus credentials", async ({ page }) => {
    await page.goto("/auth/login");
    await page.getByLabel(/email/i).fill("does-not-exist@example.com");
    await page.getByLabel(/password/i, { exact: true }).fill("nope");
    await page.getByRole("button", { name: /sign in|log in/i }).click();
    // Either an inline error or a redirect back to /auth/login.
    await expect(page).toHaveURL(/auth\/login/, { timeout: 5_000 });
  });
});
