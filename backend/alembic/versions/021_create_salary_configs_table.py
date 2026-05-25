"""Create salary_configs table.

Revision ID: 021
Revises: 020
Create Date: 2026-05-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "021"
down_revision: Union[str, None] = "020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "salary_configs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("gross_salary", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("insurance_salary", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("contract_type", sa.String(length=20), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
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
        sa.UniqueConstraint("employee_id", name="uq_salary_config_employee"),
    )
    op.create_index("ix_salary_configs_employee_id", "salary_configs", ["employee_id"])


def downgrade() -> None:
    op.drop_index("ix_salary_configs_employee_id", table_name="salary_configs")
    op.drop_table("salary_configs")