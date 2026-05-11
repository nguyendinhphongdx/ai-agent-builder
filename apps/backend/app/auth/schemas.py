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
    role: str = "user"  # platform role: user|moderator|support|admin
    created_at: datetime


class UserUpdateRequest(BaseModel):
    """Self-update body for `PATCH /auth/me`. Only fields the user can edit
    on themselves — email/role/verified flags stay admin-only."""

    full_name: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=512)


class PasswordChangeRequest(BaseModel):
    """Self-change password while authenticated.

    OAuth-only users (no `hashed_password`) can't use this — they should
    set a password via the forgot-password / reset flow first.
    """

    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


class EmailChangeRequest(BaseModel):
    """Step 1 of self-change email — request a verification code emailed
    to the *new* address. Caller confirms with `EmailChangeConfirmRequest`."""

    new_email: EmailStr
    current_password: str = Field(min_length=1)


class EmailChangeConfirmRequest(BaseModel):
    """Step 2 — submit the verification code from the new address."""

    code: str = Field(min_length=4, max_length=12)


class AuthResponse(AppBaseModel):
    """Schema trả về sau khi đăng ký/đăng nhập thành công."""
    user: UserResponse
    message: str = "ok"

    def release(self) -> dict:
        data = super().release()
        data["user"] = self.user.release()
        return data


class MfaChallengeResponse(BaseModel):
    """Returned by /auth/login when the user has MFA enabled.

    The FE shows a TOTP prompt, then POSTs ``mfa_token`` + ``code``
    to /auth/mfa/verify-login to complete the flow. The session
    cookie is NOT set until verify-login succeeds.
    """

    mfa_required: bool = True
    mfa_token: str
    """Short-lived (5 min) signed token carrying the pending user_id.
    Caller passes it back to verify-login."""


class MfaVerifyLoginRequest(BaseModel):
    """Second step of MFA-protected login — confirm with auth-app
    code or backup code."""

    mfa_token: str
    code: str = Field(..., min_length=1)
    remember_me: bool = False
