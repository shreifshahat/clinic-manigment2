"""Domain enumerations.

These are plain ``str`` enums stored in ``VARCHAR`` columns guarded by CHECK
constraints. Text + CHECK is used instead of native PostgreSQL ENUM types
because adding a value to a native enum requires ``ALTER TYPE`` (harder to
review and to roll back) while a CHECK constraint is a normal, reviewable
migration.
"""

from __future__ import annotations

from enum import StrEnum


class StaffRole(StrEnum):
    OWNER = "owner"
    DOCTOR = "doctor"
    RECEPTIONIST = "receptionist"


class AppointmentStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


#: Statuses that occupy the doctor's time slot. Any other status releases it.
BLOCKING_APPOINTMENT_STATUSES: frozenset[AppointmentStatus] = frozenset(
    {
        AppointmentStatus.PENDING,
        AppointmentStatus.CONFIRMED,
        AppointmentStatus.IN_PROGRESS,
    }
)

#: Statuses from which a booking can still be rescheduled.
RESCHEDULABLE_STATUSES: frozenset[AppointmentStatus] = frozenset(
    {
        AppointmentStatus.PENDING,
        AppointmentStatus.CONFIRMED,
    }
)


class PaymentMethod(StrEnum):
    CASH = "cash"
    VISA = "visa"


class InvoiceStatus(StrEnum):
    ISSUED = "issued"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    VOID = "void"


class PaymentStatus(StrEnum):
    RECORDED = "recorded"
    VOID = "void"


class ExpenseStatus(StrEnum):
    RECORDED = "recorded"
    VOID = "void"


class VisitAccessReason(StrEnum):
    REFERRAL = "referral"
    COVERAGE = "coverage"
    FOLLOW_UP = "follow_up"
    OWNER = "owner"
