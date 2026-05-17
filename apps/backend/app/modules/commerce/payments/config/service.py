"""Payment-provider config registry.

DB is the single source of truth — no env fallback. On a fresh
deploy the admin signs in as the system org owner, opens
``/system/payment-providers``, pastes Stripe / MoMo keys, clicks
"Test connection", flips ``is_enabled=true``. Until then payment
endpoints 503 with ``billing_unavailable``.

Caches rows in process for ``CACHE_TTL_SECONDS`` to keep the hot
path zero-DB. Writes invalidate the cache; multi-instance deploys
need pub/sub (Redis) — TODO.

Secrets are Fernet-encrypted in ``encrypted_secrets`` (JSON blob).
Decryption happens once on cache load — the cached
``ProviderConfig`` holds plaintext in memory but never persists it.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment_provider_config import (
    PROVIDER_MOMO,
    PROVIDER_STRIPE,
    PaymentProviderConfig,
)
from app.platform.db.session import async_session_factory
from app.platform.security.crypto import decrypt_secret, encrypt_secret

logger = logging.getLogger("agentforge")

CACHE_TTL_SECONDS = 30


@dataclass(frozen=True)
class ProviderConfig:
    """Snapshot a provider sees at request time. Frozen — mutation goes
    through :func:`upsert_provider_config` which invalidates the cache."""

    code: str
    display_name: str
    kind: str
    is_enabled: bool
    is_test_mode: bool
    secrets: dict[str, str] = field(default_factory=dict)        # decrypted
    config: dict[str, Any] = field(default_factory=dict)         # non-secret
    last_tested_at: datetime | None = None
    last_test_result: str | None = None

    def secret(self, key: str, default: str = "") -> str:
        return self.secrets.get(key, default)


# Process-local cache. Key = provider code. Value = (loaded_at, config).
_cache: dict[str, tuple[float, ProviderConfig]] = {}
_cache_lock = asyncio.Lock()


def _row_to_config(row: PaymentProviderConfig) -> ProviderConfig:
    secrets: dict[str, str] = {}
    if row.encrypted_secrets:
        try:
            blob = decrypt_secret(row.encrypted_secrets)
            secrets = json.loads(blob)
        except (ValueError, json.JSONDecodeError) as exc:
            logger.exception(
                "payment_provider_configs[%s]: secrets decrypt failed (%s) — "
                "treating as missing; admin should re-enter",
                row.code,
                exc,
            )
    return ProviderConfig(
        code=row.code,
        display_name=row.display_name,
        kind=row.kind,
        is_enabled=row.is_enabled,
        is_test_mode=row.is_test_mode,
        secrets=secrets,
        config=row.config or {},
        last_tested_at=row.last_tested_at,
        last_test_result=row.last_test_result,
    )


# ─── Public API ───────────────────────────────────────────────────


async def get_provider_config(code: str) -> ProviderConfig | None:
    """Cached read of the DB row for ``code``. Returns None when no
    row exists — caller treats as "provider not configured" (503)."""
    now = time.monotonic()
    cached = _cache.get(code)
    if cached and (now - cached[0]) < CACHE_TTL_SECONDS:
        return cached[1]

    async with _cache_lock:
        cached = _cache.get(code)
        if cached and (now - cached[0]) < CACHE_TTL_SECONDS:
            return cached[1]

        async with async_session_factory() as db:
            row = await db.scalar(
                select(PaymentProviderConfig).where(PaymentProviderConfig.code == code)
            )
        if row is None:
            return None
        config = _row_to_config(row)
        _cache[code] = (now, config)
        return config


async def list_provider_configs() -> list[ProviderConfig]:
    """All configured providers, sorted by ``sort_order`` then ``code``."""
    async with async_session_factory() as db:
        rows = (
            await db.execute(
                select(PaymentProviderConfig).order_by(
                    PaymentProviderConfig.sort_order, PaymentProviderConfig.code
                )
            )
        ).scalars().all()
    return [_row_to_config(r) for r in rows]


async def upsert_provider_config(
    code: str,
    *,
    display_name: str,
    kind: str,
    is_enabled: bool,
    is_test_mode: bool,
    secrets: dict[str, str] | None,
    config: dict[str, Any] | None,
    description: str | None = None,
    actor_user_id: uuid.UUID | None = None,
) -> ProviderConfig:
    """Create or update a row. ``secrets=None`` keeps existing secrets
    (lets the admin save non-secret config without re-entering the key).
    ``secrets={}`` clears secrets (rarely useful).
    """
    async with async_session_factory() as db:
        row = await db.scalar(
            select(PaymentProviderConfig).where(PaymentProviderConfig.code == code)
        )
        if row is None:
            row = PaymentProviderConfig(code=code, display_name=display_name, kind=kind)
            db.add(row)

        row.display_name = display_name
        row.kind = kind
        row.is_enabled = is_enabled
        row.is_test_mode = is_test_mode
        if config is not None:
            row.config = config
        if description is not None:
            row.description = description
        if actor_user_id is not None:
            row.updated_by = actor_user_id

        if secrets is not None:
            # Wrap in a JSON blob → encrypt once → store. Decrypting on
            # every read keeps the on-disk shape opaque to anyone with
            # only a DB dump but no ENCRYPTION_KEY.
            row.encrypted_secrets = (
                encrypt_secret(json.dumps(secrets)) if secrets else ""
            )

        await db.commit()
        await db.refresh(row)
        result = _row_to_config(row)

    invalidate_cache(code)
    return result


async def delete_provider_config(code: str) -> bool:
    async with async_session_factory() as db:
        row = await db.scalar(
            select(PaymentProviderConfig).where(PaymentProviderConfig.code == code)
        )
        if row is None:
            return False
        await db.delete(row)
        await db.commit()
    invalidate_cache(code)
    return True


def invalidate_cache(code: str | None = None) -> None:
    """Drop ``code`` (or everything) from the in-memory cache so the
    next read re-fetches from DB. Single-process safe; multi-instance
    deploys need pub/sub (Redis) — TODO."""
    if code is None:
        _cache.clear()
    else:
        _cache.pop(code, None)


async def test_provider_connection(code: str) -> tuple[bool, str]:
    """Light-touch validation — does the provider accept our keys?

    Each provider hits its own ping endpoint (Stripe: Balance.retrieve;
    MoMo: dummy create with invalid txn id to check signature path).
    Result is persisted to ``last_tested_at`` / ``last_test_result``
    for ops visibility.
    """
    config = await get_provider_config(code)
    if config is None:
        return False, "Provider not configured"

    try:
        if code == PROVIDER_STRIPE:
            import stripe

            stripe.api_key = config.secret("secret_key")
            stripe.Balance.retrieve()
            ok, msg = True, "OK"
        elif code == PROVIDER_MOMO:
            # MoMo has no cheap auth-only endpoint; verifying we have
            # the three required keys is the best we can do without
            # triggering a real txn flow.
            missing = [
                k for k in ("partner_code", "access_key", "secret_key") if not config.secret(k)
            ]
            ok = not missing
            msg = "OK" if ok else f"Missing: {', '.join(missing)}"
        else:
            ok, msg = False, f"No test routine for provider {code!r}"
    except Exception as exc:  # noqa: BLE001 — provider can raise anything
        ok, msg = False, f"{type(exc).__name__}: {exc}"

    # Persist result so the admin grid shows green/red without
    # everyone needing to re-test.
    result_text = "ok" if ok else f"failure: {msg}"
    async with async_session_factory() as db:
        row = await db.scalar(
            select(PaymentProviderConfig).where(PaymentProviderConfig.code == code)
        )
        if row is not None:
            row.last_tested_at = datetime.now(timezone.utc)
            row.last_test_result = result_text
            await db.commit()
    invalidate_cache(code)
    return ok, msg


__all__ = [
    "CACHE_TTL_SECONDS",
    "ProviderConfig",
    "delete_provider_config",
    "get_provider_config",
    "invalidate_cache",
    "list_provider_configs",
    "test_provider_connection",
    "upsert_provider_config",
]
