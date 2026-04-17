import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.schemas.base import AppBaseModel


class RegisterRequest(BaseModel):
    """Schema yêu cầu đăng ký tài khoản mới."""
    email: EmailStr
    password: str
    full_name: str | None = None


class LoginRequest(BaseModel):
    """Schema yêu cầu đăng nhập."""
    email: EmailStr
    password: str


class UserResponse(AppBaseModel):
    """Schema trả về thông tin user (không bao gồm mật khẩu)."""
    __storage_fields__ = ("avatar_url",)

    id: uuid.UUID
    email: str
    full_name: str | None
    avatar_url: str | None
    is_active: bool
    created_at: datetime


class AuthResponse(AppBaseModel):
    """Schema trả về sau khi đăng ký/đăng nhập thành công."""
    user: UserResponse
    message: str = "ok"

    def release(self) -> dict:
        data = super().release()
        data["user"] = self.user.release()
        return data
