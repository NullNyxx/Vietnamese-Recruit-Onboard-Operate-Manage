"""Create allowances table.

Revision ID: 022
Revises: 021
Create Date: 2026-05-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "022"
down_revision: Union[str, None] = "021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "allowances",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("allowance_type", sa.String(length=50), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("is_taxable", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_allowances_employee_id", "allowances", ["employee_id"])
    op.create_foreign_key(
        "fk_allowances_employee_id",
        "allowances",
        "employees",
        ["employee_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_allowances_employee_id", "allowances", "foreignkey")
    op.drop_index("ix_allowances_employee_id", table_name="allowances")
    op.drop_table("allowances")