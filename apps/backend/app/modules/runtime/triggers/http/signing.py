"""HMAC signature + replay-window verification for inbound webhooks.

Two layers, both opt-in via node config:
  ``require_signature`` — caller must include
      X-Hub-Signature-256: sha256=<hex>
    where <hex> is HMAC-SHA256(workflow.webhook_secret, raw_body).
    Matches GitHub's webhook scheme so existing sender libs work.
  ``replay_window_seconds`` (int > 0) — caller must include
      X-Webhook-Timestamp: <unix epoch seconds>
    that lies within ``± replay_window_seconds`` of server time.
    Defeats trivial replay attacks even when an attacker captures
    the signed payload from a CDN log.

Both raise ``WebhookAuthError`` (401) when validation fails. Neither
returns ``200 with detail`` — wrong here means the caller is either
mis-configured or hostile, and we want hosts to fix it.
"""
from __future__ import annotations

import hashlib
import hmac
import time

from fastapi import HTTPException, status


class WebhookAuthError(HTTPException):
    """401 with a structured ``code`` so the FE / sender can branch on it."""

    def __init__(self, code: str, detail: str):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": code, "detail": detail},
        )


_SIG_HEADER = "x-hub-signature-256"
_TS_HEADER = "x-webhook-timestamp"
_SIG_PREFIX = "sha256="


def verify_signature(
    raw_body: bytes,
    *,
    secret: str | None,
    provided: str | None,
) -> None:
    """Constant-time check of HMAC-SHA256 over the raw body.

    ``provided`` is the full header value including the ``sha256=``
    prefix (GitHub convention). Strip the prefix here so callers
    don't have to.
    """
    if not secret:
        raise WebhookAuthError(
            "signing_disabled",
            "Workflow has no webhook secret configured; rotate one to enable signature verification.",
        )
    if not provided:
        raise WebhookAuthError(
            "missing_signature",
            f"Header {_SIG_HEADER} is required when require_signature is true.",
        )
    if not provided.startswith(_SIG_PREFIX):
        raise WebhookAuthError(
            "bad_signature_format",
            f"Header {_SIG_HEADER} must start with 'sha256='.",
        )
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, provided[len(_SIG_PREFIX) :]):
        raise WebhookAuthError(
            "signature_mismatch",
            "Signature does not match the request body.",
        )


def verify_timestamp(
    *,
    provided: str | None,
    window_seconds: int,
    now: float | None = None,
) -> None:
    """Reject when the caller's timestamp is outside ``± window``.

    ``now`` is overridable for tests; production passes None.
    """
    if window_seconds <= 0:
        return  # 0 disables; caller already short-circuits but be defensive.
    if not provided:
        raise WebhookAuthError(
            "missing_timestamp",
            f"Header {_TS_HEADER} is required when replay_window_seconds is set.",
        )
    try:
        ts = int(provided)
    except ValueError:
        raise WebhookAuthError(
            "bad_timestamp_format",
            f"Header {_TS_HEADER} must be an integer (unix epoch seconds).",
        ) from None
    current = now if now is not None else time.time()
    delta = abs(current - ts)
    if delta > window_seconds:
        raise WebhookAuthError(
            "stale_timestamp",
            f"Timestamp is {int(delta)}s away from server time (window: {window_seconds}s).",
        )


def header(headers, name: str) -> str | None:
    """Case-insensitive header lookup. FastAPI's ``Request.headers`` is
    already case-insensitive but ``_build_input`` flattens to a plain
    dict in places — keep this here as a safe shared helper."""
    if hasattr(headers, "get"):
        return headers.get(name)
    return None
