"""Model registry.

Importing every model here guarantees that Alembic's ``autogenerate`` sees the
complete metadata and that ``Base.metadata`` contains every table.
"""

from __future__ import annotations

from app.db.session import Base
from app.models.appointment import Appointment
from app.models.billing import Invoice, InvoiceItem, Payment, Service
from app.models.enums import (
    AppointmentStatus,
    ExpenseStatus,
    InvoiceStatus,
    PaymentMethod,
    PaymentStatus,
    StaffRole,
    VisitAccessReason,
)
from app.models.expense import Expense, ExpenseCategory
from app.models.patient import Patient
from app.models.staff import (
    Doctor,
    DoctorBreak,
    DoctorLeave,
    DoctorWorkingHour,
    Staff,
    StaffSession,
)
from app.models.system import AuditLog, IdempotencyKey
from app.models.visit import Visit, VisitAccessGrant

__all__ = [
    "Appointment",
    "AppointmentStatus",
    "AuditLog",
    "Base",
    "Doctor",
    "DoctorBreak",
    "DoctorLeave",
    "DoctorWorkingHour",
    "Expense",
    "ExpenseCategory",
    "ExpenseStatus",
    "IdempotencyKey",
    "Invoice",
    "InvoiceItem",
    "InvoiceStatus",
    "Patient",
    "Payment",
    "PaymentMethod",
    "PaymentStatus",
    "Service",
    "Staff",
    "StaffRole",
    "StaffSession",
    "Visit",
    "VisitAccessGrant",
    "VisitAccessReason",
]
