---
id: guides-momo-setup
title: MoMo Setup — VND payments for the Hub
domain: guides
tags: [momo, payments, vietnam, vnd, hub, marketplace, ipn, webhook]
related: [arch-operations, api-hub-endpoints]
summary: Step-by-step playbook to enable VND payments via MoMo on the Hub — register merchant, configure env vars, expose IPN, validate signatures, run a sandbox test, and settle author payouts.
---

# MoMo Setup

How to enable VND-priced templates on the Hub. MoMo is the Vietnamese
e-wallet that handles paid checkouts for any template priced in VND;
USD/EUR/GBP go through Stripe (see [`arch-operations`](../architecture/operations.md) §5).

This guide is written for the **platform operator** — the person
configuring `apps/backend/.env`. Author-side onboarding currently does
not exist (see §7 below for the future direction).

---

## 1. Why MoMo and not Stripe for VND

Stripe Connect Express lets any user become a connected merchant
through an API in ~2 minutes. **MoMo has no equivalent.** Becoming a
MoMo merchant requires Vietnamese business registration and an
out-of-band contract with MoMo Business — there is no self-serve API.

Practically, this means:

- **One MoMo merchant per platform**, not one per author. The platform
  is the merchant of record for every VND sale.
- **Author payouts are platform-collects**: all VND funds land in the
  platform's MoMo balance; the platform settles authors out-of-band
  via bank transfer (see §6).
- **Currency-locked to VND.** Mixed-currency carts aren't supported;
  template authors set price in VND on publish, and the dispatch in
  `payments.service.get_provider_for_template` routes the checkout to
  MoMo automatically.

If multi-merchant ever becomes a requirement, see §7.

---

## 2. Register a MoMo Business merchant account

You need a Vietnamese business entity to register. The flow is offline
and takes a few business days:

