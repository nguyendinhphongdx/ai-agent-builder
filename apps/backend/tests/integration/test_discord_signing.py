"""Phase 2.4 Block 4 — Discord Ed25519 verification.

Build a real Ed25519 keypair, sign a payload, confirm verify
accepts the good signature and rejects every documented failure
mode.
"""
from __future__ import annotations

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import HTTPException

from app.modules.discord_triggers.service import verify_signature


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
