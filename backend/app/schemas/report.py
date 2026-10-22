"""Report schemas.

Reporting rules implemented here (documented in ``docs/REPORTS.md``):

* **Weekly report** = *collections* (payments actually received) − *recorded
  expenses* within the same window. It is an operational cash figure, **not**
  an accounting profit.
* **Invoiced total** and **collected total** are always reported separately.
* Voided payments and voided expenses are excluded from every figure; they
  remain visible in the audit trail.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class PeriodRead(BaseModel):
    start: date
    end: date
    timezone: str
    days: int


class WeeklyReport(BaseModel):
    period: PeriodRead
    currency: str

    # Headline figures
    invoiced_total: Decimal = Decimal("0")
    collected_total: Decimal = Decimal("0")
    expenses_total: Decimal = Decimal("0")
    net_result: Decimal = Decimal("0")  # collected − expenses
    outstanding_total: Decimal = Decimal("0")  # invoiced but not collected

    # Counts
    invoice_count: int = 0
    payment_count: int = 0
    expense_count: int = 0
    appointment_count: int = 0
    completed_visit_count: int = 0
    no_show_count: int = 0
    cancelled_count: int = 0

    # Breakdowns
    collected_by_method: dict[str, Decimal] = Field(default_factory=dict)
    daily: list[DailyReport] = Field(default_factory=list)
    notes: str = (
        "صافي النتيجة = المتحصلات ناقص المصروفات المسجلة. "
        "هذا مؤشر تشغيلي وليس ربحًا محاسبيًا نهائيًا."
    )


class DailyReport(BaseModel):
    date: date
    invoiced_total: Decimal = Decimal("0")
    collected_total: Decimal = Decimal("0")
    expenses_total: Decimal = Decimal("0")
    net_result: Decimal = Decimal("0")
    appointments: int = 0


class DoctorPerformanceRow(BaseModel):
    doctor_staff_id: uuid.UUID
    doctor_name: str
    appointments: int = 0
    completed: int = 0
    no_show: int = 0
    cancelled: int = 0
    invoiced_total: Decimal = Decimal("0")
    collected_total: Decimal = Decimal("0")


class DoctorPerformanceReport(BaseModel):
    period: PeriodRead
    currency: str
    rows: list[DoctorPerformanceRow] = Field(default_factory=list)


class ScheduleDayRow(BaseModel):
    date: date
    doctor_staff_id: uuid.UUID
    doctor_name: str = ""
    total: int = 0
    pending: int = 0
    confirmed: int = 0
    in_progress: int = 0
    completed: int = 0
    cancelled: int = 0
    no_show: int = 0


class ScheduleReport(BaseModel):
    period: PeriodRead
    rows: list[ScheduleDayRow] = Field(default_factory=list)


WeeklyReport.model_rebuild()
