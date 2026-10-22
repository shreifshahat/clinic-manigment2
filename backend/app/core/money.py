"""Money helpers.

Financial amounts are **never** floats. They are ``decimal.Decimal`` in Python
and ``NUMERIC(14,2)`` in PostgreSQL, quantized to the clinic's currency scale.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from app.core.errors import ValidationBusinessError


def money(value: object, decimals: int = 2) -> Decimal:
    """Coerce an arbitrary value into a quantized Decimal amount.

    Floats are accepted for convenience (e.g. JSON) but converted through
    ``str`` so that ``0.1`` does not become ``0.1000000000000000055…``.
    """
    if isinstance(value, Decimal):
        dec = value
    elif isinstance(value, float):
        dec = Decimal(str(value))
    elif isinstance(value, int):
        dec = Decimal(value)
    elif isinstance(value, str):
        try:
            dec = Decimal(value.strip())
        except InvalidOperation as exc:
            raise ValidationBusinessError("المبلغ المُدخل غير صالح.") from exc
    else:
        raise ValidationBusinessError("المبلغ المُدخل غير صالح.")
    if not dec.is_finite():
        raise ValidationBusinessError("المبلغ المُدخل غير صالح.")
    return dec.quantize(Decimal(1).scaleb(-decimals))


def zero(decimals: int = 2) -> Decimal:
    return Decimal(0).quantize(Decimal(1).scaleb(-decimals))


def to_float(value: Decimal) -> float:
    """Serialize a Decimal for JSON.

    Only used at the API boundary where the value is a *display* amount; the
    canonical representation in the database stays ``NUMERIC``. Clients that
    need exact arithmetic receive the value as a JSON string (see
    ``schemas.common.MoneyAmount``).
    """
    return float(value)
