"""Phase 2.4 Block 4 — Discord Ed25519 verification.

Build a real Ed25519 keypair, sign a payload, confirm verify
accepts the good signature and rejects every documented failure
mode.
"""
from __future__ import annotations

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import HTTPException

from app.modules.runtime.triggers._signing import (
    verify_discord_ed25519,
)


def verify_signature(
    *,
    public_key_hex: str,
    raw_body: bytes,
    signature_hex: str | None,
    timestamp: str | None,
    now: float | None = None,
) -> None:
    """Test-local wrapper preserving the legacy keyword shape so the
    existing assertions stay readable. Delegates to the shared helper
    with Discord's standard 5-minute replay window."""
    verify_discord_ed25519(
        raw_body=raw_body,
        public_key_hex=public_key_hex,
        signature_hex=signature_hex,
        timestamp_header=timestamp,
        window_seconds=300,
        now=now,
    )


def _make_keys() -> tuple[Ed25519PrivateKey, str]:
    """Returns (private_key, public_key_hex)."""
    priv = Ed25519PrivateKey.generate()
    pub_hex = priv.public_key().public_bytes_raw().hex()
    return priv, pub_hex


def test_verify_signature_happy_path() -> None:
    priv, pub_hex = _make_keys()
    ts = "1000"
    body = b'{"type":1}'
    sig_hex = priv.sign(ts.encode() + body).hex()
    verify_signature(
        public_key_hex=pub_hex,
        raw_body=body,
        signature_hex=sig_hex,
        timestamp=ts,
        now=1100.0,
    )


def test_verify_signature_missing_headers() -> None:
    _, pub_hex = _make_keys()
    with pytest.raises(HTTPException) as exc:
        verify_signature(
            public_key_hex=pub_hex,
            raw_body=b"{}",
            signature_hex=None,
            timestamp="1000",
        )
    assert exc.value.detail["code"] == "missing_signature"


def test_verify_signature_stale_timestamp() -> None:
    priv, pub_hex = _make_keys()
    ts = "1000"
    body = b"{}"
    sig_hex = priv.sign(ts.encode() + body).hex()
    with pytest.raises(HTTPException) as exc:
        verify_signature(
            public_key_hex=pub_hex,
            raw_body=body,
            signature_hex=sig_hex,
            timestamp=ts,
            now=2000.0,
        )
    assert exc.value.detail["code"] == "stale_timestamp"


def test_verify_signature_mismatch() -> None:
    priv, pub_hex = _make_keys()
    other_priv, _ = _make_keys()
    ts = "1000"
    body = b"{}"
    # Sign with the WRONG key.
    bad_sig = other_priv.sign(ts.encode() + body).hex()
    with pytest.raises(HTTPException) as exc:
        verify_signature(
            public_key_hex=pub_hex,
            raw_body=body,
            signature_hex=bad_sig,
            timestamp=ts,
            now=1000.0,
        )
    assert exc.value.detail["code"] == "signature_mismatch"
    # Avoid lint warning on unused priv.
    del priv
