"""System-level tables: audit trail, idempotency keys and clinic settings.

``audit_log`` is **append-only**: RLS grants INSERT to any authenticated staff
member and SELECT to the clinic owner; there is no UPDATE or DELETE policy, so
a compromised application role cannot rewrite history.

The audit trail records *that* a medical record was accessed and *who* did it.
It never copies the medical content itself.
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
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.timeutil import now_utc
from app.db.session import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    actor_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff.id", ondelete="SET NULL"), nullable=True
    )
    actor_role: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    outcome: Mapped[str] = mapped_column(String(16), nullable=False, default="success")
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    ip_address: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    # Free-form, non-medical context (e.g. {"window": "..."} ).
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
    )

    __table_args__ = (
        CheckConstraint(
            "outcome in ('success','denied','failure')", name="audit_log_outcome_valid"
        ),
        Index("ix_audit_log_created", "created_at"),
        Index("ix_audit_log_actor", "actor_staff_id", "created_at"),
        Index("ix_audit_log_entity", "entity_type", "entity_id"),
    )


class IdempotencyKey(Base):
    """Stores the outcome of a mutating request keyed by ``Idempotency-Key``.

    A repeated submission with the same key returns the stored response instead
    of creating a second booking / invoice / payment.
    """

    __tablename__ = "idempotency_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(120), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response_status: Mapped[int] = mapped_column(Integer, nullable=True)
    response_body: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_idempotency_keys_lookup", "staff_id", "key", unique=True),
        Index("ix_idempotency_keys_expires", "expires_at"),
    )
