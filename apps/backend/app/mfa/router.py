"""MFA endpoints — TOTP setup, verify, disable, backup-code regen.

All require an authenticated user. Login-time challenge (when the
user is mid-flow but not yet authenticated) lives in auth/router.py
and reads :func:`mfa.service.verify_login_factor`.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.config import settings
from app.db.session import get_db
from app.mfa import service as mfa_service
from app.models.user import User

router = APIRouter(prefix="/auth/mfa", tags=["mfa"])


# ─── Schemas ───────────────────────────────────────────────────────


class TOTPSetupResponse(BaseModel):
    """Returned by ``/setup`` — gives the FE everything to render a QR
    code and a manual-entry fallback."""

    secret: str
    """Base32 secret — shown once for manual entry into the auth app."""
    provisioning_uri: str
    """``otpauth://`` URL — the FE renders this as a QR code."""


class TOTPVerifySetupRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class TOTPVerifySetupResponse(BaseModel):
    enabled: bool
    backup_codes: list[str]
    """Plaintext backup codes — shown ONCE; user must copy/print them."""


class BackupCodesResponse(BaseModel):
    backup_codes: list[str]


class MfaStatusResponse(BaseModel):
    mfa_enabled: bool
    has_totp_secret: bool
    backup_codes_remaining: int


# ─── Status ────────────────────────────────────────────────────────


@router.get("/status", response_model=MfaStatusResponse)
async def mfa_status(
    current_user: User = Depends(get_current_user),
):
    """Quick UI poll — drives the "MFA enabled" badge on Security tab."""
    return MfaStatusResponse(
        mfa_enabled=bool(current_user.mfa_enabled),
        has_totp_secret=current_user.totp_secret_encrypted is not None,
        backup_codes_remaining=len(current_user.mfa_backup_codes or []),
    )


# ─── TOTP setup ────────────────────────────────────────────────────


@router.post("/totp/setup", response_model=TOTPSetupResponse)
async def totp_setup(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stage a fresh TOTP secret. Does NOT enable MFA — that needs
    a successful ``/totp/verify-setup`` to confirm the user's auth
    app actually accepted the secret."""
    secret = await mfa_service.stage_totp_secret(db, current_user)
    await db.commit()
    uri = mfa_service.provisioning_uri(
        secret, email=current_user.email, issuer=settings.APP_NAME
    )
    return TOTPSetupResponse(secret=secret, provisioning_uri=uri)


@router.post("/totp/verify-setup", response_model=TOTPVerifySetupResponse)
async def totp_verify_setup(
    body: TOTPVerifySetupRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Confirm enrolment with a code from the user's auth app.
    Flips ``mfa_enabled=True`` and surfaces the (one-time) plaintext
    backup codes."""
    ok = await mfa_service.verify_setup_totp(db, current_user, body.code)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid code — try again with a fresh one from your app.",
        )
    # Backup codes were minted during verify_setup; the row now holds
    # *hashes*. Re-mint plaintexts here so we can show them once.
    # (Alternative: have verify_setup_totp return plaintexts + hashes.
    # Chose simplicity — one extra round costs nothing.)
    plaintexts = await mfa_service.regenerate_backup_codes(db, current_user)
    await db.commit()
    return TOTPVerifySetupResponse(enabled=True, backup_codes=plaintexts)


# ─── Backup codes ─────────────────────────────────────────────────


@router.post("/backup-codes/regenerate", response_model=BackupCodesResponse)
async def regenerate_backup_codes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Burn the existing backup codes + mint 10 fresh ones. Use when
    a user thinks their codes leaked, or after consuming most of them."""
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enable MFA first.",
        )
    plaintexts = await mfa_service.regenerate_backup_codes(db, current_user)
    await db.commit()
    return BackupCodesResponse(backup_codes=plaintexts)


# ─── Disable ──────────────────────────────────────────────────────


class DisableRequest(BaseModel):
    """Disable requires a current TOTP code OR a backup code —
    same factor required to *use* MFA must prove the disable request
    is intentional. Prevents account takeover via stolen session cookie."""

    code: str = Field(..., min_length=1)


@router.post("/disable", status_code=status.HTTP_204_NO_CONTENT)
async def disable_mfa(
    body: DisableRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """User-initiated MFA teardown. Admins can force-disable via the
    admin panel (separate endpoint, audit-logged)."""
    if not current_user.mfa_enabled:
        return  # idempotent
    ok = await mfa_service.verify_login_factor(db, current_user, body.code)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid code. Use your authenticator or a backup code.",
        )
    await mfa_service.disable_totp(db, current_user)
    await db.commit()
