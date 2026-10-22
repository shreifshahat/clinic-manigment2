"""Authentication-related schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.core.permissions import Permission
from app.models.enums import StaffRole


class SessionRead(BaseModel):
    """Returned to the frontend right after a successful sign-in."""

    staff_id: uuid.UUID
    role: StaffRole
    full_name: str
    email: str
    permissions: list[str]
    must_change_password: bool = False


class LogoutResponse(BaseModel):
    message: str
    revoked_sessions: int = 0
    #: هل أُنهيت جلسة مزوّد المصادقة أيضًا (يتطلب ضبط Supabase).
    provider_session_revoked: bool = False


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)

    def validate_strength(self) -> None:
        password = self.new_password
        if password.lower() == password or password.upper() == password:
            raise ValueError("يجب أن تحتوي كلمة المرور على أحرف كبيرة وصغيرة.")
        if not any(ch.isdigit() for ch in password):
            raise ValueError("يجب أن تحتوي كلمة المرور على رقم واحد على الأقل.")


class PasswordChangeResponse(BaseModel):
    message: str


class DevLoginRequest(BaseModel):
    """Only available when development authentication is enabled."""

    email: str = Field(min_length=5, max_length=255)
    ttl_minutes: int = Field(default=60, ge=1, le=720)


class DevLoginResponse(BaseModel):
    """Development sign-in result (never used in production)."""

    token: str
    expires_in_minutes: int
    staff: SessionRead


class ClinicMeta(BaseModel):
    """Public, non-sensitive clinic configuration for the frontend."""

    name: str
    timezone: str
    currency: str
    currency_decimals: int
    week_start_weekday: int
    today: str
    permissions_of_current_user: list[Permission] = []
