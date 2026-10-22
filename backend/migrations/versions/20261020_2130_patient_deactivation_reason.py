"""record why a patient record was withdrawn

Revision ID: 20261020_2130_deactivate_reason
Revises: 20261020_2110_rls
Create Date: 2026-10-21 09:30:00

E-08: withdrawing a patient record is a sensitive administrative action; the
reason must be stored on the record itself and in the audit trail.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261020_2130_deactivate_reason"
down_revision: str | None = "20261020_2110_rls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "patients",
        sa.Column(
            "deactivate_reason",
            sa.String(length=240),
            nullable=False,
            server_default="",
        ),
    )


def downgrade() -> None:
    op.drop_column("patients", "deactivate_reason")
