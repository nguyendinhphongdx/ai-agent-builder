"""Self-service profile endpoints — /me read/edit, avatar, password.

Owns the things the authenticated user changes about *themselves*.
Email address has its own flow (verification required) in
:mod:`.email`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.modules.identity.auth._internal import (
    AUTH_PUBLIC_LIMIT,
    AUTH_USER_LIMIT,
    set_auth_cookies,
)
from app.modules.identity.auth.dependencies import get_current_user
from app.modules.identity.auth.schemas import (
    PasswordChangeRequest,
    UserResponse,
    UserUpdateRequest,
)
from app.modules.identity.auth.service import hash_password, verify_password
from app.platform.db.session import get_db

router = APIRouter()


# ─── Read ──────────────────────────────────────────────────────────


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Lấy thông tin user hiện tại đang đăng nhập."""
    return UserResponse.model_validate(current_user).release()


# ─── Avatar upload ────────────────────────────────────────────────

# Small enough to fit a profile thumbnail, large enough to accept a
# phone-camera selfie. Bigger payloads return 413.
_AVATAR_MAX_BYTES = 4 * 1024 * 1024  # 4 MiB
_AVATAR_ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp"}


@router.post(
    "/me/avatar",
    response_model=UserResponse,
    dependencies=[AUTH_USER_LIMIT],
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

    from app.platform.storage.base import generate_storage_key
    from app.platform.storage.factory import get_storage

    storage = get_storage()
    key = generate_storage_key(
        "avatars", current_user.id, file.filename or "avatar.png"
    )
    await storage.upload(key, content, file.content_type)

    current_user.avatar_url = key
    await db.flush()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user).release()


# ─── Profile edit ──────────────────────────────────────────────────


@router.patch("/me", response_model=UserResponse, dependencies=[AUTH_USER_LIMIT])
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


# ─── Password change ──────────────────────────────────────────────


@router.post(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[AUTH_PUBLIC_LIMIT],
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

    set_auth_cookies(
        response, str(current_user.id), token_version=current_user.token_version
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
