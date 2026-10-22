"""Staff, doctor profile and schedule schemas."""

from __future__ import annotations

import uuid
from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import StaffRole


class StaffCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    role: StaffRole
    phone: str | None = Field(default=None, max_length=32)
    national_id: str | None = Field(default=None, max_length=32)
    specialty: str = Field(default="", max_length=120)
    default_slot_minutes: int = Field(default=30, ge=5, le=480)
    consultation_fee: str = Field(default="0", pattern=r"^\d{1,12}(\.\d{1,2})?$")

    @model_validator(mode="after")
    def _doctor_fields(self) -> StaffCreate:
        if self.role == StaffRole.DOCTOR and not self.specialty.strip():
            # Speciality is optional in practice, but the doctor must be
            # initialised with a slot length that the booking engine can use.
            self.specialty = ""
        return self


class StaffUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=32)
    specialty: str | None = Field(default=None, max_length=120)
    default_slot_minutes: int | None = Field(default=None, ge=5, le=480)
    consultation_fee: str | None = Field(
        default=None, pattern=r"^\d{1,12}(\.\d{1,2})?$"
    )
    is_accepting_patients: bool | None = None


class StaffRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    auth_user_id: uuid.UUID | None = None
    role: StaffRole
    full_name: str
    email: str
    phone: str | None = None
    national_id: str | None = None
    is_active: bool = True
    must_change_password: bool = False
    specialty: str = ""
    default_slot_minutes: int = 30
    consultation_fee: str = "0"
    is_accepting_patients: bool = True
    created_at: datetime | None = None
    last_login_at: datetime | None = None


class StaffCreateResult(StaffRead):
    """Returned once, right after the account is created.

    ``temporary_password`` is shown **only** in this response: it is never
    stored by the clinic system. The employee must change it at first login.
    """

    temporary_password: str | None = None
    auth_provider: str = "supabase"


class StaffSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    staff_id: uuid.UUID
    user_agent: str = ""
    ip_address: str = ""
    issued_at: datetime | None = None
    last_seen_at: datetime | None = None
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    revoked_reason: str = ""


class PasswordResetRequest(BaseModel):
    reason: str = Field(default="", max_length=240)


class DoctorWorkingHourCreate(BaseModel):
    weekday: int = Field(ge=1, le=7)
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def _valid_range(self) -> DoctorWorkingHourCreate:
        if self.end_time <= self.start_time:
            raise ValueError("نهاية الدوام يجب أن تكون بعد بدايته.")
        return self


class DoctorWorkingHourRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    doctor_staff_id: uuid.UUID
    weekday: int
    start_time: time
    end_time: time
    is_active: bool = True


class DoctorBreakCreate(BaseModel):
    weekday: int = Field(ge=1, le=7)
    start_time: time
    end_time: time
    label: str = Field(default="", max_length=80)

    @model_validator(mode="after")
    def _valid_range(self) -> DoctorBreakCreate:
        if self.end_time <= self.start_time:
            raise ValueError("نهاية الاستراحة يجب أن تكون بعد بدايتها.")
        return self


class DoctorBreakRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    doctor_staff_id: uuid.UUID
    weekday: int
    start_time: time
    end_time: time
    label: str = ""


class DoctorLeaveCreate(BaseModel):
    doctor_staff_id: uuid.UUID
    starts_at: datetime
    ends_at: datetime
    reason: str = Field(default="", max_length=160)

    @model_validator(mode="after")
    def _valid_window(self) -> DoctorLeaveCreate:
        if self.starts_at.tzinfo is None or self.ends_at.tzinfo is None:
            raise ValueError("يجب إرسال التواريخ مع المنطقة الزمنية (ISO-8601).")
        if self.ends_at <= self.starts_at:
            raise ValueError("نهاية الإجازة يجب أن تكون بعد بدايتها.")
        return self


class DoctorLeaveRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    doctor_staff_id: uuid.UUID
    starts_at: datetime
    ends_at: datetime
    reason: str = ""
    created_at: datetime | None = None
