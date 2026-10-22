"""Patient records.

The patient table holds *identifiers and contact details only*. Medical content
lives exclusively in :mod:`app.models.visit` and is protected by RLS so that
the owner and the receptionist have **no database-level path** to it.

Retention: patients are never hard-deleted. ``deleted_at`` marks the record as
withdrawn (the row is anonymized by a documented maintenance job, and the
linked clinical history is kept for the legally required retention period).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.timeutil import now_utc
from app.db.session import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    national_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
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
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: سبب سحب السجل (يُسجَّل في سجل التدقيق أيضًا).
    deactivate_reason: Mapped[str] = mapped_column(String(240), nullable=False, default="")

    __table_args__ = (
        CheckConstraint(
            "gender in ('','male','female')", name="patients_gender_valid"
        ),
        Index("ix_patients_full_name", "full_name"),
        Index("ix_patients_phone", "phone"),
        Index("ix_patients_active", "is_active"),
    )
