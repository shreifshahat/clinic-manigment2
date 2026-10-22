"""Timezone-aware helpers.

Policy (single source of truth for the whole system):

* Every timestamp is stored in the database as ``timestamptz`` (UTC internally).
* The API speaks ISO-8601 with an explicit offset; responses are UTC ``...Z``.
* The clinic has ONE timezone (``CLINIC_TIMEZONE``). Wall-clock rules such as
  working hours, breaks and weekly report windows are expressed in that
  timezone, never in UTC.
* The frontend renders using the same timezone value exposed by
  ``GET /api/v1/meta/clinic``.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

UTC = UTC


def now_utc() -> datetime:
    """Current instant, timezone aware, UTC."""
    return datetime.now(UTC)


def to_utc(value: datetime, tz: ZoneInfo) -> datetime:
    """Convert a naive/aware datetime expressed in ``tz`` to UTC.

    Naive input is interpreted as wall-clock time in ``tz`` (the clinic's local
    time). Aware input is converted (not re-interpreted).
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=tz)
    return value.astimezone(UTC)


def to_local(value: datetime, tz: ZoneInfo) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(tz)


def combine_local(day: date, clock: time, tz: ZoneInfo) -> datetime:
    """Build an absolute instant from a local date + local wall-clock time."""
    return datetime.combine(day, clock, tzinfo=tz).astimezone(UTC)


def local_date(value: datetime, tz: ZoneInfo) -> date:
    return to_local(value, tz).date()


def week_start(day: date, week_start_weekday: int) -> date:
    """Return the first day of the week that contains ``day``.

    ``week_start_weekday`` uses ISO-8601 numbering (Monday=1 ... Sunday=7).
    The default for an Arabic clinic is Saturday (6).
    """
    delta = (day.isoweekday() - week_start_weekday) % 7
    return day - timedelta(days=delta)


def iso_utc(value: datetime | None) -> str | None:
    """Serialize an instant as UTC ISO-8601 with a ``Z`` suffix."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
