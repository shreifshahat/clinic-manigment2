"""Expense schemas (clinic owner only)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExpenseCategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)


class ExpenseCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    is_active: bool = True


class ExpenseCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    description: str = Field(min_length=2, max_length=200)
    category_id: uuid.UUID | None = None
    notes: str = Field(default="", max_length=1000)
    incurred_at: datetime | None = None

    @model_validator(mode="after")
    def _tz_aware(self) -> ExpenseCreate:
        if self.incurred_at is not None and self.incurred_at.tzinfo is None:
            raise ValueError("يجب إرسال تاريخ الصرف مع المنطقة الزمنية (ISO-8601).")
        return self


class ExpenseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category_id: uuid.UUID | None = None
    category_name: str = ""
    amount: Decimal
    description: str
    incurred_at: datetime | None = None
    status: str
    notes: str = ""
    created_by_staff_id: uuid.UUID | None = None
    voided_at: datetime | None = None
    void_reason: str = ""


class VoidRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=240)
