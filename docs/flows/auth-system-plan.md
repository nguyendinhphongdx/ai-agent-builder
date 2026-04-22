---
id: flows-auth-system-plan
title: Auth System — Full BA Spec & Implementation Plan
domain: flows
tags: [auth, plan, register, login, oauth, email-verification, password-reset, specification]
related: [flows-user-registration, api-auth-endpoints, frontend-feature-auth]
summary: End-to-end target design for signup + email verification + login (with remember-me) + password reset + OAuth (GitHub / Google). Status, data model, API contracts, FE routes, security rules, decision points, phased rollout.
status: draft
---

# Auth System — BA Spec & Implementation Plan

> **Purpose.** Lock down the target authentication system before we start
> touching code. This document is the single source of truth for:
> endpoints, schemas, routes, emails, security rules, and the phased
> rollout. Once all decision points are resolved, implementation tasks
> become mechanical.

## 1. Scope

### In-scope
- Sign up (register) with email verification
- Sign in (login) with "remember me"
- Forgot password + reset via email
- Sign in with Google + GitHub (OAuth Authorization Code)
- Sign out (clear cookies)

### Out of scope (future)
- Two-factor auth (2FA / TOTP)
- Account lockout after N failures
- Email change flow
- Magic link / passwordless (can live alongside OAuth later)
- Login attempts audit log
- Linking/unlinking OAuth providers in Settings

## 2. User Stories

| # | Actor | Story |
|---|---|---|
| US-01 | Visitor | Sign up with email + password, receive verification email |
| US-02 | New user | Click link in email → account activated |
| US-03 | Unverified user | Request a fresh verification email (resend) |
| US-04 | Returning user | Log in with email + password |
| US-05 | Returning user | "Remember me" keeps me signed in for 30 days |
| US-06 | Forgetful user | Enter email → receive password reset link |
| US-07 | Forgetful user | Click link → pick new password → sign in |
| US-08 | Any user | Sign out clears cookies and redirects to `/login` |
| US-09 | Visitor | Continue with GitHub — one-click sign up/sign in |
| US-10 | Visitor | Continue with Google — one-click sign up/sign in |

## 3. Data Model Changes

### 3.1 Table `users` — alter

```sql
ALTER TABLE users
  ADD COLUMN is_verified  BOOLEAN      NOT NULL DEFAULT false,
  ADD COLUMN verified_at  TIMESTAMPTZ  NULL,
  ALTER COLUMN hashed_password DROP NOT NULL;
-- hashed_password nullable so pure-OAuth users can exist without a password.
```

### 3.2 Table `auth_tokens` — new

Single table for both purposes keeps migrations flat.

```sql
CREATE TABLE auth_tokens (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash  VARCHAR(64) NOT NULL,                -- SHA-256 hex of plaintext
  purpose     VARCHAR(32) NOT NULL,                -- 'email_verification' | 'password_reset'
  expires_at  TIMESTAMPTZ NOT NULL,
  used_at     TIMESTAMPTZ NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_auth_tokens_hash    ON auth_tokens(token_hash);
CREATE INDEX idx_auth_tokens_user    ON auth_tokens(user_id, purpose);
```

### 3.3 Table `oauth_accounts` — new

Tracks which provider identities belong to which internal user.

```sql
CREATE TABLE oauth_accounts (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  provider          VARCHAR(32)  NOT NULL,   -- 'github' | 'google'
  provider_user_id  VARCHAR(128) NOT NULL,   -- stable ID from provider
  provider_email    VARCHAR(255) NOT NULL,
  access_token      TEXT NULL,               -- only if we later need provider APIs
  refresh_token     TEXT NULL,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE (provider, provider_user_id)
);

CREATE INDEX idx_oauth_accounts_user ON oauth_accounts(user_id);
```

### 3.4 Token storage

