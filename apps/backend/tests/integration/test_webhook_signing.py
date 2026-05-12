"""Phase 2.4 Block 1 — HMAC signature + replay verification.

Unit tests for the signing helpers — the router wiring is exercised
by existing webhook flow tests; we just confirm the verifier
behaves correctly across happy path and every documented failure
mode.
"""
from __future__ import annotations

import hashlib
import hmac

import pytest

from app.modules.runtime.triggers.http.signing import (
    WebhookAuthError,
    verify_signature,
    verify_timestamp,
)


def _sign(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_verify_signature_happy_path() -> None:
    body = b'{"event":"push"}'
    secret = "s3cret"
    verify_signature(body, secret=secret, provided=_sign(body, secret))


def test_verify_signature_missing_secret_raises() -> None:
    with pytest.raises(WebhookAuthError) as exc:
        verify_signature(b"{}", secret=None, provided=_sign(b"{}", "x"))
    assert exc.value.detail["code"] == "signing_disabled"


def test_verify_signature_missing_header_raises() -> None:
    with pytest.raises(WebhookAuthError) as exc:
        verify_signature(b"{}", secret="s", provided=None)
    assert exc.value.detail["code"] == "missing_signature"


def test_verify_signature_bad_format_raises() -> None:
    with pytest.raises(WebhookAuthError) as exc:
        verify_signature(b"{}", secret="s", provided="abcdef")
    assert exc.value.detail["code"] == "bad_signature_format"


def test_verify_signature_mismatch_raises() -> None:
    body = b'{"event":"push"}'
    with pytest.raises(WebhookAuthError) as exc:
        verify_signature(body, secret="s", provided=_sign(body, "other"))
    assert exc.value.detail["code"] == "signature_mismatch"


def test_verify_timestamp_inside_window() -> None:
    verify_timestamp(provided="1000", window_seconds=300, now=1200.0)


def test_verify_timestamp_outside_window_raises() -> None:
    with pytest.raises(WebhookAuthError) as exc:
        verify_timestamp(provided="1000", window_seconds=300, now=1500.0)
    assert exc.value.detail["code"] == "stale_timestamp"


def test_verify_timestamp_missing_header_raises() -> None:
    with pytest.raises(WebhookAuthError) as exc:
        verify_timestamp(provided=None, window_seconds=300)
    assert exc.value.detail["code"] == "missing_timestamp"


def test_verify_timestamp_bad_format_raises() -> None:
    with pytest.raises(WebhookAuthError) as exc:
        verify_timestamp(provided="not-an-int", window_seconds=300, now=1000.0)
    assert exc.value.detail["code"] == "bad_timestamp_format"


def test_verify_timestamp_window_zero_is_noop() -> None:
    # Defence in depth — caller skips when 0; even if it doesn't,
    # the verifier must not error.
    verify_timestamp(provided=None, window_seconds=0)
