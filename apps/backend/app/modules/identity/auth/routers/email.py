"""Email management — change primary email + verify on signup.

Two flows in one file because they share the verification-code
machinery and both target the user's email column:

* /me/email + /me/email/confirm   — change primary email (signed-in)
* /verify-email/send + /confirm   — verify the email on a new account
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.modules.identity.auth._internal import AUTH_USER_LIMIT, set_auth_cookies
from app.modules.identity.auth.dependencies import get_current_user
from app.modules.identity.auth.emails import (
    send_email_change_code,
    send_verification_email,
)
from app.modules.identity.auth.schemas import (
    EmailChangeConfirmRequest,
    EmailChangeRequest,
    VerifyEmailConfirmRequest,
)
from app.modules.identity.auth.service import (
    get_user_by_email,
    get_user_by_id,
    verify_password,
)
from app.modules.identity.auth.tokens import (
    PURPOSE_EMAIL_CHANGE,
    PURPOSE_EMAIL_VERIFICATION,
    create_numeric_code,
    redeem,
)
from app.platform.config import settings
from app.platform.db.session import get_db

router = APIRouter()


# ─── Change primary email ─────────────────────────────────────────


@router.post("/me/email", dependencies=[AUTH_USER_LIMIT])
async def request_email_change(
    body: EmailChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Step 1: stage `pending_email`, mail a verification code to the new
    address. The actual swap happens in `confirm_email_change`.

    Requires the current password to defend against a hijacked session
    silently moving the account to an attacker-controlled inbox.
    """
    if not current_user.hashed_password:
        raise HTTPException(
            status_code=400,
            detail="No password set on this account — set one via the forgot-password flow first",
        )
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    new_email = body.new_email.strip().lower()
    if new_email == current_user.email.lower():
        raise HTTPException(status_code=400, detail="That's already your email")

    existing = await get_user_by_email(db, new_email)
    if existing is not None:
        raise HTTPException(status_code=409, detail="That email is already in use")

    current_user.pending_email = new_email
    code = await create_numeric_code(
        db,
        current_user.id,
        PURPOSE_EMAIL_CHANGE,
        timedelta(minutes=settings.EMAIL_VERIFICATION_TTL_MINUTES),
    )
    await db.flush()
    # Send to the *new* address — only the legit owner of the new inbox
    # sees the code, defeating typo + prankster scenarios.
    await send_email_change_code(new_email, current_user.full_name, code)
    return {"sent": True, "to": new_email}


@router.post("/me/email/confirm", dependencies=[AUTH_USER_LIMIT])
async def confirm_email_change(
    body: EmailChangeConfirmRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Step 2: redeem the code, swap email, bump token_version, re-issue
    cookies on this session so the user stays logged in."""
    if not current_user.pending_email:
        raise HTTPException(
            status_code=400,
            detail="No email change in progress — request one first",
        )

    redeemed_user_id = await redeem(db, body.code, PURPOSE_EMAIL_CHANGE)
    if redeemed_user_id != current_user.id:
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    new_email = current_user.pending_email

    # Race: someone else snapped up the address between request + confirm.
    other = await get_user_by_email(db, new_email)
    if other is not None and other.id != current_user.id:
        current_user.pending_email = None
        await db.flush()
        raise HTTPException(status_code=409, detail="That email is already in use")

    current_user.email = new_email
    current_user.pending_email = None
    current_user.token_version = (current_user.token_version or 0) + 1
    await db.flush()

    set_auth_cookies(
        response, str(current_user.id), token_version=current_user.token_version
    )
    return {"email": new_email}


# ─── Initial email verification ───────────────────────────────────


@router.post("/verify-email/send", dependencies=[AUTH_USER_LIMIT])
async def verify_email_send(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Gửi lại email xác thực cho user hiện tại."""
    if current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already verified",
        )

    code = await create_numeric_code(
        db,
        user_id=current_user.id,
        purpose=PURPOSE_EMAIL_VERIFICATION,
        ttl=timedelta(minutes=settings.EMAIL_VERIFICATION_TTL_MINUTES),
    )
    await send_verification_email(current_user.email, current_user.full_name, code)
    return {"sent": True}


@router.post("/verify-email/confirm", dependencies=[AUTH_USER_LIMIT])
async def verify_email_confirm(
    body: VerifyEmailConfirmRequest,
    db: AsyncSession = Depends(get_db),
):
    """Xác thực email bằng code 6 chữ số nhận được qua email."""
    user_id = await redeem(db, body.code, PURPOSE_EMAIL_VERIFICATION)
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

    if not user.is_verified:
        user.is_verified = True
        user.verified_at = datetime.now(timezone.utc)
        await db.flush()

    return {"verified": True}
