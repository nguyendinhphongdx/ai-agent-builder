"""Slack request signature verification — thin wrapper around the
shared helper in ``_signing.py``.

Kept as its own module (rather than calling the shared helper
directly at router-level) so tests + downstream tooling that
already import from this path keep working.
"""
from __future__ import annotations

from app.modules.runtime.triggers._signing import (
    TriggerAuthError as SlackAuthError,
)
from app.modules.runtime.triggers._signing import (
    verify_slack_v0,
)

__all__ = ["SlackAuthError", "verify"]


def verify(
    *,
    raw_body: bytes,
    signing_secret: str,
    provided_signature: str | None,
    provided_timestamp: str | None,
    window_seconds: int,
    now: float | None = None,
) -> None:
    """Backwards-compatible wrapper. Delegates to ``verify_slack_v0``."""
    verify_slack_v0(
        raw_body=raw_body,
        signing_secret=signing_secret,
        signature_header=provided_signature,
        timestamp_header=provided_timestamp,
        window_seconds=window_seconds,
        now=now,
    )