Plaintext tokens are **never** persisted. We store `sha256(token)` and
compare hashes on verification. Tokens are one-shot: `used_at` is stamped
on the first successful redemption and the row is permanently dead.

## 4. API Contracts

Every endpoint below is mounted under `${API_PREFIX}/auth`
(`/api/auth/...` in default config).

### 4.1 POST `/auth/register`  — UPDATE existing

```yaml
request:
  email:     string (required, valid email)
  password:  string (required, min 8)
  full_name: string (optional)

response:
  201:
    user: UserResponse    # includes is_verified: false
  409:
    detail: "Email already registered"

side_effects:
  - Create user (is_verified=false)
  - Create auth_token (purpose=email_verification, TTL 24h)
  - Send verification email (fire-and-forget)
  - Set auth cookies (user is logged in, unverified)
```

### 4.2 POST `/auth/login`  — UPDATE existing

```yaml
request:
  email:       string (required)
  password:    string (required)
  remember_me: boolean (optional, default false)

response:
  200:
    user: UserResponse
  401:
    detail: "Invalid email or password"
  403:
    detail: "Account is disabled"

side_effects:
  - Update users.last_login_at
  - Set cookies; refresh_token TTL is 30d if remember_me=true, else 7d.
    The `remember` flag is encoded in the refresh JWT so /auth/refresh
    reissues with the same TTL on every rotation.
```

Unverified users **can log in** — there is no 403 block here; the dashboard
shows a persistent banner until they verify (see FE § 5).

### 4.3 POST `/auth/logout`  — UNCHANGED

Existing implementation clears both cookies. No change.

### 4.4 POST `/auth/refresh`  — UPDATE existing

Reads `remember` flag from the current refresh token's payload and
reissues the new pair with the matching TTL. Behavior unchanged for
clients that never set `remember_me`.

### 4.5 GET `/auth/me`  — UPDATE response only

Adds `is_verified` and `verified_at` fields to `UserResponse`. Existing
consumers ignoring unknown fields are unaffected.

### 4.6 POST `/auth/verify-email/send`  — NEW

```yaml
auth: required (any logged-in user)

request: {}

response:
  200:
    sent: true
  409:
    detail: "Already verified"
  429:
    detail: "Try again in {seconds}s"

side_effects:
  - Mark any prior unused email_verification token as used_at=now
  - Create new token + email
rate_limit: 1 per minute per user
```

### 4.7 POST `/auth/verify-email/confirm`  — NEW

```yaml
auth: not required

request:
  token: string (plaintext from email link)

response:
  200:
    verified: true
  400:
    detail: "Invalid or expired token"

side_effects:
  - users.is_verified = true, users.verified_at = now
  - auth_tokens.used_at = now
```

### 4.8 POST `/auth/forgot-password`  — NEW

```yaml
auth: not required

request:
  email: string

response:
  200:
    sent: true   # ALWAYS — do not reveal whether email exists

side_effects:
  - If user exists: create password_reset token (TTL 30min) + send email
  - If user does not exist: no-op, but still delay ~200ms to avoid
    timing-based enumeration

rate_limit: 3 per hour per email address
```

### 4.9 POST `/auth/reset-password`  — NEW

```yaml
auth: not required

request:
  token:        string
  new_password: string (min 8)

response:
  200:
    ok: true
  400:
    detail: "Invalid or expired token"

side_effects:
  - Update users.hashed_password
  - auth_tokens.used_at = now
  - INVALIDATE ALL refresh tokens for the user (see § 6.4)
```

### 4.10 GET `/auth/oauth/{provider}/start`  — NEW

```yaml
path_params:
  provider: "github" | "google"

query_params:
  redirect_to: string (optional, must be same-origin path)

response:
  302 → provider authorize URL

side_effects:
  - Generate random state + PKCE verifier
  - Store { state, redirect_to, pkce_verifier } in a signed session
    cookie with TTL 5 min, HttpOnly, SameSite=Lax
```

