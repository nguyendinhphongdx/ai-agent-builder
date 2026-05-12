# E2E Tests (Playwright)

Lightweight scaffold from P3.4. Three smoke specs:

- `landing.spec.ts` — anonymous landing renders + 404
- `auth.spec.ts` — sign-up form + login rejects bogus
- `chat.spec.ts` — authenticated `/home` (skipped unless
  `E2E_AUTH_USER` + `E2E_AUTH_PASSWORD` are set)

## Run

```bash
pnpm install            # installs @playwright/test
pnpm dlx playwright install --with-deps   # one-time browser binaries
pnpm e2e                # all three browsers
pnpm e2e --project=chromium   # just chromium
pnpm e2e:headed         # see the browser
pnpm e2e:report         # open last HTML report
```

## Stack-up

`playwright.config.ts` boots `pnpm dev` automatically for local
runs (`reuseExistingServer: true` so it skips when the dev
server is already up). In CI the server is started separately.

`baseURL` resolves from `E2E_BASE_URL` env (default
`http://localhost:3000`).

## Adding tests

Land Tier-1 paths first (per roadmap):

1. Signup → email verify → onboarding → first agent
2. Create agent + attach tool + chat with streaming
3. Upload KB → wait processing → query KB
4. Build workflow with 5 nodes → execute → check output
5. Publish template → another user purchases → fork

Tier-2 are nice-to-have (SSO mock, MFA, hub browse, admin ban).
