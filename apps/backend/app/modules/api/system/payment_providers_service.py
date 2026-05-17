"""Admin-facing service for the ``payment_provider_configs`` table.

Thin wrapper over :mod:`app.modules.commerce.payments.config` that
shapes rows for the admin grid: masks secrets, exposes per-provider
metadata (which keys are expected), and routes test-connection calls.

Why mask instead of omitting: the admin grid needs to know *that* a
key was entered before (so the operator doesn't accidentally wipe a
configured row), but the plaintext must never leave the API.
"""
from __future__ import annotations

import uuid
from typing import Any

from app.modules.commerce.payments.config import (
    ProviderConfig,
    delete_provider_config,
    get_provider_config,
    list_provider_configs,
    test_provider_connection,
    upsert_provider_config,
)

# Per-provider key catalogue — what the FE should render input fields
# for. Each entry: (key, label, hint). Secrets get a password field +
# masking; non-secrets render plain. Hints are short, one-line copy
# rendered under the input — long-form prose lives in PROVIDER_GUIDES.
PROVIDER_SECRET_KEYS: dict[str, list[tuple[str, str, str]]] = {
    "stripe": [
        ("secret_key", "Secret API key", "Starts with sk_test_… (test) or sk_live_… (live). Dashboard → Developers → API keys."),
        ("publishable_key", "Publishable key", "Starts with pk_test_… / pk_live_…. Used by the JS SDK on the FE — not strictly required if you don't embed Checkout."),
        ("webhook_secret", "Webhook signing secret", "Starts with whsec_…. Created when you register the webhook endpoint below."),
    ],
    "momo": [
        ("partner_code", "Partner code", "Issued by MoMo Business when you register your merchant account."),
        ("access_key", "Access key", "Half of the API credential pair from the MoMo Business portal."),
        ("secret_key", "Secret key", "Used to HMAC-sign outbound create + refund requests; MoMo signs IPN payloads with the same key."),
    ],
}

PROVIDER_CONFIG_KEYS: dict[str, list[tuple[str, str, str]]] = {
    "stripe": [
        ("platform_fee_bps", "Platform fee (basis points)", "Defaults to 1500 = 15%. Applied as application_fee on Connect destination charges. 100 bps = 1%."),
        ("success_url", "Hub success URL template", "Where buyers land after a successful Hub purchase. Use {CHECKOUT_SESSION_ID} placeholder if you want the session id."),
        ("cancel_url", "Hub cancel URL template", "Where buyers land if they hit Cancel during Hub checkout."),
        ("connect_return_url", "Connect onboarding return URL", "Where authors are redirected after finishing Stripe Connect onboarding."),
        ("connect_refresh_url", "Connect onboarding refresh URL", "Used by Stripe if the onboarding link expires — should restart the flow."),
        ("billing_success_url", "Billing portal success URL", "Post-subscription-checkout redirect (org-level billing flow)."),
        ("billing_cancel_url", "Billing portal cancel URL", "Cancel redirect for the org-level billing flow."),
    ],
    "momo": [
        ("endpoint", "MoMo API endpoint", "https://test-payment.momo.vn for sandbox; https://payment.momo.vn for production."),
        ("notify_url", "IPN notify URL", "MoMo POSTs payment results here. Must match the path your backend exposes — see the webhook URL below."),
        ("return_url", "Browser return URL", "Where MoMo redirects the buyer's browser after they pay."),
    ],
}

# Friendly default labels + kinds for the "not yet configured" entries
# we synthesise when an admin opens the page on a fresh deploy. Keep
# the codes in sync with the constants in `models.payment_provider_config`.
_PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "stripe": {"display_name": "Stripe", "kind": "both"},
    "momo": {"display_name": "MoMo", "kind": "paid"},
}


# Long-form setup guides surfaced as a collapsible block at the top of
# each editor. Each step is plain text — the FE renders them as a
# numbered list. ``webhook_path`` is the route the provider should POST
# IPNs / events to; the FE prefixes it with the deployment's API base.
PROVIDER_GUIDES: dict[str, dict[str, Any]] = {
    "stripe": {
        "intro": (
            "Stripe handles both Hub one-time purchases (USD / EUR / …) "
            "and recurring org-level subscriptions. Same secret + webhook "
            "secret cover all event types — the dispatcher in the backend "
            "routes Hub vs Connect vs Subscription events by prefix."
        ),
        "webhook_path": "/api/webhooks/stripe",
        "steps": [
            "Sign in to dashboard.stripe.com and copy the secret key from Developers → API keys. Use a *Test mode* key while you're verifying — flip Test mode off in this UI once you switch to live keys.",
            "Developers → Webhooks → Add endpoint. Use the URL above (prefix with your deployment's API base) and select these events: checkout.session.completed, account.updated, customer.subscription.*, invoice.payment_succeeded, invoice.payment_failed.",
            "Stripe shows the webhook signing secret (whsec_…) once after creation — paste it into Webhook signing secret below.",
            "If you sell through Hub: enable Connect (Settings → Connect → Get started) so authors can onboard their own Stripe accounts. Express accounts are the recommended type.",
            "Click Test connection below to verify Stripe accepts the secret key.",
            "Flip Enabled and Save. Checkout endpoints stay 503 until both are set.",
        ],
        "docs": [
            ("Stripe API keys", "https://stripe.com/docs/keys"),
            ("Webhook signatures", "https://stripe.com/docs/webhooks/signatures"),
            ("Stripe Connect Express", "https://stripe.com/docs/connect/express-accounts"),
        ],
    },
    "momo": {
        "intro": (
            "MoMo is Vietnam-only and VND-locked. There is no Connect "
            "equivalent — the platform collects all funds and settles "
            "with authors out-of-band. Recurring billing isn't supported "
            "by MoMo's standard API; subscriptions still route through Stripe."
        ),
        "webhook_path": "/api/webhooks/momo",
        "steps": [
            "Register a merchant account at business.momo.vn (Vietnamese business registration required). MoMo assigns you a Partner code, Access key, and Secret key.",
            "In your MoMo Business dashboard, set IPN URL = the webhook URL above (prefix with your deployment's API base). MoMo POSTs payment results here.",
            "Set Endpoint to https://test-payment.momo.vn for the sandbox or https://payment.momo.vn for production — toggle this UI's Test mode flag accordingly.",
            "Set Return URL to a page on your frontend that polls /api/purchase-status — buyers land there after paying.",
            "Paste Partner code, Access key, Secret key below, hit Test connection (verifies the three values are present), then flip Enabled and Save.",
        ],
        "docs": [
            ("MoMo Business portal", "https://business.momo.vn/"),
            ("MoMo Payment API docs", "https://developers.momo.vn/v3/docs/payment/"),
        ],
    },
}