### 4.11 GET `/auth/oauth/{provider}/callback`  — NEW

```yaml
query_params:
  code:  string
  state: string

response:
  302 → FRONTEND_URL + (stored redirect_to)
  302 → /login?error=oauth_failed  (on any failure)

side_effects:
  1. Verify state matches signed cookie; clear cookie
  2. Exchange code → provider access_token (with PKCE verifier)
  3. Fetch provider profile (email, id, name, email_verified)
  4. Account matching (§ 6.3); create or link user
  5. Set auth cookies (access + refresh, same as login)
```

## 5. Frontend Routes

| Route | Purpose | Guard |
|---|---|---|
| `/login` | Email/password form + OAuth buttons | Public; redirect to `/` if authed |
| `/register` | Sign up form | Public; redirect to `/` if authed |
| `/forgot-password` | Email input for reset | Public |
| `/reset-password?token=xxx` | New password form | Public; validates token on mount |
| `/verify-email?token=xxx` | Auto-confirms on load | Public |
| `/verify-email/pending` | "Check your inbox" landing | Authed but unverified |
| `/oauth/error?reason=xxx` | OAuth failure surface | Public |
| `(dashboard layout)` | All authed pages | Authed; shows unverified banner |

### 5.1 State transition diagrams

**Register → verify:**
```
/register
  └─ POST /auth/register (201)
       ├─ cookies set (user logged in, unverified)
       └─ navigate → /verify-email/pending
            └─ user clicks email link
                 └─ /verify-email?token=xxx
                      └─ POST /auth/verify-email/confirm
                           ├─ success → navigate → /
                           └─ failure → show "Link expired" + resend button
```

**Forgot password:**
```
/forgot-password
  └─ POST /auth/forgot-password (200 always)
       └─ show "Check inbox" confirmation
            └─ user clicks email link
                 └─ /reset-password?token=xxx
                      └─ POST /auth/reset-password
                           ├─ success → navigate → /login?reset=1
                           └─ failure → show "Invalid/expired link"
```

**OAuth login:**
```
/login
  └─ click "Continue with GitHub"
       └─ GET /api/auth/oauth/github/start (browser redirect)
            └─ GitHub consent screen
                 └─ GitHub redirects → /api/auth/oauth/github/callback
                      ├─ success → redirect to FRONTEND_URL
                      └─ failure → redirect to /login?error=oauth_failed
```

### 5.2 Unverified banner

Rendered by the authed layout whenever `user.is_verified === false`.

```
┌──────────────────────────────────────────────────────────────┐
│ ⚠ Please verify your email address.  [Resend email]   [ × ] │
└──────────────────────────────────────────────────────────────┘
```

- "Resend email" hits `/auth/verify-email/send`
- Button enters 60-second cooldown after success
- × dismisses for current session only (LocalStorage, not permanent)

## 6. Security Rules

### 6.1 Token hygiene
- Plaintext tokens exist **only** inside email bodies and URL query strings
- Server stores `sha256(token)` — see auth_tokens.token_hash
- Used tokens are marked `used_at` and **never** reusable
- On issuing a new token for a given purpose, old unused tokens for the
  same user + purpose are bulk-marked `used_at` so only the latest is valid

### 6.2 TTLs
| Token | TTL |
|---|---|
| Access JWT (cookie) | 30 min |
| Refresh JWT (cookie) | 7 days (default) / 30 days (remember me) |
| Email verification | 24 hours |
| Password reset | 30 minutes |
| OAuth state cookie | 5 minutes |

### 6.3 OAuth account matching

Input from provider: `(provider, provider_user_id, provider_email, email_verified)`.

