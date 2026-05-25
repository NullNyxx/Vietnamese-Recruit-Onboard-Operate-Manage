"""Create payroll_periods table.

Revision ID: 024
Revises: 023
Create Date: 2026-05-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "024"
down_revision: Union[str, None] = "023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payroll_periods",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("total_gross", sa.Numeric(precision=14, scale=2), server_default="0"),
        sa.Column("total_net", sa.Numeric(precision=14, scale=2), server_default="0"),
        sa.Column("total_tax", sa.Numeric(precision=14, scale=2), server_default="0"),
        sa.Column("total_insurance", sa.Numeric(precision=14, scale=2), server_default="0"),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_by", sa.Uuid(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("month", "year", name="uq_payroll_period_month_year"),
    )


def downgrade() -> None:
    op.drop_table("payroll_periods")