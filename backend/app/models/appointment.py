"""Appointments — the booking core of the system.

Conflict prevention is implemented **twice**:

* Application level: the booking service locks the doctor row
  (``SELECT ... FOR UPDATE``), re-checks availability and only then inserts.
* Database level: a GiST exclusion constraint over
  ``tstzrange(starts_at, ends_at)`` for the same doctor, restricted to the
  statuses that occupy the slot. The constraint is the final authority: even a
  buggy code path, a manual ``INSERT`` in the SQL editor, or a future service
  cannot produce an overlapping booking.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.timeutil import now_utc
from app.db.session import Base
from app.models.enums import AppointmentStatus


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    doctor_staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctors.staff_id", ondelete="RESTRICT"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=AppointmentStatus.PENDING.value
    )
    # Short, non-clinical reason given at booking time (reception context).
    visit_reason: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    cancellation_reason: Mapped[str] = mapped_column(
        String(160), nullable=False, default=""
    )
    rescheduled_from_appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True
    )
    reschedule_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        onupdate=now_utc,
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="appointments_range_valid"),
        CheckConstraint(
            "status in ('pending','confirmed','in_progress','completed','cancelled','no_show')",
            name="appointments_status_valid",
        ),
        Index("ix_appointments_doctor_start", "doctor_staff_id", "starts_at"),
        Index("ix_appointments_patient_start", "patient_id", "starts_at"),
        Index("ix_appointments_status", "status"),
    )