```
IF row exists in oauth_accounts WHERE (provider, provider_user_id):
    → use linked user. Login.
ELSE IF provider reports email_verified == true
       AND user exists with email = provider_email:
    → link: insert oauth_accounts row
    → users.is_verified = true  (provider confirms the email)
    → login
ELSE IF user exists with email = provider_email
       (but provider did NOT verify email):
    → DO NOT auto-link. Redirect to /login with a hint:
      "An account with this email exists. Please sign in with your
       password first, then connect GitHub from Settings."
ELSE:
    → create new user (hashed_password = NULL, is_verified=true)
    → insert oauth_accounts row
    → login
```

### 6.4 Session invalidation on password reset

Current design uses **stateless JWTs** for refresh tokens, so we cannot
simply "delete" old tokens. Options:

- **Recommended**: add `users.token_version INTEGER DEFAULT 0`. Refresh
  JWT payload carries a `ver` claim. `/auth/refresh` rejects tokens whose
  `ver` doesn't match current `token_version`. Password reset bumps the
  version by 1 → all outstanding refresh tokens invalidated.
- Alternative: persistent refresh token store — bigger change, skip for now.

### 6.5 CSRF on OAuth callback
- `state` is a cryptographically-random 32-byte value, signed + HttpOnly cookie
- PKCE code verifier included in state cookie for providers that support PKCE

### 6.6 Open-redirect prevention
`redirect_to` query param is accepted only if it starts with `/` and does
not contain `//` (to block `//evil.com`).

### 6.7 Rate limiting

Phase 1 minimum (all implementable in ≤ 20 LOC with Redis):

| Endpoint | Limit |
|---|---|
| POST /auth/login | 5 fails / 15 min / IP |
| POST /auth/forgot-password | 3 / hour / email |
| POST /auth/verify-email/send | 1 / minute / user |

If Redis isn't wired up yet, Phase 1 ships without rate limits and we add
them later. Document this decision in code.

### 6.8 Cookies
All auth cookies: `HttpOnly; Secure; SameSite=Lax; Path=/` (refresh uses
`Path=/api/auth/refresh` as today).

### 6.9 Password policy
- Min 8 characters
- No complexity rules (follows NIST SP 800-63B modern guidance)
- Rejection of top-10k common passwords is nice-to-have (Phase 3)

## 7. Email Infrastructure

### 7.1 Provider
**Resend** (https://resend.com) — 3,000 emails/month free tier, React
Email integration, 5-minute setup.

Required env vars:
```
RESEND_API_KEY=...
EMAIL_FROM=noreply@agentforge.dev
FRONTEND_URL=http://localhost:3000
```

### 7.2 Dev mode
When `DEBUG=true` and `RESEND_API_KEY` is unset, the sender logs the
rendered email to stdout instead of making a network call. No accidental
real-email sends during local work.

### 7.3 Templates

All emails are simple: a single CTA button + plain-text fallback.

| Template | Subject | CTA |
|---|---|---|
| verify-email | "Verify your AgentForge email" | "Verify my email" |
| reset-password | "Reset your AgentForge password" | "Choose a new password" |
| welcome (optional) | "Welcome to AgentForge 🎉" | "Open dashboard" |

## 8. Schemas (Pydantic)

```python
# auth/schemas.py — additions / changes

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)

class VerifyEmailConfirmRequest(BaseModel):
    token: str

class UserResponse(BaseModel):
    # ... existing fields ...
    is_verified: bool
    verified_at: datetime | None = None
```

## 9. Decision Points

Locked once the user confirms these.

| # | Question | Options | Recommendation | Status |
|---|---|---|---|---|
| D1 | Auto-login after register? | a) yes + banner  b) block until verified | **a) yes + banner** | ☐ |
| D2 | Unverified user limitations? | a) none  b) can't execute workflows  c) banner only | **c) banner only** | ☐ |
| D3 | Email provider? | Resend / SMTP / SendGrid | **Resend** | ☐ |
| D4 | Email verification TTL? | 24h / 7d | **24h** | ☐ |
| D5 | Remember me TTL? | 7d / 30d / 90d | **30d** | ☐ |
| D6 | Reset password invalidates all sessions? | yes / no | **yes** | ☐ |
| D7 | Password policy? | 6 / 8 / 8+complexity | **min 8, no complexity** | ☐ |
| D8 | Welcome email after verify? | yes / no | **no, skip Phase 1** | ☐ |
| D9 | Rate limit backend? | Redis / DB / skip | **Redis if available, else skip** | ☐ |
| D10 | OAuth providers? | GitHub / Google / both | **both** | ☐ |
| D11 | OAuth library? | Authlib / manual httpx | **Authlib** | ☐ |
| D12 | Auto-link OAuth by verified email? | yes / no | **yes, only if provider verified** | ☐ |
| D13 | Store provider access tokens? | yes / no | **no, Phase 1** | ☐ |
| D14 | OAuth users require separate email verification? | yes / no | **no, provider confirms** | ☐ |
| D15 | `users.hashed_password` nullable? | yes / no | **yes** (OAuth-only accounts) | ☐ |

