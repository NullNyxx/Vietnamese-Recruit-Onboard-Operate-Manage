"""Create payslips table.

Revision ID: 025
Revises: 024
Create Date: 2026-05-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "025"
down_revision: Union[str, None] = "024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payslips",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("period_id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("gross_salary", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("total_allowances", sa.Numeric(precision=10, scale=2), server_default="0"),
        sa.Column("total_ot_hours", sa.Numeric(precision=6, scale=2), server_default="0"),
        sa.Column("total_ot_amount", sa.Numeric(precision=10, scale=2), server_default="0"),
        sa.Column("gross_income", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("personal_deduction", sa.Numeric(precision=10, scale=2), server_default="11000000"),
        sa.Column("dependent_deduction", sa.Numeric(precision=10, scale=2), server_default="0"),
        sa.Column("taxable_income", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("income_tax", sa.Numeric(precision=10, scale=2), server_default="0"),
        sa.Column("insurance_premium", sa.Numeric(precision=10, scale=2), server_default="0"),
        sa.Column("net_salary", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("work_days", sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column("actual_work_days", sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column("pdf_url", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payslips_period_id", "payslips", ["period_id"])
    op.create_index("ix_payslips_employee_id", "payslips", ["employee_id"])
    op.create_foreign_key(
        "fk_payslips_period_id",
        "payslips",
        "payroll_periods",
        ["period_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_payslips_employee_id",
        "payslips",
        "employees",
        ["employee_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_payslips_employee_id", "payslips", "foreignkey")
    op.drop_constraint("fk_payslips_period_id", "payslips", "foreignkey")
    op.drop_index("ix_payslips_employee_id", table_name="payslips")
    op.drop_index("ix_payslips_period_id", table_name="payslips")
    op.drop_table("payslips")