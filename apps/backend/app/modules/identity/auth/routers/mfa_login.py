"""Login-time MFA challenge — the second factor verifier.

The user has already passed password verification in
:mod:`.basic` (login) and was handed back a signed challenge
token (``_mint_mfa_challenge_token``); this subrouter accepts that
token + the TOTP/backup code and finishes the login.

Full MFA setup endpoints (enroll, verify-setup, list/disable factors,
backup codes) live in :mod:`app.modules.identity.auth.mfa`. This file
is intentionally only the *login-time* leg.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.auth._internal import (
    AUTH_PUBLIC_LIMIT,
    set_auth_cookies,
)
from app.modules.identity.auth.schemas import (
    AuthResponse,
    MfaVerifyLoginRequest,
    UserResponse,
)
from app.modules.identity.auth.service import get_user_by_id
from app.platform.config import settings
from app.platform.db.session import get_db

router = APIRouter()


# ─── Challenge token helpers ──────────────────────────────────────
# Short-lived signed token issued by /auth/login when the account
# has MFA enabled. Carries (user_id, remember-me flag) so the second
# step can resume the same session intent.

_MFA_CHALLENGE_TTL_SECONDS = 300  # 5 minutes — covers typing the code.


def _mfa_signer():
    from itsdangerous import URLSafeTimedSerializer

    return URLSafeTimedSerializer(settings.SECRET_KEY, salt="mfa-login-challenge")


def mint_mfa_challenge_token(user_id: str, remember: bool) -> str:
    """Used by :mod:`.basic` (login endpoint) when the account requires MFA."""
    return _mfa_signer().dumps({"sub": user_id, "remember": remember})


def _verify_mfa_challenge_token(token: str) -> tuple[str, bool]:
    """Returns (user_id, remember) — raises HTTPException on bad/expired."""
    from itsdangerous import BadSignature, SignatureExpired

    try:
        payload = _mfa_signer().loads(token, max_age=_MFA_CHALLENGE_TTL_SECONDS)
    except SignatureExpired:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="MFA challenge expired — log in again.",
        )
    except BadSignature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA challenge token.",
        )
    return str(payload["sub"]), bool(payload.get("remember", False))


# ─── Endpoint ─────────────────────────────────────────────────────


@router.post(
    "/mfa/verify-login",
    response_model=AuthResponse,
    dependencies=[AUTH_PUBLIC_LIMIT],
)
async def mfa_verify_login(
    body: MfaVerifyLoginRequest,
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Second step of MFA-protected login. Accepts the TOTP code or
    a backup code — same validation path as in-app verification."""
    from app.models.audit_log import ACTOR_USER
    from app.modules.identity.auth.mfa.service import verify_login_factor
    from app.modules.ops.audit import service as audit_service

    user_id, remember_from_token = _verify_mfa_challenge_token(body.mfa_token)
    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active or not user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA challenge token.",
        )

    ok = await verify_login_factor(db, user, body.code)
    if not ok:
        await audit_service.log_event(
            db,
            action="auth.login.mfa_failed",
            actor_user_id=user.id,
            actor_type=ACTOR_USER,
            resource_type="user",
            resource_id=user.id,
            request=request,
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid code.",
        )

    user.last_login_at = datetime.now(timezone.utc)
    set_auth_cookies(
        response,
        str(user.id),
        token_version=user.token_version,
        # If the user ticked "remember me" on the password step we
        # honour it; the challenge token carries the flag forward.
        remember=remember_from_token or body.remember_me,
    )
    await audit_service.log_event(
        db,
        action="auth.login.success",
        actor_user_id=user.id,
        actor_type=ACTOR_USER,
        resource_type="user",
        resource_id=user.id,
        request=request,
        metadata={"mfa": True},
    )
    await db.commit()
    return AuthResponse(user=UserResponse.model_validate(user)).release()
