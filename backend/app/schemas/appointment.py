"""Appointment schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import AppointmentStatus
from app.schemas.patient import PatientFinancial, PatientPublic


class AppointmentCreate(BaseModel):
    doctor_staff_id: uuid.UUID
    patient_id: uuid.UUID
    starts_at: datetime
    duration_minutes: int | None = Field(default=None, ge=5, le=480)
    visit_reason: str = Field(default="", max_length=160)
    notes: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def _tz_aware(self) -> AppointmentCreate:
        if self.starts_at.tzinfo is None:
            raise ValueError("يجب إرسال وقت البداية مع المنطقة الزمنية (ISO-8601).")
        return self


class AppointmentUpdate(BaseModel):
    visit_reason: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=500)
    duration_minutes: int | None = Field(default=None, ge=5, le=480)


class AppointmentStatusUpdate(BaseModel):
    status: AppointmentStatus
    reason: str = Field(default="", max_length=160)

    @model_validator(mode="after")
    def _status_specific_reason(self) -> AppointmentStatusUpdate:
        needs_reason = self.status in {AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW}
        if needs_reason and not self.reason.strip():
            raise ValueError("يجب ذكر سبب الإلغاء أو عدم الحضور.")
        return self


class AppointmentCancel(BaseModel):
    reason: str = Field(min_length=3, max_length=160)


class AppointmentReschedule(BaseModel):
    starts_at: datetime
    duration_minutes: int | None = Field(default=None, ge=5, le=480)
    reason: str = Field(default="", max_length=160)

    @model_validator(mode="after")
    def _tz_aware(self) -> AppointmentReschedule:
        if self.starts_at.tzinfo is None:
            raise ValueError("يجب إرسال وقت البداية مع المنطقة الزمنية (ISO-8601).")
        return self


class AppointmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    doctor_staff_id: uuid.UUID
    patient_id: uuid.UUID
    doctor_name: str = ""
    doctor_specialty: str = ""
    patient: PatientPublic | None = None
    patient_ref: PatientFinancial | None = None
    starts_at: datetime
    ends_at: datetime
    status: AppointmentStatus
    visit_reason: str = ""
    cancellation_reason: str = ""
    reschedule_count: int = 0
    version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None
    confirmed_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None


class SlotRead(BaseModel):
    starts_at: datetime
    ends_at: datetime
    is_available: bool = True
    reason: str | None = None


class DaySchedule(BaseModel):
    doctor_staff_id: uuid.UUID
    doctor_name: str = ""
    date: str
    slots: list[SlotRead] = []
    appointments: list[AppointmentRead] = []
