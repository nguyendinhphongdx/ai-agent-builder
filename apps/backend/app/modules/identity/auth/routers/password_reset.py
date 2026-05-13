"""Forgot / reset password — the unauthenticated recovery flow.

In-session password changes live in :mod:`.profile`. This file is
the path the user takes when they're locked out: request a reset
link, then redeem the token with a new password.
"""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.auth._internal import AUTH_PUBLIC_LIMIT
from app.modules.identity.auth.emails import send_password_reset_email
from app.modules.identity.auth.schemas import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.modules.identity.auth.service import (
    get_user_by_email,
    get_user_by_id,
    hash_password,
)
from app.modules.identity.auth.tokens import (
    PURPOSE_PASSWORD_RESET,
    create_and_store,
    redeem,
)
from app.platform.config import settings
from app.platform.db.session import get_db

router = APIRouter()


@router.post("/forgot-password", dependencies=[AUTH_PUBLIC_LIMIT])
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Gửi email reset password. LUÔN trả 200 (không leak email exists)."""
    user = await get_user_by_email(db, body.email)
    if user and user.is_active:
        token = await create_and_store(
            db,
            user_id=user.id,
            purpose=PURPOSE_PASSWORD_RESET,
            ttl=timedelta(minutes=settings.PASSWORD_RESET_TTL_MINUTES),
        )
        await send_password_reset_email(user.email, user.full_name, token)
    return {"sent": True}


@router.post("/reset-password", dependencies=[AUTH_PUBLIC_LIMIT])
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Đặt password mới bằng token. Invalidate mọi session của user."""
    user_id = await redeem(db, body.token, PURPOSE_PASSWORD_RESET)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )

    user = await get_user_by_id(db, str(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )

    user.hashed_password = hash_password(body.new_password)
    user.token_version += 1  # invalidates all outstanding refresh tokens
    await db.flush()

    return {"ok": True}
