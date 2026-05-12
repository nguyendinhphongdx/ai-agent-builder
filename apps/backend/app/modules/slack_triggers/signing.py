"""Slack request signature verification.

Slack's v0 scheme:
  base = "v0:" + timestamp + ":" + raw_body
  expected = "v0=" + HMAC-SHA256(signing_secret, base).hexdigest()
  compare against X-Slack-Signature header (constant-time).

Replay protection: require X-Slack-Request-Timestamp within
``SLACK_REPLAY_WINDOW_SECONDS`` of server time. Slack's docs
recommend 5 minutes; we mirror.

Spec: https://api.slack.com/authentication/verifying-requests-from-slack
"""
from __future__ import annotations

import hashlib
import hmac
import time

from fastapi import HTTPException, status


class SlackAuthError(HTTPException):
    def __init__(self, code: str, detail: str):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": code, "detail": detail},
        )


def verify(
    *,
    raw_body: bytes,
    signing_secret: str,
    provided_signature: str | None,
    provided_timestamp: str | None,
    window_seconds: int,
    now: float | None = None,
) -> None:
    """Raises SlackAuthError on any verification failure."""
    if not signing_secret:
        raise SlackAuthError(
            "slack_disabled",
            "Slack receiver is not configured (SLACK_SIGNING_SECRET empty).",
        )
    if not provided_timestamp:
        raise SlackAuthError(
            "missing_timestamp",
            "X-Slack-Request-Timestamp header is required.",
        )
    try:
        ts = int(provided_timestamp)
    except ValueError:
        raise SlackAuthError(
            "bad_timestamp_format",
            "X-Slack-Request-Timestamp must be a unix epoch integer.",
        ) from None
    current = now if now is not None else time.time()
    if abs(current - ts) > window_seconds:
        raise SlackAuthError(
            "stale_timestamp",
            f"Timestamp is {int(abs(current - ts))}s away from server time.",
        )

    if not provided_signature:
        raise SlackAuthError(
            "missing_signature",
            "X-Slack-Signature header is required.",
        )
    base = b"v0:" + str(ts).encode() + b":" + raw_body
    expected = (
        "v0="
        + hmac.new(signing_secret.encode(), base, hashlib.sha256).hexdigest()
    )
    if not hmac.compare_digest(expected, provided_signature):
        raise SlackAuthError(
            "signature_mismatch",
            "Slack signature does not match the request body.",
        )
