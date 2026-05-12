"""MFA — TOTP enrolment, verification, backup-code generation.

State machine:
  not enrolled        totp_secret_encrypted IS NULL, mfa_enabled=False
  pending enrolment   secret stored, mfa_enabled=False until a verify
                      call succeeds. UI typically gates this on
                      ``setup_totp`` then ``verify_setup_totp``.
  enrolled            mfa_enabled=True. Login flow demands a TOTP code.

The pending state lets us show "Confirm with a code from your app"
before we trust the user's authenticator copy was correct — turning
mfa_enabled on prematurely would lock the user out if they typed
the secret in wrong.
"""
from __future__ import annotations

import hashlib
import secrets
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.platform.security.crypto import decrypt_secret, encrypt_secret

if TYPE_CHECKING:
    pass


_BACKUP_CODE_COUNT = 10
_BACKUP_CODE_BYTES = 6  # 8 chars after base32 — easy to type


def _pyotp():
    """Lazy import — keeps pyotp optional for env that skip MFA install."""
    try:
        import pyotp as _mod
    except ImportError as exc:  # pragma: no cover — install issue
        raise RuntimeError(
            "pyotp not installed — TOTP MFA is unavailable. "
            "pip install pyotp."
        ) from exc
    return _mod


# ─── TOTP setup + verify ──────────────────────────────────────────


def generate_totp_secret() -> str:
    """Return a fresh base32-encoded TOTP secret. Caller stores
    encrypted on the User row and shows once in the QR code."""
    return _pyotp().random_base32()


def provisioning_uri(secret: str, *, email: str, issuer: str) -> str:
    """Build the ``otpauth://`` URI for QR-encoding in the FE.

    issuer is what authenticator apps render as the account label —
    use ``settings.APP_NAME`` so users see "AgentForge: alice@…".
    """
    return _pyotp().totp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)


def verify_totp(secret: str, code: str, *, valid_window: int = 1) -> bool:
    """True iff ``code`` matches the current/adjacent 30s window.

    ``valid_window=1`` accepts the previous + next slot in addition
    to the current one — covers clock drift between user and server.
    """
    if not code or not code.isdigit() or len(code) != 6:
        return False
    return _pyotp().totp.TOTP(secret).verify(code, valid_window=valid_window)


async def stage_totp_secret(db: AsyncSession, user: User) -> str:
    """Generate + encrypt + persist a TOTP secret for ``user``. Does
    NOT flip ``mfa_enabled`` — caller must verify the user can read
    the secret from their authenticator first via ``verify_setup_totp``."""
    secret = generate_totp_secret()
    user.totp_secret_encrypted = encrypt_secret(secret)
    await db.flush()
    return secret


async def verify_setup_totp(
    db: AsyncSession, user: User, code: str
) -> bool:
    """Confirm enrolment by checking a code against the staged secret.

    On success: flip ``mfa_enabled=True`` and mint backup codes.
    On failure: nothing happens — caller can retry without resetting.
    """
    if not user.totp_secret_encrypted:
        return False
    secret = decrypt_secret(user.totp_secret_encrypted)
    if not verify_totp(secret, code):
        return False
    user.mfa_enabled = True
    # Backup codes are issued once at enrolment. Re-running setup
    # regenerates the secret and clears codes — same flow as
    # "re-enrol from a new phone".
    user.mfa_backup_codes = _generate_backup_code_hashes()
    await db.flush()
    return True


async def disable_totp(db: AsyncSession, user: User) -> None:
    """Tear down all MFA factors. Used by the user on their own
    request and by admins for emergency recovery."""
    user.totp_secret_encrypted = None
    user.mfa_enabled = False
    user.mfa_backup_codes = []
    await db.flush()


# ─── Backup codes ─────────────────────────────────────────────────


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _mint_backup_code() -> str:
    """8-char alphanumeric — easy to read off a printed page."""
    raw = secrets.token_bytes(_BACKUP_CODE_BYTES)
    # base32 → no ambiguous chars; trim padding.
    import base64
    return base64.b32encode(raw).decode("ascii").rstrip("=")[:8]


def _generate_backup_code_hashes() -> list[str]:
    """Internal — produces the hashed list for the user row. Plaintext
    codes are surfaced to the user via :func:`generate_new_backup_codes`."""
    return [_hash_code(_mint_backup_code()) for _ in range(_BACKUP_CODE_COUNT)]


async def regenerate_backup_codes(
    db: AsyncSession, user: User
) -> list[str]:
    """Replace existing backup codes with a fresh batch. Returns the
    plaintext codes — caller MUST show them to the user immediately
    and never store them. Old codes are invalidated atomically by the
    overwrite.
    """
    plaintexts = [_mint_backup_code() for _ in range(_BACKUP_CODE_COUNT)]
    user.mfa_backup_codes = [_hash_code(p) for p in plaintexts]
    await db.flush()
    return plaintexts


async def consume_backup_code(
    db: AsyncSession, user: User, code: str
) -> bool:
    """Check + burn a backup code in one step. Returns True iff the
    code was in the user's remaining set; the matching hash is removed
    so it can't be reused."""
    if not code:
        return False
    digest = _hash_code(code.strip().upper())
    if digest not in (user.mfa_backup_codes or []):
        return False
    user.mfa_backup_codes = [h for h in user.mfa_backup_codes if h != digest]
    await db.flush()
    return True


# ─── Login-time check ─────────────────────────────────────────────


async def verify_login_factor(
    db: AsyncSession, user: User, code: str
) -> bool:
    """Accept either a 6-digit TOTP code or an 8-char backup code.

    Backup codes are single-use; TOTP can be reused indefinitely (the
    30s window enforces freshness).
    """
    code = (code or "").strip()
    if code.isdigit() and len(code) == 6:
        if not user.totp_secret_encrypted:
            return False
        secret = decrypt_secret(user.totp_secret_encrypted)
        return verify_totp(secret, code)
    # Treat anything else as a backup code attempt.
    return await consume_backup_code(db, user, code)
