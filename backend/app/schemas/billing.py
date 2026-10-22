"""Billing schemas.

The receptionist receives :class:`InvoiceTotalsRead` — total, paid, remaining
and method — and never the line-item detail, which keeps the financial trail
minimal for the role as specified.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import PaymentMethod
from app.schemas.patient import PatientFinancial, PatientPublic


class ServiceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=240)
    default_price: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=240)
    default_price: Decimal | None = Field(
        default=None, ge=0, max_digits=14, decimal_places=2
    )
    is_active: bool | None = None


class ServiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str = ""
    default_price: Decimal
    is_active: bool = True


class InvoiceItemCreate(BaseModel):
    service_id: uuid.UUID | None = None
    description: str = Field(min_length=1, max_length=160)
    quantity: Decimal = Field(default=Decimal("1"), gt=0, max_digits=10, decimal_places=2)
    unit_price: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)


class InvoiceCreate(BaseModel):
    patient_id: uuid.UUID
    appointment_id: uuid.UUID | None = None
    visit_id: uuid.UUID | None = None
    items: list[InvoiceItemCreate] = Field(min_length=1, max_length=50)
    notes: str = Field(default="", max_length=240)
    currency: str = Field(default="EGP", min_length=3, max_length=3)

    @model_validator(mode="after")
    def _currency_upper(self) -> InvoiceCreate:
        self.currency = self.currency.upper()
        return self


class InvoiceItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    service_id: uuid.UUID | None = None
    description: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal


class InvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invoice_number: str
    patient_id: uuid.UUID
    patient: PatientPublic | None = None
    patient_ref: PatientFinancial | None = None
    appointment_id: uuid.UUID | None = None
    visit_id: uuid.UUID | None = None
    status: str
    currency: str
    total: Decimal
    paid_amount: Decimal = Decimal("0")
    remaining_amount: Decimal = Decimal("0")
    items: list[InvoiceItemRead] = []
    notes: str = ""
    issued_at: datetime | None = None
    created_by_staff_id: uuid.UUID | None = None
    voided_at: datetime | None = None
    void_reason: str = ""


class InvoiceTotalsRead(BaseModel):
    """Receptionist view: totals only, no line items."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invoice_number: str
    patient_id: uuid.UUID
    patient_name: str = ""
    status: str
    currency: str
    total: Decimal
    paid_amount: Decimal = Decimal("0")
    remaining_amount: Decimal = Decimal("0")
    payment_method: PaymentMethod | None = None
    issued_at: datetime | None = None


class PaymentCreate(BaseModel):
    invoice_id: uuid.UUID
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    method: PaymentMethod
    reference: str = Field(default="", max_length=64)
    notes: str = Field(default="", max_length=240)
    received_at: datetime | None = None

    @model_validator(mode="after")
    def _no_card_data(self) -> PaymentCreate:
        """Reject anything that looks like a stored card number or CVV."""
        reference = (self.reference or "").strip()
        digits = "".join(ch for ch in reference if ch.isdigit())
        if len(digits) >= 13:
            raise ValueError(
                "لا يجوز حفظ أرقام البطاقات. سجّل العملية عبر جهاز الدفع فقط."
            )
        if self.notes and any(len(run) >= 13 for run in self.notes.replace("-", " ").split()):
            raise ValueError("لا يجوز حفظ بيانات البطاقة في الملاحظات.")
        self.reference = reference
        return self


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invoice_id: uuid.UUID
    amount: Decimal
    method: PaymentMethod
    status: str
    reference: str = ""
    notes: str = ""
    received_at: datetime | None = None
    collected_by_staff_id: uuid.UUID | None = None
    voided_at: datetime | None = None
    void_reason: str = ""


class VoidRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=240)
