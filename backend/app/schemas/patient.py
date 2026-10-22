"""Patient schemas.

Different roles receive different *shapes* of the same patient:

* ``PatientPublic``   – id, full name, phone. Reception and doctors.
* ``PatientFinancial`` – id, full name only. The clinic owner (financial
  reports must not leak contact details).
* ``PatientFull``     – everything, reception only.
"""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

PHONE_PATTERN = re.compile(r"^[0-9+\-\s()]{6,20}$")


class PatientBase(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=6, max_length=32)
    birth_date: date | None = None
    gender: str = Field(default="", max_length=16)
    national_id: str | None = Field(default=None, max_length=32)
    notes: str = Field(default="", max_length=500)

    @field_validator("full_name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("اسم المريض غير صالح.")
        return value

    @field_validator("phone")
    @classmethod
    def _valid_phone(cls, value: str) -> str:
        value = value.strip()
        if not PHONE_PATTERN.match(value):
            raise ValueError("رقم التواصل غير صالح.")
        return value

    @field_validator("gender")
    @classmethod
    def _valid_gender(cls, value: str) -> str:
        value = (value or "").strip().lower()
        if value not in {"", "male", "female"}:
            raise ValueError("قيمة الجنس غير صالحة.")
        return value


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, min_length=6, max_length=32)
    birth_date: date | None = None
    gender: str | None = Field(default=None, max_length=16)
    national_id: str | None = Field(default=None, max_length=32)
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("phone")
    @classmethod
    def _valid_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not PHONE_PATTERN.match(value):
            raise ValueError("رقم التواصل غير صالح.")
        return value


class DeactivatePatientRequest(BaseModel):
    """ withdrawing a patient record requires a documented reason."""

    reason: str = Field(min_length=3, max_length=240)


class PatientPublic(BaseModel):
    """Identity + contact. Safe for reception and for the treating doctor."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    phone: str


class PatientFinancial(BaseModel):
    """Minimal identity used next to financial figures (clinic owner)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str


class PatientFull(PatientPublic):
    model_config = ConfigDict(from_attributes=True)

    birth_date: date | None = None
    gender: str = ""
    national_id: str | None = None
    notes: str = ""
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PatientListItem(PatientPublic):
    model_config = ConfigDict(from_attributes=True)

    last_appointment_at: str | None = None
    appointment_count: int = 0


class PatientFinancialListItem(PatientFinancial):
    """List item for the clinic owner: identity without contact details."""

    model_config = ConfigDict(from_attributes=True)

    last_appointment_at: str | None = None
    appointment_count: int = 0
