"""Shared signature + replay-window verification helpers.

Each webhook trigger has its own quirks but the underlying crypto
boils down to four shapes. Each helper raises ``TriggerAuthError``
(401 with structured body) on any failure so callers don't need
to invent their own error class.

  GitHub v0 (HTTP trigger)
    base       = raw_body
    signature  = "sha256=" + HMAC-SHA256(secret, base).hex()
    header     = X-Hub-Signature-256
    + optional timestamp replay header

  Slack v0
    base       = b"v0:" + ts + b":" + raw_body
    signature  = "v0=" + HMAC-SHA256(secret, base).hex()
    headers    = X-Slack-Signature + X-Slack-Request-Timestamp
    timestamp replay REQUIRED (5min window per Slack docs)

  Teams HMAC
    base       = raw_body
    signature  = base64(HMAC-SHA256(base64_decode(secret), base))
    header     = Authorization: HMAC <base64>
    no timestamp

  Discord Ed25519
    base       = ts.encode() + raw_body
    signature  = hex(ed25519_sign(private_key, base))
    headers    = X-Signature-Ed25519 + X-Signature-Timestamp
    asymmetric — verifying party holds the *public* key
    timestamp replay REQUIRED (5min window per Discord docs)

All four collapse to: (raw_body, secret_or_pubkey, provided_sig,
optional_ts, optional_window) → ok|raise.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time

from fastapi import HTTPException, status

__all__ = [
    "TriggerAuthError",
    "verify_timestamp",
    "verify_github_v0",
    "verify_slack_v0",
    "verify_teams_hmac",
    "verify_discord_ed25519",
]


class TriggerAuthError(HTTPException):
    """401 with structured ``{code, detail}`` body so the FE / sender
    can branch on it without parsing English."""

    def __init__(self, code: str, detail: str):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": code, "detail": detail},
        )


# ─── Timestamp replay-window check ─────────────────────────────────


def verify_timestamp(
    provided: str | None,
    *,
    window_seconds: int,
    now: float | None = None,
    header_name: str = "X-Timestamp",
) -> int:
    """Parse + bounds-check a unix-epoch timestamp string.

    Returns the parsed int (callers usually need it for the signature
    base string). Raises ``TriggerAuthError`` on missing / malformed /
    stale. ``window_seconds <= 0`` disables the check entirely (caller
    decides default).
    """
    if window_seconds <= 0:
        if provided is None:
            return 0
        try:
            return int(provided)
        except ValueError:
            return 0

    if not provided:
        raise TriggerAuthError(
            "missing_timestamp",
            f"Header {header_name} is required.",
        )
    try:
        ts = int(provided)
    except ValueError:
        raise TriggerAuthError(
            "bad_timestamp_format",
            f"Header {header_name} must be a unix epoch integer.",
        ) from None
    current = now if now is not None else time.time()
    delta = abs(current - ts)
    if delta > window_seconds:
        raise TriggerAuthError(
            "stale_timestamp",
            f"Timestamp is {int(delta)}s away from server time "
            f"(window: {window_seconds}s).",
        )
    return ts


# ─── HMAC-SHA256 variants ──────────────────────────────────────────


def _ct_eq(expected: str, provided: str) -> bool:
    """Constant-time string compare. Wraps hmac.compare_digest so call
    sites don't repeat the encode-to-bytes dance everywhere."""
    return hmac.compare_digest(expected, provided)


def verify_github_v0(
    *,
    raw_body: bytes,
    secret: str | None,
    signature_header: str | None,
    timestamp_header: str | None = None,
    window_seconds: int = 0,
    ts_header_name: str = "X-Webhook-Timestamp",
) -> None:
    """GitHub-style: ``X-Hub-Signature-256: sha256=<hex>`` of HMAC over
    raw body. Timestamp replay is opt-in.
    """
    if not secret:
        raise TriggerAuthError(
            "signing_disabled",
            "No signing secret configured for this trigger.",
        )
    if not signature_header:
        raise TriggerAuthError(
            "missing_signature",
            "Header X-Hub-Signature-256 is required.",
        )
    if not signature_header.startswith("sha256="):
        raise TriggerAuthError(
            "bad_signature_format",
            "Header X-Hub-Signature-256 must start with 'sha256='.",
        )
    if window_seconds > 0:
        verify_timestamp(
            timestamp_header,
            window_seconds=window_seconds,
            header_name=ts_header_name,
        )

    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if not _ct_eq(expected, signature_header[len("sha256=") :]):
        raise TriggerAuthError(
            "signature_mismatch",
            "Signature does not match the request body.",
        )


