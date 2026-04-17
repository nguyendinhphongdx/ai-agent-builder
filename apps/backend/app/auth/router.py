from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, Cookie, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.schemas import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from app.auth.service import (
    create_access_token,
    create_refresh_token,
    create_user,
    decode_token,
    get_user_by_email,
    get_user_by_id,
    verify_password,
)
from app.config import settings
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookies(response: Response, user_id: str) -> None:
    """Gán access_token và refresh_token vào HTTP-only cookie.

    - access_token: gửi với mọi request, path="/"
    - refresh_token: chỉ gửi khi gọi endpoint refresh, path="/api/auth/refresh"
    """
    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)

    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/api/auth/refresh",
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(  # Đăng ký tài khoản mới, kiểm tra email trùng trước khi tạo
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    existing = await get_user_by_email(db, body.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = await create_user(db, body.email, body.password, body.full_name)
    _set_auth_cookies(response, str(user.id))

    return AuthResponse(user=UserResponse.model_validate(user)).release()


@router.post("/login", response_model=AuthResponse)
async def login(  # Đăng nhập, xác thực email + mật khẩu và cấp token
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    # Tìm user và xác thực mật khẩu
    user = await get_user_by_email(db, body.email)
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Kiểm tra tài khoản có bị vô hiệu hóa không
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Cập nhật thời gian đăng nhập lần cuối
    user.last_login_at = datetime.now(timezone.utc)
    _set_auth_cookies(response, str(user.id))

    return AuthResponse(user=UserResponse.model_validate(user)).release()


@router.post("/refresh", response_model=AuthResponse)
async def refresh(  # Làm mới access token bằng refresh token từ cookie
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
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

    _set_auth_cookies(response, str(user.id))

    return AuthResponse(user=UserResponse.model_validate(user)).release()


@router.post("/logout")
async def logout(response: Response):
    """Đăng xuất bằng cách xóa cookie access_token và refresh_token."""
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/auth/refresh")
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Lấy thông tin user hiện tại đang đăng nhập."""
    return UserResponse.model_validate(current_user).release()
