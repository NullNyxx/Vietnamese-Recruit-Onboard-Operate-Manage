"""Create dependents table.

Revision ID: 023
Revises: 022
Create Date: 2026-05-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "023"
down_revision: Union[str, None] = "022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dependents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("relationship", sa.String(length=50), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("tax_dependent", sa.Boolean(), server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dependents_employee_id", "dependents", ["employee_id"])
    op.create_foreign_key(
        "fk_dependents_employee_id",
        "dependents",
        "employees",
        ["employee_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_dependents_employee_id", "dependents", "foreignkey")
    op.drop_index("ix_dependents_employee_id", table_name="dependents")
    op.drop_table("dependents")