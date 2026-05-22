"""Create work_schedules table with default schedule.

Revision ID: 017
Revises: 016
Create Date: 2026-05-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create work_schedules table and seed default schedule."""
    op.create_table(
        "work_schedules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("break_minutes", sa.Integer(), server_default="60"),
        sa.Column("late_threshold_minutes", sa.Integer(), server_default="15"),
        sa.Column("early_leave_threshold_minutes", sa.Integer(), server_default="15"),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Seed default work schedule
    op.execute("""
        INSERT INTO work_schedules (id, name, start_time, end_time, break_minutes, late_threshold_minutes, early_leave_threshold_minutes, is_default)
        VALUES (gen_random_uuid(), 'Ca hành chính', '08:00:00', '17:00:00', 60, 15, 15, true)
    """)


def downgrade() -> None:
    """Drop work_schedules table."""
    op.drop_table("work_schedules")
