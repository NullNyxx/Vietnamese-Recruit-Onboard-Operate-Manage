"""Create overtime_requests table.

Revision ID: 019
Revises: 018
Create Date: 2026-05-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create overtime_requests table."""
    op.create_table(
        "overtime_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("planned_hours", sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column("actual_hours", sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"]),
    )

    op.create_index("ix_overtime_requests_employee_id", "overtime_requests", ["employee_id"])


def downgrade() -> None:
    """Drop overtime_requests table."""
    op.drop_index("ix_overtime_requests_employee_id", table_name="overtime_requests")
    op.drop_table("overtime_requests")
