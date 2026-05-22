"""Create attendance_records table.

Revision ID: 018
Revises: 017
Create Date: 2026-05-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create attendance_records table."""
    op.create_table(
        "attendance_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("schedule_id", sa.Uuid(), nullable=True),
        sa.Column("check_in", sa.DateTime(timezone=True), nullable=True),
        sa.Column("check_out", sa.DateTime(timezone=True), nullable=True),
        sa.Column("work_hours", sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column(
            "overtime_hours",
            sa.Numeric(precision=4, scale=2),
            server_default="0",
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["schedule_id"], ["work_schedules.id"]),
        sa.UniqueConstraint("employee_id", "work_date", name="uq_attendance_employee_date"),
    )

    op.create_index("ix_attendance_records_employee_id", "attendance_records", ["employee_id"])
    op.create_index("ix_attendance_records_work_date", "attendance_records", ["work_date"])


def downgrade() -> None:
    """Drop attendance_records table."""
    op.drop_index("ix_attendance_records_work_date", table_name="attendance_records")
    op.drop_index("ix_attendance_records_employee_id", table_name="attendance_records")
    op.drop_table("attendance_records")
