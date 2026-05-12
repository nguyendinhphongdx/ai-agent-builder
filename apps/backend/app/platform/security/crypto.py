"""Fernet helpers for at-rest secrets.

Used by:
- ``ai_credentials.service`` for LLM provider keys
- ``payouts.service`` for author MoMo merchant credentials

The key lives in ``settings.ENCRYPTION_KEY``. Rotating it requires
re-encrypting every existing secret (out-of-scope for this helper).
"""
from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.platform.config import settings


def _fernet() -> Fernet:
    if not settings.ENCRYPTION_KEY:
        raise RuntimeError(
            "ENCRYPTION_KEY is not set. Generate one with: "
            'python -c "import secrets,base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"'
        )
    return Fernet(settings.ENCRYPTION_KEY.encode())


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a secret. Returns base64-encoded ciphertext."""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    """Decrypt a secret previously produced by :func:`encrypt_secret`.

    Raises ``ValueError`` on tampered / corrupt input — the caller can
    surface that as a 500 since it indicates DB corruption, not user error.
    """
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise ValueError(
            "Failed to decrypt secret — invalid or corrupt ciphertext"
        ) from exc


def mask_secret(plaintext: str) -> str:
    """Display-safe preview — first 6 + last 4 chars with dots in between.

    Short strings (≤10) are fully masked since splitting would leak
    almost all of them.
    """
    if len(plaintext) <= 10:
        return "****"
    return plaintext[:6] + "•" * 8 + plaintext[-4:]
