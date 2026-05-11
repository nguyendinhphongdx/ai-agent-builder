"""Phase 2.4 Block 3 — Slack signature verification.

The receiver wiring is exercised by integration tests; this just
nails down the verifier's contract against Slack's documented
v0 scheme.
"""
from __future__ import annotations

import hashlib
import hmac

import pytest

from app.slack_triggers.signing import SlackAuthError, verify


def _make_sig(secret: str, ts: int, body: bytes) -> str:
    base = b"v0:" + str(ts).encode() + b":" + body
    return "v0=" + hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()


def test_verify_happy_path() -> None:
    body = b'{"type":"event_callback"}'
    secret = "slack-secret"
    sig = _make_sig(secret, 1000, body)
    verify(
        raw_body=body,
        signing_secret=secret,
        provided_signature=sig,
        provided_timestamp="1000",
        window_seconds=300,
        now=1100.0,
    )


def test_verify_disabled_when_secret_empty() -> None:
    with pytest.raises(SlackAuthError) as exc:
        verify(
            raw_body=b"{}",
            signing_secret="",
            provided_signature="v0=x",
            provided_timestamp="1000",
            window_seconds=300,
            now=1000.0,
        )
    assert exc.value.detail["code"] == "slack_disabled"


def test_verify_missing_timestamp() -> None:
    with pytest.raises(SlackAuthError) as exc:
        verify(
            raw_body=b"{}",
            signing_secret="s",
            provided_signature="v0=x",
            provided_timestamp=None,
            window_seconds=300,
        )
    assert exc.value.detail["code"] == "missing_timestamp"


def test_verify_stale_timestamp() -> None:
    body = b"{}"
    secret = "s"
    sig = _make_sig(secret, 1000, body)
    with pytest.raises(SlackAuthError) as exc:
        verify(
            raw_body=body,
            signing_secret=secret,
            provided_signature=sig,
            provided_timestamp="1000",
            window_seconds=300,
            now=2000.0,
        )
    assert exc.value.detail["code"] == "stale_timestamp"


def test_verify_signature_mismatch() -> None:
    body = b"hello"
    secret = "s"
    bad_sig = _make_sig("wrong", 1000, body)
    with pytest.raises(SlackAuthError) as exc:
        verify(
            raw_body=body,
            signing_secret=secret,
            provided_signature=bad_sig,
            provided_timestamp="1000",
            window_seconds=300,
            now=1000.0,
        )
    assert exc.value.detail["code"] == "signature_mismatch"
