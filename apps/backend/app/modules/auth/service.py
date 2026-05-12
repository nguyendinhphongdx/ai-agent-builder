from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.modules.workspaces.service import ensure_personal_workspace
from app.platform.config import settings

# Cấu hình mã hóa mật khẩu sử dụng bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Mã hóa mật khẩu plain text thành bcrypt hash."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str | None) -> bool:
    """So sánh mật khẩu plain text với hash đã lưu. OAuth-only users có
    ``hashed_password = NULL`` — luôn trả False để login bằng password fail."""
    if not hashed:
        return False
    return pwd_context.verify(plain, hashed)


def create_token(data: dict, expires_delta: timedelta) -> str:
    """Tạo JWT token với payload và thời gian hết hạn."""
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(user_id: str) -> str:
    """Tạo access token ngắn hạn để xác thực request."""
    return create_token(
        {"sub": user_id, "type": "access"},
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(
    user_id: str,
    token_version: int = 0,
    remember: bool = False,
) -> str:
    """Tạo refresh token.

    - ``token_version`` phải khớp với ``User.token_version`` lúc refresh;
      password reset bump version → tất cả refresh token cũ invalid.
    - ``remember`` flag nhúng trong payload để /refresh biết re-issue với
      TTL cũ (7d thường, 30d nếu user đã tick Remember me).
    """
    days = (
        settings.REMEMBER_ME_EXPIRE_DAYS
        if remember
        else settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    return create_token(
        {
            "sub": user_id,
            "type": "refresh",
            "ver": token_version,
            "remember": remember,
        },
        timedelta(days=days),
    )


def decode_token(token: str) -> dict | None:
    """Giải mã JWT token, trả về payload hoặc None nếu token không hợp lệ."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Tìm user theo địa chỉ email."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    """Tìm user theo ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    email: str,
    password: str | None,
    full_name: str | None,
    *,
    is_verified: bool = False,
    provision_workspace: bool = True,
) -> User:
    """Tạo user mới. ``password`` có thể ``None`` cho OAuth-only accounts.

    ``provision_workspace=True`` (default) auto-creates a personal
    Org+Workspace+owner-Member and points ``user.default_workspace_id``
    at it. CLIs that bootstrap admin / system users without a personal
    tenant context can pass ``False``.
    """
    user = User(
        email=email,
        hashed_password=hash_password(password) if password else None,
        full_name=full_name,
        is_verified=is_verified,
        verified_at=datetime.now(timezone.utc) if is_verified else None,
    )
    db.add(user)
    await db.flush()
    if provision_workspace:
        await ensure_personal_workspace(db, user)
    await db.refresh(user)
    return user
