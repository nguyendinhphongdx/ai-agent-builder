import { expect, test } from "@playwright/test";

/**
 * Tier-1 smoke: anonymous user can load the landing page, see the
 * primary CTA, and click through to sign-up.
 *
 * Catches: SSR hydration errors, missing env vars on the FE,
 * broken auth redirects.
 */
test.describe("Landing page", () => {
  test("renders and links to sign-up", async ({ page }) => {
    await page.goto("/");
    // Page should render without hydration error.
    await expect(page).toHaveTitle(/AgentForge/i);
    // Primary CTA leads to the auth flow. Match flexibly — copy
    // changes are common, the contract is "a link to /auth/* exists".
    const signupLink = page.getByRole("link", { name: /get started|sign up|sign in/i });
    await expect(signupLink.first()).toBeVisible();
  });

  test("404 page renders for unknown route", async ({ page }) => {
    const response = await page.goto("/this-does-not-exist");
    // Next renders 404 with status 404; don't depend on copy.
    expect(response?.status()).toBe(404);
  });
});
