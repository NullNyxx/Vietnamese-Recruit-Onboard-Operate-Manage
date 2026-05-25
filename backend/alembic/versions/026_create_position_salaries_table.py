"""Create position_salaries table.

Revision ID: 026
Revises: 025
Create Date: 2026-05-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "026"
down_revision: Union[str, None] = "025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "position_salaries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("position_id", sa.Uuid(), nullable=False),
        sa.Column("grade", sa.String(length=10), nullable=False, server_default="A"),
        sa.Column("min_salary", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("mid_salary", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("max_salary", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_position_salaries_position_id", "position_salaries", ["position_id"])
    op.create_foreign_key(
        "fk_position_salaries_position_id",
        "position_salaries",
        "positions",
        ["position_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_position_salaries_position_id", "position_salaries", "foreignkey")
    op.drop_index("ix_position_salaries_position_id", table_name="position_salaries")
    op.drop_table("position_salaries")