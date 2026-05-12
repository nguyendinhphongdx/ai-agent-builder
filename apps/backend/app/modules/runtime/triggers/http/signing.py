"""HTTP-trigger signature + replay-window verification — thin
wrapper around the shared helpers in ``_signing.py``.

GitHub-style ``X-Hub-Signature-256: sha256=<hex>`` over the raw
body, plus an opt-in ``X-Webhook-Timestamp`` replay window. Kept
as its own module so existing router + tests keep importing from
this stable path.
"""
from __future__ import annotations

from app.modules.runtime.triggers._signing import (
    TriggerAuthError as WebhookAuthError,
)
from app.modules.runtime.triggers._signing import (
    verify_github_v0,
)
from app.modules.runtime.triggers._signing import (
    verify_timestamp as _verify_timestamp_shared,
)

__all__ = ["WebhookAuthError", "verify_signature", "verify_timestamp", "header"]


def verify_signature(
    raw_body: bytes,
    *,
    secret: str | None,
    provided: str | None,
) -> None:
    """Constant-time HMAC-SHA256 check. Backwards-compatible signature."""
    verify_github_v0(
        raw_body=raw_body,
        secret=secret,
        signature_header=provided,
    )


def verify_timestamp(
    *,
    provided: str | None,
    window_seconds: int,
    now: float | None = None,
) -> None:
    """Replay-window check. Backwards-compatible keyword shape."""
    _verify_timestamp_shared(
        provided,
        window_seconds=window_seconds,
        now=now,
        header_name="X-Webhook-Timestamp",
    )


def header(headers, name: str) -> str | None:
    """Case-insensitive header lookup used by some legacy call sites."""
    if hasattr(headers, "get"):
        return headers.get(name)
    return None
