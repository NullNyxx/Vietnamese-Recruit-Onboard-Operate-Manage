"""Create leave_types table with seed data.

Revision ID: 014
Revises: 013
Create Date: 2026-05-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create leave_types table and seed default types."""
    op.create_table(
        "leave_types",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("default_days_per_year", sa.Integer(), server_default="0"),
        sa.Column("is_paid", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("requires_approval", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("requires_document", sa.Boolean(), server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Seed default leave types (Vietnamese labor law)
    op.execute("""
        INSERT INTO leave_types (id, name, display_name, default_days_per_year, is_paid, requires_approval, requires_document) VALUES
        (gen_random_uuid(), 'annual', 'Phép năm', 12, true, true, false),
        (gen_random_uuid(), 'sick', 'Nghỉ ốm', 30, true, true, true),
        (gen_random_uuid(), 'unpaid', 'Không lương', 0, false, true, false),
        (gen_random_uuid(), 'maternity', 'Thai sản', 180, true, true, true),
        (gen_random_uuid(), 'wedding', 'Kết hôn', 3, true, true, false),
        (gen_random_uuid(), 'funeral', 'Tang', 3, true, true, false),
        (gen_random_uuid(), 'personal', 'Việc riêng', 1, false, true, false)
    """)


def downgrade() -> None:
    """Drop leave_types table."""
    op.drop_table("leave_types")
