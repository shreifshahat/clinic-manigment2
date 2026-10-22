"""shared rate-limit counters

Revision ID: 20261020_2140_rate_limit
Revises: 20261020_2130_deactivate_reason
Create Date: 2026-10-21 09:40:00

E-05: the previous limiter kept its counters in the memory of a single
process, so the effective limit multiplied by the number of workers. The
counters now live in PostgreSQL and are therefore identical for every worker
and every instance.

The table holds **no personal data**: the key is a salted hash of the client
address, and only a counter plus a time window are stored.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261020_2140_rate_limit"
down_revision: str | None = "20261020_2130_deactivate_reason"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rate_limit_counters",
        sa.Column("key", sa.String(length=80), primary_key=True),
        sa.Column("window_start", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("counter", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_rate_limit_counters_window_start",
        "rate_limit_counters",
        ["window_start"],
    )
    op.execute("alter table rate_limit_counters enable row level security")
    # جدول تقني: لا يحتوي بيانات شخصية، والوصول إليه من دور التطبيق فقط.
    op.execute(
        """
        create policy rate_limit_counters_all on rate_limit_counters
            for all using (true) with check (true)
        """
    )
    op.execute(
        """
        do $do$
        begin
            if exists (select 1 from pg_roles where rolname = 'clinic_app') then
                grant select, insert, update, delete on rate_limit_counters to clinic_app;
            end if;
        end
        $do$;
        """
    )


def downgrade() -> None:
    op.execute("drop table if exists rate_limit_counters")
