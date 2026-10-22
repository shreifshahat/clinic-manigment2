"""Expenses and their categories.

Only the clinic owner can see or record expenses (least privilege). Posted
expenses are never edited in place: a mistake is voided with a reason and
re-issued, which keeps the financial trail intact.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.timeutil import now_utc
from app.db.session import Base
from app.models.enums import ExpenseStatus


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class ExpenseCategory(Base):
    __tablename__ = "expense_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
    )


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("expense_categories.id", ondelete="SET NULL"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    incurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
    )
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, default=ExpenseStatus.RECORDED.value
    )
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff.id", ondelete="SET NULL"), nullable=True
    )
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    voided_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff.id", ondelete="SET NULL"), nullable=True
    )
    void_reason: Mapped[str] = mapped_column(String(240), nullable=False, default="")

    __table_args__ = (
        CheckConstraint("amount > 0", name="expenses_amount_positive"),
        CheckConstraint("status in ('recorded','void')", name="expenses_status_valid"),
        Index("ix_expenses_incurred", "incurred_at"),
        Index("ix_expenses_category", "category_id"),
    )
