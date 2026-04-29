from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.emails import (
    send_password_reset_email,
    send_verification_email,
)
from app.auth.schemas import (
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UserResponse,
    VerifyEmailConfirmRequest,
)
from app.auth.service import (
    create_access_token,
    create_refresh_token,
    create_user,
    decode_token,
    get_user_by_email,
    get_user_by_id,
    hash_password,
    verify_password,
)
from app.auth.tokens import (
    PURPOSE_EMAIL_VERIFICATION,
    PURPOSE_PASSWORD_RESET,
    create_and_store,
    create_numeric_code,
    redeem,
)
from app.config import settings
from app.db.session import get_db
from app.models.user import User

from app.rate_limit import make_limit

# Public auth endpoints are the most-attacked surface — keep per-IP limits
# strict so a credential-stuffing attempt costs the attacker. Internal
# (authenticated) endpoints get more headroom via per-user keys.
_AUTH_PUBLIC_LIMIT = Depends(make_limit("auth-public", 30))   # login/register/refresh/forgot
_AUTH_USER_LIMIT = Depends(make_limit("auth-user", 60))       # logout/verify/reset

router = APIRouter(prefix="/auth", tags=["auth"])


# ─── Cookie helpers ────────────────────────────────────────────────

def _set_auth_cookies(
    response: Response,
    user_id: str,
    *,
    token_version: int = 0,
    remember: bool = False,
) -> None:
    """Gán access_token + refresh_token vào HTTP-only cookie.

    - access_token cookie: path=/, TTL từ ACCESS_TOKEN_EXPIRE_MINUTES
    - refresh_token cookie: path=/api/auth/refresh, TTL phụ thuộc ``remember``
    """
    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id, token_version, remember=remember)

    refresh_days = (
        settings.REMEMBER_ME_EXPIRE_DAYS
        if remember
        else settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=refresh_days * 86400,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        path=f"{settings.API_PREFIX}/auth/refresh",
    )


# ─── Register ──────────────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED, dependencies=[_AUTH_PUBLIC_LIMIT])
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

    _set_auth_cookies(response, str(user.id), token_version=user.token_version)
    return AuthResponse(user=UserResponse.model_validate(user)).release()


# ─── Login ─────────────────────────────────────────────────────────

@router.post("/login", response_model=AuthResponse, dependencies=[_AUTH_PUBLIC_LIMIT])
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Xác thực email + password. Unverified users vẫn login được."""
    user = await get_user_by_email(db, body.email)
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    user.last_login_at = datetime.now(timezone.utc)
    _set_auth_cookies(
        response,
        str(user.id),
        token_version=user.token_version,
        remember=body.remember_me,
    )
    return AuthResponse(user=UserResponse.model_validate(user)).release()


# ─── Refresh ───────────────────────────────────────────────────────

@router.post("/refresh", response_model=AuthResponse, dependencies=[_AUTH_PUBLIC_LIMIT])
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
    _set_auth_cookies(
        response,
        str(user.id),
        token_version=user.token_version,
        remember=remember,
    )
    return AuthResponse(user=UserResponse.model_validate(user)).release()


# ─── Logout / Me ──────────────────────────────────────────────────

@router.post("/logout")
async def logout(response: Response):
    """Đăng xuất bằng cách xóa cookie access_token và refresh_token."""
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path=f"{settings.API_PREFIX}/auth/refresh")
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Lấy thông tin user hiện tại đang đăng nhập."""
    return UserResponse.model_validate(current_user).release()


# ─── Email verification ───────────────────────────────────────────

@router.post("/verify-email/send", dependencies=[_AUTH_USER_LIMIT])
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


@router.post("/verify-email/confirm", dependencies=[_AUTH_USER_LIMIT])
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


# ─── Forgot / Reset password ──────────────────────────────────────

@router.post("/forgot-password", dependencies=[_AUTH_PUBLIC_LIMIT])
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


@router.post("/reset-password", dependencies=[_AUTH_PUBLIC_LIMIT])
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
