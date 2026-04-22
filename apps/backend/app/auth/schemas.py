import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.base import AppBaseModel


class RegisterRequest(BaseModel):
    """Schema yêu cầu đăng ký tài khoản mới."""
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str | None = None


class LoginRequest(BaseModel):
    """Schema yêu cầu đăng nhập."""
    email: EmailStr
    password: str
    remember_me: bool = False


class ForgotPasswordRequest(BaseModel):
    """Schema for password-reset link request. Response is always 200."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Redeem a password-reset token and set a new password."""
    token: str
    new_password: str = Field(min_length=8)


class VerifyEmailConfirmRequest(BaseModel):
    """Redeem an email-verification code."""
    code: str = Field(min_length=4, max_length=12)


class UserResponse(AppBaseModel):
    """Schema trả về thông tin user (không bao gồm mật khẩu)."""
    __storage_fields__ = ("avatar_url",)

    id: uuid.UUID
    email: str
    full_name: str | None
    avatar_url: str | None
    is_active: bool
    is_verified: bool
    verified_at: datetime | None = None
    created_at: datetime


class AuthResponse(AppBaseModel):
    """Schema trả về sau khi đăng ký/đăng nhập thành công."""
    user: UserResponse
    message: str = "ok"

    def release(self) -> dict:
        data = super().release()
        data["user"] = self.user.release()
        return data
