"""Drop attendance, leave, payroll, and related tables.

These modules have been removed from the application.
Tables are dropped in reverse dependency order.

Revision ID: 027
Revises: 026
Create Date: 2026-05-27
"""

from alembic import op
from sqlalchemy import inspect

revision: str = "027"
down_revision: str = "026"
branch_labels = None
depends_on = None


def _drop_if_exists(table_name: str) -> None:
    """Drop a table only if it exists in the database."""
    bind = op.get_bind()
    inspector = inspect(bind)
    if table_name in inspector.get_table_names():
        op.drop_table(table_name)


def upgrade() -> None:
    # Payroll tables (depend on employees)
    _drop_if_exists("payslips")
    _drop_if_exists("payroll_periods")
    _drop_if_exists("position_salaries")
    _drop_if_exists("allowances")
    _drop_if_exists("dependents")
    _drop_if_exists("salary_configs")

    # Attendance/Leave tables (depend on employees)
    _drop_if_exists("overtime_requests")
    _drop_if_exists("attendance_records")
    _drop_if_exists("leave_requests")
    _drop_if_exists("leave_balances")
    _drop_if_exists("work_schedules")
    _drop_if_exists("holidays")
    _drop_if_exists("leave_types")


def downgrade() -> None:
    # Downgrade is not supported — these modules have been removed.
    # To restore, re-run migrations 014-026.
    pass