1. Apply at [business.momo.vn](https://business.momo.vn). MoMo will
   request company registration documents (giấy phép kinh doanh), tax
   ID (mã số thuế), and a bank account in the company's name.
2. After approval, MoMo gives you a sandbox account immediately and a
   production account once the contract is signed. They share the same
   API shape — only the endpoint host and credentials differ.
3. From the dashboard, copy three values:
   - **`partnerCode`** — public id, ~10 chars (e.g. `MOMO`).
   - **`accessKey`** — public.
   - **`secretKey`** — **secret.** Treat this like a password; rotating
     it requires raising a support ticket with MoMo.

You'll have one set for sandbox and one for production. **Never reuse
production credentials in sandbox** — and vice versa.

---

## 3. Configure `apps/backend/.env`

Add these to the backend `.env` (template lives in `apps/backend/.env.example`):

```env
# ─── MoMo (VND payments — Vietnam) ───────────────────────────────────────────
MOMO_PARTNER_CODE=
MOMO_ACCESS_KEY=
MOMO_SECRET_KEY=
# Production: https://payment.momo.vn  ·  Sandbox: https://test-payment.momo.vn
MOMO_ENDPOINT=https://test-payment.momo.vn
# Where MoMo redirects the buyer's browser after payment.
MOMO_RETURN_URL=https://app.example.com/hub/purchase-complete
# Public HTTPS URL MoMo POSTs IPN events to (must serve /api/webhooks/momo).
# Empty in dev → IPN won't fire; tests rely on the redirect query string.
MOMO_NOTIFY_URL=https://app.example.com/api/webhooks/momo
```

| Var | Purpose | Required when |
|---|---|---|
| `MOMO_PARTNER_CODE` | Identifies the merchant | always (empty disables VND checkout) |
| `MOMO_ACCESS_KEY` | Public auth | always |
| `MOMO_SECRET_KEY` | HMAC signing key | always |
| `MOMO_ENDPOINT` | API host | switch between sandbox (`test-payment.momo.vn`) and production (`payment.momo.vn`) |
| `MOMO_RETURN_URL` | Browser-redirect after pay | always |
| `MOMO_NOTIFY_URL` | Server-to-server IPN target | production. Sandbox can omit if you only verify the redirect path. |

Empty `MOMO_PARTNER_CODE` keeps MoMo dormant — `POST /api/templates/{id}/purchase`
on a VND template returns 503 (not 500) and `/api/webhooks/momo` returns
404, so an unconfigured deploy is honest about the missing channel.

---

## 4. Expose the IPN endpoint

MoMo's *Instant Payment Notification* is a server-to-server POST
informing us a payment completed. Without it, we'd never flip
`Purchase.status='paid'` and the buyer's redirect-poll would spin
forever.

Requirements:

- **HTTPS only.** MoMo refuses `http://` for production.
- **Publicly reachable.** No IP allow-listing on MoMo's side; rely on
  HMAC signature for trust.
- **Path:** `POST /api/webhooks/momo` (mounted by
  `app.payments.webhooks.momo`).
- **Body:** JSON. Each request carries a `signature` field.

Local development:

- The default MoMo sandbox does not POST IPN to a `localhost` URL.
  Use [ngrok](https://ngrok.com) or [cloudflared tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
  to expose `http://localhost:8000/api/webhooks/momo` over HTTPS, then
  set `MOMO_NOTIFY_URL` to the tunnel URL.
- Alternative: skip IPN locally and verify only the redirect-side
  poll. The `Purchase.status` will stay `pending` until you trigger
  IPN manually.

---

## 5. Run a sandbox test transaction

End-to-end smoke test, expects backend running with MoMo configured in
sandbox mode:

```bash
# 1. Publish a paid VND template (UI: Libraries → agent → Publish,
#    pick "Paid → VND").
# 2. As a different user, browse the Hub, hit "Buy".
# 3. You're redirected to MoMo's sandbox payment page.
# 4. Pay with the sandbox test wallet credentials MoMo provides in their
#    docs (sandbox accepts a fixed dummy account).
# 5. MoMo POSTs IPN to /api/webhooks/momo. Backend verifies signature,
#    flips Purchase.status='paid', forks the agent for the buyer.
# 6. Browser redirected to MOMO_RETURN_URL?orderId=...; the FE polls
#    /templates/purchases/{orderId}/status and shows the new agent.
```

Watch the backend logs for `momo ipn:` lines:

```
momo ipn: order=01HW… resultCode=0
momo ipn: forked template=… version=… buyer=… → agent=…
```

A `bad signature` warning means `MOMO_SECRET_KEY` doesn't match the one
MoMo signed with — check sandbox vs prod confusion.

---

## 6. Author payouts (V1 — platform-collects)

Once a VND sale lands, the funds sit in the platform's MoMo balance.
Authors don't have a Stripe-Connect-style direct deposit. Settlement
flow:

1. Author sees their owed net (gross − 10% platform fee) in
   `/settings/payouts`. Numbers are computed deterministically from
   `STRIPE_PLATFORM_FEE_BPS` so on-screen and bank-transfer amounts
   agree.
2. Platform runs settlement out-of-band — typically once per
   month — and bank-transfers each author's net total. Track which
   purchases have been settled in your own ledger; the
   `agent_template_purchases` table doesn't carry a "settled" flag
   yet. (Add one when this becomes a hot-path concern.)
3. For tax reporting, MoMo provides invoice exports from the merchant
   dashboard. Author 1099-equivalents (in Vietnam: invoices for tax
   declaration) are the platform's responsibility, not MoMo's.

**Refunds.** `POST /api/admin/purchases/{id}/refund` calls
`MoMoProvider.refund` which hits MoMo's
`/v2/gateway/api/refund` with an HMAC-signed request. The author's owed
balance ledger should subtract the refunded amount accordingly.

---

## 7. Future — per-author MoMo connect

If you want each author to receive payments directly to *their* MoMo
merchant balance (no platform-collects step), the architecture is:

1. **Author registers separately** with MoMo Business — out-of-band
   process, on the author's side. MoMo issues them their own
   `partnerCode/accessKey/secretKey`.
2. **Settings UI captures the credentials.** Add a "Connect MoMo" form
   on `/settings/payouts` next to Stripe. Encrypt with the same Fernet
   helper that encrypts AI credentials and store on the User row (or a
   separate `payment_accounts` table).
3. **Checkout uses the author's credentials.** `MoMoProvider.create_checkout`
   reads from `template.author.momo_*` instead of the platform-level
   `settings.MOMO_*`. Platform fee comes via reduce-from-display: we
   calculate fees and ask the author to remit them out-of-band, since
   MoMo has no `application_fee` primitive equivalent.

This is roughly a 2-3 hour lift but **gates publishing on the author
having registered with MoMo Business themselves** — a much higher
friction point than connecting a Stripe Express account. For most
launches the platform-collects model is the right default.

---

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| 503 on POST /purchase for VND template | `MOMO_PARTNER_CODE` empty | Set the three MoMo env vars and restart. |
| `MoMo create failed: code=… msg=…` | Bad signature, expired credentials, or wrong endpoint host | Verify `MOMO_SECRET_KEY`; check sandbox vs prod host. |
| IPN never arrives | `MOMO_NOTIFY_URL` not publicly reachable, http:// instead of https:// | Front the backend with HTTPS; for dev use a tunnel. |
| `momo ipn: bad signature` warning | `MOMO_SECRET_KEY` doesn't match MoMo's records | Often sandbox key reused in prod or vice versa. Rotate credentials at MoMo if compromised. |
| Buyer paid but Purchase stuck `pending` | IPN failed (firewall / 5xx response). MoMo retries every few minutes for ~24h. | Check `/api/webhooks/momo` logs for the retry; fix the failure cause. |
| Purchase row missing on IPN | Race: IPN arrived before the create-session DB commit landed. | MoMo retries; the second delivery finds the row. No action. |

---

## 9. Operational checklist before going live

- [ ] Production `MOMO_*` env vars set (separately from sandbox).
- [ ] `MOMO_NOTIFY_URL` is HTTPS and publicly reachable.
- [ ] `MOMO_RETURN_URL` lands at a real `/hub/purchase-complete` page.
- [ ] At least one sandbox round-trip completed end-to-end with the
      Purchase row flipping to `paid`.
- [ ] Settlement workflow agreed with finance — who runs it, how often,
      from which bank account.
- [ ] Refund procedure tested in sandbox.
- [ ] Sentry receives `momo ipn:` errors (set `SENTRY_DSN`; see
      [`arch-operations`](../architecture/operations.md) §4).
