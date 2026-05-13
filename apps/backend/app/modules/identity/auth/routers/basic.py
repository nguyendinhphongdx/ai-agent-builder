"""Auth lifecycle — register / login / refresh / logout.

The "skeleton" of authenticated sessions: create an account, prove
identity, rotate tokens, drop the cookies. Email verification +
password management live in sibling subrouters.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.auth._internal import AUTH_PUBLIC_LIMIT, set_auth_cookies
from app.modules.identity.auth.emails import send_verification_email
from app.modules.identity.auth.routers.mfa_login import mint_mfa_challenge_token
from app.modules.identity.auth.schemas import (
    AuthResponse,
    LoginRequest,
    MfaChallengeResponse,
    RegisterRequest,
    UserResponse,
)
from app.modules.identity.auth.service import (
    create_user,
    decode_token,
    get_user_by_email,
    get_user_by_id,
    verify_password,
)
from app.modules.identity.auth.tokens import (
    PURPOSE_EMAIL_VERIFICATION,
    create_numeric_code,
)
from app.platform.config import settings
from app.platform.db.session import get_db

router = APIRouter()


# ─── Register ──────────────────────────────────────────────────────


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[AUTH_PUBLIC_LIMIT],
)
async def register(
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Tạo tài khoản mới, gửi email xác thực, auto-login."""
    existing = await get_user_by_email(db, body.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = await create_user(db, body.email, body.password, body.full_name)

    # Issue 6-digit verification code + email it (fire-and-forget)
    code = await create_numeric_code(
        db,
        user_id=user.id,
        purpose=PURPOSE_EMAIL_VERIFICATION,
        ttl=timedelta(minutes=settings.EMAIL_VERIFICATION_TTL_MINUTES),
    )
    await send_verification_email(user.email, user.full_name, code)

    set_auth_cookies(response, str(user.id), token_version=user.token_version)
    return AuthResponse(user=UserResponse.model_validate(user)).release()


# ─── Login ─────────────────────────────────────────────────────────


@router.post("/login", dependencies=[AUTH_PUBLIC_LIMIT])
async def login(
    body: LoginRequest,
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Xác thực email + password.

    If ``user.mfa_enabled``, returns a ``MfaChallengeResponse`` instead
    of session cookies — caller follows up with /auth/mfa/verify-login.
    """
    from app.models.audit_log import ACTOR_SYSTEM, ACTOR_USER
    from app.modules.ops.audit import service as audit_service

    user = await get_user_by_email(db, body.email)
    if not user or not verify_password(body.password, user.hashed_password):
        # Log the failed attempt — no actor user id (could be probing
        # for valid emails). Email kept in metadata so security can
        # spot credential stuffing patterns.
        await audit_service.log_event(
            db,
            action="auth.login.failed",
            actor_type=ACTOR_SYSTEM,
            request=request,
            metadata={"email": body.email[:255]},
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        await audit_service.log_event(
            db,
            action="auth.login.disabled",
            actor_user_id=user.id,
            actor_type=ACTOR_USER,
            resource_type="user",
            resource_id=user.id,
            request=request,
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Second factor required — issue short-lived challenge token, NO
    # session cookies yet. Browser must call /auth/mfa/verify-login.
    if user.mfa_enabled:
        await audit_service.log_event(
            db,
            action="auth.login.mfa_required",
            actor_user_id=user.id,
            actor_type=ACTOR_USER,
            resource_type="user",
            resource_id=user.id,
            request=request,
        )
        await db.commit()
        return MfaChallengeResponse(
            mfa_token=mint_mfa_challenge_token(str(user.id), body.remember_me),
        ).model_dump()

    user.last_login_at = datetime.now(timezone.utc)
    set_auth_cookies(
        response,
        str(user.id),
        token_version=user.token_version,
        remember=body.remember_me,
    )
    await audit_service.log_event(
        db,
        action="auth.login.success",
        actor_user_id=user.id,
        actor_type=ACTOR_USER,
        resource_type="user",
        resource_id=user.id,
        request=request,
    )
    await db.commit()
    return AuthResponse(user=UserResponse.model_validate(user)).release()


# ─── Refresh ───────────────────────────────────────────────────────


@router.post(
    "/refresh", response_model=AuthResponse, dependencies=[AUTH_PUBLIC_LIMIT]
)
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Làm mới access + refresh token. Giữ nguyên TTL remember của lần login ban đầu."""
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token",
        )

    payload = decode_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = await get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # token_version mismatch → all sessions invalidated (eg. after password reset)
    if int(payload.get("ver", 0)) != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session invalidated",
        )

    remember = bool(payload.get("remember", False))
    set_auth_cookies(
        response,
        str(user.id),
        token_version=user.token_version,
        remember=remember,
    )
    return AuthResponse(user=UserResponse.model_validate(user)).release()


# ─── Logout ────────────────────────────────────────────────────────


@router.post("/logout")
async def logout(
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Đăng xuất bằng cách xóa cookie access_token và refresh_token.

    Logs the event when we can identify the user; an already-expired
    session that calls logout just gets cookies cleared with no audit
    row (nothing meaningful to record).
    """
    from app.models.audit_log import ACTOR_USER
    from app.modules.ops.audit import service as audit_service

    # Try to resolve the user from the access cookie WITHOUT raising —
    # logout must succeed even when the token is bad/expired.
    user_id: uuid.UUID | None = None
    cookie = request.cookies.get("access_token")
    if cookie:
        payload = decode_token(cookie)
        if payload and payload.get("type") == "access":
            try:
                user_id = uuid.UUID(str(payload.get("sub")))
            except (ValueError, TypeError):
                user_id = None

    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path=f"{settings.API_PREFIX}/auth/refresh")

    if user_id is not None:
        await audit_service.log_event(
            db,
            action="auth.logout",
            actor_user_id=user_id,
            actor_type=ACTOR_USER,
            resource_type="user",
            resource_id=user_id,
            request=request,
        )
        await db.commit()
    return {"message": "Logged out"}