def verify_slack_v0(
    *,
    raw_body: bytes,
    signing_secret: str | None,
    signature_header: str | None,
    timestamp_header: str | None,
    window_seconds: int = 300,
    now: float | None = None,
) -> None:
    """Slack's v0 scheme. Timestamp is mandatory because it's part of
    the base string — there's no useful "skip replay" mode.
    """
    if not signing_secret:
        raise TriggerAuthError(
            "slack_disabled",
            "Slack receiver is not configured (SLACK_SIGNING_SECRET empty).",
        )
    ts = verify_timestamp(
        timestamp_header,
        window_seconds=window_seconds,
        now=now,
        header_name="X-Slack-Request-Timestamp",
    )
    if not signature_header:
        raise TriggerAuthError(
            "missing_signature",
            "Header X-Slack-Signature is required.",
        )
    base = b"v0:" + str(ts).encode() + b":" + raw_body
    expected = (
        "v0="
        + hmac.new(signing_secret.encode(), base, hashlib.sha256).hexdigest()
    )
    if not _ct_eq(expected, signature_header):
        raise TriggerAuthError(
            "signature_mismatch",
            "Slack signature does not match the request body.",
        )


def verify_teams_hmac(
    *,
    raw_body: bytes,
    secret_b64: str | None,
    authorization_header: str | None,
) -> None:
    """Microsoft Teams Outgoing Webhook: ``Authorization: HMAC <b64>``
    of HMAC-SHA256 over the raw body. Secret stored base64-encoded;
    we decode before HMAC. No timestamp.
    """
    if not authorization_header or not authorization_header.startswith("HMAC "):
        raise TriggerAuthError(
            "missing_signature",
            "Authorization: HMAC <signature> header is required.",
        )
    if not secret_b64:
        raise TriggerAuthError(
            "signing_disabled",
            "Teams trigger has no HMAC secret configured.",
        )
    provided_b64 = authorization_header[len("HMAC ") :].strip()
    try:
        secret_bytes = base64.b64decode(secret_b64)
    except (ValueError, base64.binascii.Error) as exc:  # type: ignore[attr-defined]
        raise TriggerAuthError(
            "bad_secret",
            "Trigger HMAC secret is malformed (not valid base64).",
        ) from exc
    expected = base64.b64encode(
        hmac.new(secret_bytes, raw_body, hashlib.sha256).digest()
    ).decode()
    if not _ct_eq(expected, provided_b64):
        raise TriggerAuthError(
            "signature_mismatch",
            "HMAC does not match the request body.",
        )


# ─── Asymmetric (Discord Ed25519) ──────────────────────────────────


def verify_discord_ed25519(
    *,
    raw_body: bytes,
    public_key_hex: str | None,
    signature_hex: str | None,
    timestamp_header: str | None,
    window_seconds: int = 300,
    now: float | None = None,
) -> None:
    """Discord interactions endpoint: Ed25519 over ``ts || body``.
    Public key comes from the Discord application dashboard; the
    verifier holds the *public* key (no shared secret).
    """
    # Lazy import — cryptography is already a backend dep, but keep
    # the helper import-light for tests that mock or skip Discord.
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PublicKey,
    )

    if not public_key_hex:
        raise TriggerAuthError(
            "signing_disabled",
            "Discord trigger has no public key configured.",
        )
    if not signature_hex or not timestamp_header:
        raise TriggerAuthError(
            "missing_signature",
            "Headers X-Signature-Ed25519 + X-Signature-Timestamp are required.",
        )
    # Replay window check FIRST — cheap, before the asymmetric crypto.
    verify_timestamp(
        timestamp_header,
        window_seconds=window_seconds,
        now=now,
        header_name="X-Signature-Timestamp",
    )
    try:
        key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
        key.verify(
            bytes.fromhex(signature_hex),
            timestamp_header.encode() + raw_body,
        )
    except (InvalidSignature, ValueError) as exc:
        raise TriggerAuthError(
            "signature_mismatch",
            "Ed25519 verification failed.",
        ) from exc
