"""Sentry SDK initialization.

Call ``init_sentry()`` once at process start (before ``FastAPI()`` is
created so the integrations can wrap Starlette/asyncio properly). When
``SENTRY_DSN`` is empty the call is a no-op — no network, no module
import side-effects beyond what the SDK does on its own import.
"""
from __future__ import annotations

import logging

import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from app.platform.config import settings

logger = logging.getLogger("agentforge")


def init_sentry() -> None:
    if not settings.SENTRY_DSN:
        logger.info("Sentry disabled (SENTRY_DSN not set)")
        return

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        release=settings.RELEASE or None,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        # send_default_pii=False (default) — don't auto-attach request bodies
        # / cookies / headers. Sensitive payloads (API keys in tool configs,
        # KB document contents) must never leave the box without explicit opt-in.
        send_default_pii=False,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            StarletteIntegration(transaction_style="endpoint"),
            AsyncioIntegration(),
            # WARNING-level breadcrumbs, ERROR+ as captured events.
            LoggingIntegration(level=logging.WARNING, event_level=logging.ERROR),
        ],
    )
    logger.info(
        "Sentry initialized (env=%s, release=%s, traces=%.2f)",
        settings.ENVIRONMENT,
        settings.RELEASE or "auto",
        settings.SENTRY_TRACES_SAMPLE_RATE,
    )