## 10. Implementation Phases

Each phase is a single commit-ready unit of work. Tests are interleaved.

### Phase 1 — Backend foundation  _(1–2 days)_
- Alembic migration: `is_verified`, `verified_at`, `token_version`,
  nullable `hashed_password`, `auth_tokens`, `oauth_accounts`
- `auth/tokens.py` — generate / hash / verify helpers
- `auth/emails.py` — Resend integration + templates + dev-stdout fallback
- Authlib registration for providers (behind a feature-flag env var)
- Env var additions

### Phase 2 — Backend email/password endpoints  _(1 day)_
- Update `POST /auth/register` (issue verification token, send email)
- Update `POST /auth/login` (accept `remember_me`, encode into JWT)
- Update `POST /auth/refresh` (carry `remember` forward; check `token_version`)
- New: `POST /auth/verify-email/send`
- New: `POST /auth/verify-email/confirm`
- New: `POST /auth/forgot-password`
- New: `POST /auth/reset-password` (bump `token_version`)

### Phase 3 — Backend OAuth endpoints  _(1 day)_
- `GET /auth/oauth/{provider}/start`
- `GET /auth/oauth/{provider}/callback`
- Account-matching logic per § 6.3
- State-cookie CSRF protection

### Phase 4 — Frontend  _(1 day)_
- `/verify-email/pending` page
- `/verify-email` auto-confirm page
- `/reset-password` form page
- Wire `/forgot-password` to real API
- `LoginForm`: wire `remember_me` + real OAuth URLs (remove "coming soon" stubs)
- `RegisterForm`: redirect to `/verify-email/pending` on success
- Unverified banner in dashboard layout with resend + cooldown

### Phase 5 — Polish & testing  _(0.5 day)_
- Email templates styled (React Email)
- Error pages: `/oauth/error`, expired-token surfaces
- Manual test matrix — all flows, all providers, expired & used tokens
- Update `docs/flows/user-registration.md` once Phase 4 lands

Total: **~5 days** for a solo dev.

## 11. Open Questions

Things we **cannot** proceed without:

1. **Resend account / API key.** Will the user provision one, or use
   stdout-only mode in dev until production?
2. **Domain for FROM address.** `noreply@<domain>` — which domain?
3. **GitHub OAuth App.** Client ID / secret + registered callback URL.
4. **Google OAuth Client.** Same.
5. **FRONTEND_URL** for production (used in email links).

Things that can be deferred:

- Redis for rate limiting (fall back to no-limit in Phase 1)
- React Email templates (plain HTML works for Phase 1-2)

## 12. Non-goals for this plan

- Server-side session store (we stay stateless JWT + versioning)
- Multi-tenant / organisations
- SSO / SAML — wait until an enterprise customer asks
- Passkeys / WebAuthn — tracked separately

---

_Last updated: draft prior to Phase 1 kickoff. Update status boxes in
§ 9 as decisions land._
