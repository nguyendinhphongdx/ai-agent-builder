from datetime import datetime, timedelta, timezone

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.emails import (
    send_email_change_code,
    send_password_reset_email,
    send_verification_email,
)
from app.auth.schemas import (
    AuthResponse,
    EmailChangeConfirmRequest,
    EmailChangeRequest,
    ForgotPasswordRequest,
    LoginRequest,
    PasswordChangeRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UserResponse,
    UserUpdateRequest,
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
    PURPOSE_EMAIL_CHANGE,
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


# Avatar upload limits — small enough to fit a profile thumbnail, large
# enough to accept a phone-camera selfie. Bigger payloads return 413.
_AVATAR_MAX_BYTES = 4 * 1024 * 1024  # 4 MiB
_AVATAR_ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp"}


@router.post(
    "/me/avatar",
    response_model=UserResponse,
    dependencies=[_AUTH_USER_LIMIT],
)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a profile avatar. Stores via the configured storage backend
    (local / S3 / GCS) and writes the storage key to ``users.avatar_url``;
    the existing ``release()`` machinery resolves it to a public URL on
    response.

    Old avatar (if any) is left in storage — orphan cleanup is a separate
    concern handled by a periodic job, not a hot-path delete that could
    break a still-loading client view of the previous URL.
    """
    if file.content_type not in _AVATAR_ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Avatar must be PNG/JPEG/WEBP — got {file.content_type or 'unknown'}",
        )
    content = await file.read()
    if len(content) > _AVATAR_MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Avatar exceeds {_AVATAR_MAX_BYTES // (1024 * 1024)} MiB limit",
        )
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    from app.storage.base import generate_storage_key
    from app.storage.factory import get_storage

    storage = get_storage()
    key = generate_storage_key(
        "avatars", current_user.id, file.filename or "avatar.png"
    )
    await storage.upload(key, content, file.content_type)

    current_user.avatar_url = key
    await db.flush()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user).release()


@router.patch("/me", response_model=UserResponse, dependencies=[_AUTH_USER_LIMIT])
async def update_me(
    body: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Self-edit profile. Only fields the user owns — email is changed via
    a separate flow (verification required), role / is_verified stay
    admin-only."""
    if body.full_name is not None:
        current_user.full_name = body.full_name.strip() or None
    if body.avatar_url is not None:
        current_user.avatar_url = body.avatar_url.strip() or None
    await db.flush()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user).release()


def _set_auth_cookies(response: Response, user_id: str, token_version: int) -> None:
    """Re-issue access + refresh cookies on the same response. Used by
    self-change endpoints that bump `token_version` so the active session
    isn't accidentally logged out."""
    access = create_access_token(user_id)
    refresh = create_refresh_token(user_id, token_version=token_version)
    secure = not settings.DEBUG
    response.set_cookie(
        "access_token",
        access,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        "refresh_token",
        refresh,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path=f"{settings.API_PREFIX}/auth",
    )


@router.post(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_AUTH_PUBLIC_LIMIT],
)
async def change_password(
    body: PasswordChangeRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Self-change password while authenticated.

    OAuth-only users (no `hashed_password`) get 400 — they should use
    the forgot-password flow first to set one. Bumps `token_version` so
    every other refresh session is invalidated immediately; the active
    tab gets fresh cookies in the same response so it doesn't log out.
    """
    if not current_user.hashed_password:
        raise HTTPException(
            status_code=400,
            detail="No password set on this account — use the forgot-password flow first",
        )
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=400, detail="New password must differ from current"
        )

    current_user.hashed_password = hash_password(body.new_password)
    current_user.token_version = (current_user.token_version or 0) + 1
    await db.flush()

    _set_auth_cookies(response, str(current_user.id), current_user.token_version)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/me/email", dependencies=[_AUTH_USER_LIMIT])
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


@router.post("/me/email/confirm", dependencies=[_AUTH_USER_LIMIT])
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

    _set_auth_cookies(response, str(current_user.id), current_user.token_version)
    return {"email": new_email}


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
