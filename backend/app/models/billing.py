"""Billing: services, invoices, invoice lines and payments.

Money rules:
* All amounts are ``NUMERIC(14,2)`` in PostgreSQL and ``Decimal`` in Python.
  Floats are never used for arithmetic.
* An invoice and its payments are separate objects: a payment references an
  invoice, so partial settlement, multiple tenders and a later void all keep a
  complete history.
* Card payments record **that** a payment happened on the terminal
  (``method='visa'``) plus an optional short reference. Full card numbers and
  CVV are never stored — the API rejects anything that looks like a PAN.
* Posted financial records are never deleted or silently edited. A correction
  is a *void* (with reason, actor and timestamp) or a compensating entry.
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
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.timeutil import now_utc
from app.db.session import Base
from app.models.enums import InvoiceStatus, PaymentStatus


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Service(Base):
    """Price list entry (consultation, procedure, …)."""

    __tablename__ = "services"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    default_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
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

    __table_args__ = (
        CheckConstraint("default_price >= 0", name="services_price_non_negative"),
        Index("ix_services_active", "is_active"),
    )


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    invoice_number: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False
    )
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True
    )
    visit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("visits.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=InvoiceStatus.ISSUED.value
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EGP")
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    notes: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
    )
    created_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff.id", ondelete="SET NULL"), nullable=True
    )
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    voided_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff.id", ondelete="SET NULL"), nullable=True
    )
    void_reason: Mapped[str] = mapped_column(String(240), nullable=False, default="")

    __table_args__ = (
        CheckConstraint(
            "status in ('issued','partially_paid','paid','void')",
            name="invoices_status_valid",
        ),
        CheckConstraint("total >= 0", name="invoices_total_non_negative"),
        Index("ix_invoices_patient_issued", "patient_id", "issued_at"),
        Index("ix_invoices_status_issued", "status", "issued_at"),
    )


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False
    )
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("services.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(160), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)

    __table_args__ = (
        CheckConstraint("quantity > 0", name="invoice_items_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="invoice_items_price_non_negative"),
        CheckConstraint("line_total >= 0", name="invoice_items_total_non_negative"),
        Index("ix_invoice_items_invoice", "invoice_id"),
    )


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, default=PaymentStatus.RECORDED.value
    )
    # Short, non-sensitive reference (receipt number / terminal approval code).
    reference: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    notes: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
    )
    collected_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff.id", ondelete="SET NULL"), nullable=True
    )
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    voided_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff.id", ondelete="SET NULL"), nullable=True
    )
    void_reason: Mapped[str] = mapped_column(String(240), nullable=False, default="")

    __table_args__ = (
        CheckConstraint("amount > 0", name="payments_amount_positive"),
        CheckConstraint("method in ('cash','visa')", name="payments_method_valid"),
        CheckConstraint("status in ('recorded','void')", name="payments_status_valid"),
        Index("ix_payments_invoice", "invoice_id"),
        Index("ix_payments_received", "received_at"),
    )
