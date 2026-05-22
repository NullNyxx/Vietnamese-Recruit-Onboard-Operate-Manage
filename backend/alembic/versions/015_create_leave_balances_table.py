"""Create leave_balances table.

Revision ID: 015
Revises: 014
Create Date: 2026-05-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create leave_balances table."""
    op.create_table(
        "leave_balances",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("leave_type_id", sa.Uuid(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("total_days", sa.Numeric(precision=5, scale=1), nullable=False),
        sa.Column(
            "used_days",
            sa.Numeric(precision=5, scale=1),
            server_default="0",
            nullable=False,
        ),
        sa.Column("remaining_days", sa.Numeric(precision=5, scale=1), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["leave_type_id"], ["leave_types.id"]),
        sa.UniqueConstraint(
            "employee_id", "leave_type_id", "year", name="uq_leave_balance"
        ),
    )

    op.create_index("ix_leave_balances_employee_id", "leave_balances", ["employee_id"])


def downgrade() -> None:
    """Drop leave_balances table."""
    op.drop_index("ix_leave_balances_employee_id", table_name="leave_balances")
    op.drop_table("leave_balances")
