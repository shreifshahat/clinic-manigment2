"""Visit (medical record) schemas.

These payloads are **only** reachable by a doctor. The API never returns them
to the clinic owner or the receptionist — the endpoints are permission-gated
and the underlying table is protected by RLS as well.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import VisitAccessReason
from app.schemas.patient import PatientPublic


class VisitBase(BaseModel):
    chief_complaint: str = Field(default="", max_length=4000)
    diagnosis: str = Field(default="", max_length=4000)
    treatment: str = Field(default="", max_length=4000)
    notes: str = Field(default="", max_length=8000)
    vitals: dict[str, str] = Field(default_factory=dict)


class VisitCreate(VisitBase):
    appointment_id: uuid.UUID
    patient_id: uuid.UUID
    doctor_staff_id: uuid.UUID

    @model_validator(mode="after")
    def _vitals_limits(self) -> VisitCreate:
        if len(self.vitals) > 30:
            raise ValueError("عدد القراءات الحيوية كبير جدًا.")
        return self


class VisitUpdate(VisitBase):
    pass


class VisitComplete(BaseModel):
    note: str = Field(default="", max_length=1000)


class VisitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    appointment_id: uuid.UUID
    patient_id: uuid.UUID
    doctor_staff_id: uuid.UUID
    doctor_name: str = ""
    patient: PatientPublic | None = None
    chief_complaint: str = ""
    diagnosis: str = ""
    treatment: str = ""
    notes: str = ""
    vitals: dict[str, str] = Field(default_factory=dict)
    is_completed: bool = False
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    access_granted: bool = False


class VisitGrantCreate(BaseModel):
    visit_id: uuid.UUID
    granted_doctor_staff_id: uuid.UUID
    reason: VisitAccessReason
    note: str = Field(default="", max_length=240)
    expires_at: datetime | None = None


class VisitGrantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    visit_id: uuid.UUID
    granted_doctor_staff_id: uuid.UUID
    granted_doctor_name: str = ""
    granted_by_staff_id: uuid.UUID | None = None
    reason: VisitAccessReason
    note: str = ""
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime | None = None
