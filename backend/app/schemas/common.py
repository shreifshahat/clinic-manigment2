"""Shared schema helpers."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

#: Amounts are always transferred as decimal *strings* to avoid any float
#: rounding in the browser. Clients parse them with ``Number()`` only for
#: display; the backend never does arithmetic on floats.
Money = Annotated[Decimal, Field(max_digits=14, decimal_places=2)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PageMeta(BaseModel):
    page: int = Field(ge=1)
    size: int = Field(ge=1)
    total: int = Field(ge=0)
    pages: int = Field(ge=0)


class Page[T](BaseModel):
    items: list[T]
    meta: PageMeta


class MessageResponse(BaseModel):
    message: str