def _mask(value: str) -> str:
    """Return a masked preview of a secret so the admin grid can show
    that a key is set without leaking it. Keeps the last 4 chars for
    operator identification; matches the format Stripe's dashboard uses.
    """
    if not value:
        return ""
    if len(value) <= 4:
        return "•" * len(value)
    return "•" * (len(value) - 4) + value[-4:]


def _serialize(cfg: ProviderConfig, *, persisted: bool = True) -> dict[str, Any]:
    masked_secrets = {k: _mask(v) for k, v in cfg.secrets.items()}
    return {
        "code": cfg.code,
        "display_name": cfg.display_name,
        "kind": cfg.kind,
        "is_enabled": cfg.is_enabled,
        "is_test_mode": cfg.is_test_mode,
        "persisted": persisted,
        "secrets_preview": masked_secrets,
        "secret_keys": [
            {"key": k, "label": label, "hint": hint, "is_set": bool(cfg.secrets.get(k))}
            for k, label, hint in PROVIDER_SECRET_KEYS.get(cfg.code, [])
        ],
        "config": cfg.config,
        "config_keys": [
            {"key": k, "label": label, "hint": hint}
            for k, label, hint in PROVIDER_CONFIG_KEYS.get(cfg.code, [])
        ],
        "guide": PROVIDER_GUIDES.get(cfg.code),
        "last_tested_at": cfg.last_tested_at.isoformat() if cfg.last_tested_at else None,
        "last_test_result": cfg.last_test_result,
    }


def _placeholder(code: str) -> ProviderConfig:
    """Synthesise an empty ``ProviderConfig`` for a provider that has a
    class in code but no DB row yet. Lets the admin form render with
    sensible defaults — saving the form upserts the row."""
    defaults = _PROVIDER_DEFAULTS.get(code, {"display_name": code.title(), "kind": "both"})
    return ProviderConfig(
        code=code,
        display_name=defaults["display_name"],
        kind=defaults["kind"],
        is_enabled=False,
        is_test_mode=True,
        secrets={},
        config={},
    )


async def list_for_admin() -> list[dict[str, Any]]:
    """All providers — persisted DB rows merged with the in-code
    registry so admins on a fresh deploy still see Stripe/MoMo and can
    fill them in from the UI (no CLI required)."""
    rows = await list_provider_configs()
    by_code = {r.code: r for r in rows}
    out: list[dict[str, Any]] = [_serialize(r, persisted=True) for r in rows]
    for code in PROVIDER_SECRET_KEYS:
        if code not in by_code:
            out.append(_serialize(_placeholder(code), persisted=False))
    return out


async def get_for_admin(code: str) -> dict[str, Any] | None:
    cfg = await get_provider_config(code)
    if cfg is not None:
        return _serialize(cfg, persisted=True)
    # No DB row yet, but the provider is known to the registry — return
    # an empty editor scaffold instead of 404 so deep-links work.
    if code in PROVIDER_SECRET_KEYS:
        return _serialize(_placeholder(code), persisted=False)
    return None


async def upsert_from_admin(
    code: str,
    *,
    display_name: str,
    kind: str,
    is_enabled: bool,
    is_test_mode: bool,
    secrets: dict[str, str] | None,
    config: dict[str, Any] | None,
    description: str | None,
    actor_user_id: uuid.UUID | None,
) -> dict[str, Any]:
    """Save admin edits. ``secrets=None`` preserves existing secrets so
    the admin can edit non-secret config without re-entering the key
    (FE sends None for unchanged secrets)."""
    result = await upsert_provider_config(
        code,
        display_name=display_name,
        kind=kind,
        is_enabled=is_enabled,
        is_test_mode=is_test_mode,
        secrets=secrets,
        config=config,
        description=description,
        actor_user_id=actor_user_id,
    )
    return _serialize(result)


async def delete_from_admin(code: str) -> bool:
    return await delete_provider_config(code)


async def run_test_connection(code: str) -> dict[str, Any]:
    ok, msg = await test_provider_connection(code)
    return {"ok": ok, "message": msg}


__all__ = [
    "PROVIDER_CONFIG_KEYS",
    "PROVIDER_SECRET_KEYS",
    "delete_from_admin",
    "get_for_admin",
    "list_for_admin",
    "run_test_connection",
    "upsert_from_admin",
]
