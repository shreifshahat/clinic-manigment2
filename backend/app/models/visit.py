"""Clinical encounters — the medical file.

Access rule (enforced by RLS *and* by the service layer):

* A doctor may read/write a visit only for encounters they performed, unless
  an explicit, time-boxed grant exists in ``visit_access_grants``.
* The clinic owner and the receptionist have **no RLS policy** that allows them
  to read this table at all. There is deliberately no ``owner`` policy here.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.timeutil import now_utc
from app.db.session import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False
    )
    doctor_staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctors.staff_id", ondelete="RESTRICT"), nullable=False
    )
    chief_complaint: Mapped[str] = mapped_column(Text, nullable=False, default="")
    diagnosis: Mapped[str] = mapped_column(Text, nullable=False, default="")
    treatment: Mapped[str] = mapped_column(Text, nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    vitals: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_completed: Mapped[bool] = mapped_column(nullable=False, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(
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

    __table_args__ = (
        Index("ix_visits_patient_created", "patient_id", "created_at"),
        Index("ix_visits_doctor_created", "doctor_staff_id", "created_at"),
    )


class VisitAccessGrant(Base):
    """Explicit, auditable authorisation for a doctor to read another
    doctor's encounter (referral, coverage, follow-up).

    Grants are never silent: they record who granted them, why and until when.
    """

    __tablename__ = "visit_access_grants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    visit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("visits.id", ondelete="CASCADE"), nullable=False
    )
    granted_doctor_staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctors.staff_id", ondelete="CASCADE"), nullable=False
    )
    granted_by_staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff.id", ondelete="SET NULL"), nullable=True
    )
    reason: Mapped[str] = mapped_column(String(40), nullable=False)
    note: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
    )

    __table_args__ = (
        CheckConstraint(
            "reason in ('referral','coverage','follow_up','owner')",
            name="visit_access_grants_reason_valid",
        ),
        Index("ix_visit_access_grants_doctor", "granted_doctor_staff_id", "revoked_at"),
    )
