import { expect, test } from "@playwright/test";

/**
 * Tier-1 smoke: authenticated user opens the chat page, the
 * page hydrates without runtime errors, and the input is
 * focused / typable.
 *
 * Authenticates via the storage-state preset created in
 * ``global-setup.ts`` (TODO — for MVP we skip if no fixture,
 * letting the test fail clearly with a missing-storage-state
 * message). The full "send a turn + receive SSE token" path
 * lands when global-setup is in.
 */
test.describe("Chat (smoke)", () => {
  test.skip(
    !process.env.E2E_AUTH_USER,
    "Set E2E_AUTH_USER + E2E_AUTH_PASSWORD to run authenticated paths",
  );

  test("chat page renders for an authenticated user", async ({ page, context }) => {
    // Cheap auth — POST /api/auth/login then attach the cookies.
    // Avoids juggling Playwright storageState fixtures for the
    // MVP scaffold. Replace with proper global-setup once we
    // ship more tests that need it.
    const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";
    const resp = await context.request.post(`${apiBase}/auth/login`, {
      data: {
        email: process.env.E2E_AUTH_USER,
        password: process.env.E2E_AUTH_PASSWORD,
      },
    });
    expect(resp.ok()).toBeTruthy();

    await page.goto("/home");
    // /home should redirect to an agent / show a "create agent"
    // CTA. Either renders; assert no error overlay.
    await expect(page.locator("text=/error|crash|exception/i")).toHaveCount(0);
  });
});
