"""Staff accounts, doctor profiles and their working rules.

There is **no password column anywhere in this schema**. Authentication is
owned by Supabase Auth; ``staff.auth_user_id`` is the link between the two
worlds. The role and the business profile live here, in the clinic's own
database, so that permissions are auditable and independent of the auth
provider.
"""

from __future__ import annotations

import uuid
from datetime import datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.timeutil import now_utc
from app.db.session import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Staff(Base):
    """A member of the clinic team (owner, doctor or receptionist)."""

    __tablename__ = "staff"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    auth_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    national_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
    created_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("staff.id", ondelete="SET NULL"),
        nullable=True,
    )

    doctor: Mapped[Doctor | None] = relationship(
        back_populates="staff", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "role in ('owner','doctor','receptionist')", name="staff_role_valid"
        ),
        Index("ix_staff_role_active", "role", "is_active"),
    )


class Doctor(Base):
    """Doctor-specific attributes. ``staff_id`` is the primary key.

    Keeping the doctor keyed by ``staff_id`` (instead of a second surrogate
    id) means every RLS policy can compare ``doctor_staff_id`` with the
    caller's ``app.user_id`` directly, with no extra joins.
    """

    __tablename__ = "doctors"

    staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff.id", ondelete="CASCADE"), primary_key=True
    )
    specialty: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    default_slot_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    consultation_fee: Mapped[float] = mapped_column(
        Numeric(14, 2), nullable=False, default=0
    )
    is_accepting_patients: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
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

    staff: Mapped[Staff] = relationship(back_populates="doctor", foreign_keys=[staff_id])
    working_hours: Mapped[list[DoctorWorkingHour]] = relationship(
        back_populates="doctor",
        cascade="all, delete-orphan",
        order_by="DoctorWorkingHour.weekday",
    )
    breaks: Mapped[list[DoctorBreak]] = relationship(
        back_populates="doctor", cascade="all, delete-orphan"
    )
    leaves: Mapped[list[DoctorLeave]] = relationship(
        back_populates="doctor", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "default_slot_minutes between 5 and 480", name="doctors_slot_minutes_valid"
        ),
        CheckConstraint("consultation_fee >= 0", name="doctors_fee_non_negative"),
    )


class DoctorWorkingHour(Base):
    """Recurring weekly availability window (local wall-clock time)."""

    __tablename__ = "doctor_working_hours"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    doctor_staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctors.staff_id", ondelete="CASCADE"), nullable=False
    )
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)  # ISO: 1=Mon .. 7=Sun
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
    )

    doctor: Mapped[Doctor] = relationship(back_populates="working_hours")

    __table_args__ = (
        UniqueConstraint(
            "doctor_staff_id", "weekday", "start_time", name="doctor_staff_id"
        ),
        CheckConstraint("weekday between 1 and 7", name="doctor_working_hours_weekday_valid"),
        CheckConstraint("end_time > start_time", name="doctor_working_hours_range_valid"),
    )


class DoctorBreak(Base):
    """A break inside a working day (e.g. lunch). No appointment may overlap it."""

    __tablename__ = "doctor_breaks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    doctor_staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctors.staff_id", ondelete="CASCADE"), nullable=False
    )
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    label: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
    )

    doctor: Mapped[Doctor] = relationship(back_populates="breaks")

    __table_args__ = (
        CheckConstraint("weekday between 1 and 7", name="doctor_breaks_weekday_valid"),
        CheckConstraint("end_time > start_time", name="doctor_breaks_range_valid"),
    )


class DoctorLeave(Base):
    """An approved absence (holiday, conference, illness) blocking bookings."""

    __tablename__ = "doctor_leaves"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    doctor_staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctors.staff_id", ondelete="CASCADE"), nullable=False
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    created_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("staff.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
    )

    doctor: Mapped[Doctor] = relationship(back_populates="leaves")

    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="doctor_leaves_range_valid"),
        Index("ix_doctor_leaves_doctor_window", "doctor_staff_id", "starts_at", "ends_at"),
    )


class StaffSession(Base):
    """Server-side session registry.

    Supabase Auth issues and refreshes the JWT; this table lets the clinic
    *end* a session immediately (logout, role change, suspected compromise)
    instead of waiting for the token to expire.
    """

    __tablename__ = "staff_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff.id", ondelete="CASCADE"), nullable=False
    )
    # SHA-256 of the access token: identifies the session without storing it.
    token_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    ip_address: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[str] = mapped_column(String(80), nullable=False, default="")

    __table_args__ = (
        UniqueConstraint("token_fingerprint", name="token_fingerprint"),
        Index("ix_staff_sessions_staff_active", "staff_id", "revoked_at"),
    )
