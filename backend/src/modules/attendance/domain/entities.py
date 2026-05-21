"""Domain entities for the Attendance & Leave module.

Defines SQLModel table classes for leave management, attendance tracking,
overtime requests, work schedules, and holidays.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel


# ---------------------------------------------------------------------------
# Leave Management
# ---------------------------------------------------------------------------


class LeaveType(SQLModel, table=True):
    """Represents a category of leave (annual, sick, etc.).

    Stores configuration for each leave type including default days
    per year and whether approval/documentation is required.
    """

    __tablename__ = "leave_types"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(max_length=50, unique=True, nullable=False)
    display_name: str = Field(max_length=100, nullable=False)
    default_days_per_year: int = Field(default=0)
    is_paid: bool = Field(default=True)
    requires_approval: bool = Field(default=True)
    requires_document: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class LeaveBalance(SQLModel, table=True):
    """Tracks remaining leave days for an employee per type per year.

    Updated when leave requests are approved or cancelled.
    Initialized at the start of each year based on seniority.
    """

    __tablename__ = "leave_balances"
    __table_args__ = (
        UniqueConstraint("employee_id", "leave_type_id", "year", name="uq_leave_balance"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    employee_id: UUID = Field(foreign_key="employees.id", nullable=False, index=True)
    leave_type_id: UUID = Field(foreign_key="leave_types.id", nullable=False)
    year: int = Field(nullable=False)
    total_days: Decimal = Field(max_digits=5, decimal_places=1, nullable=False)
    used_days: Decimal = Field(default=Decimal("0"), max_digits=5, decimal_places=1)
    remaining_days: Decimal = Field(max_digits=5, decimal_places=1, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class LeaveRequest(SQLModel, table=True):
    """Represents a leave request submitted by HR on behalf of an employee.

    Tracks the full lifecycle: pending → approved/rejected/cancelled.
    When approved, the corresponding LeaveBalance is deducted.
    When cancelled (if previously approved), the balance is restored.
    """

    __tablename__ = "leave_requests"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    employee_id: UUID = Field(foreign_key="employees.id", nullable=False, index=True)
    leave_type_id: UUID = Field(foreign_key="leave_types.id", nullable=False)
    start_date: date = Field(nullable=False)
    end_date: date = Field(nullable=False)
    total_days: Decimal = Field(max_digits=5, decimal_places=1, nullable=False)
    reason: str | None = Field(default=None)
    status: str = Field(default="pending", max_length=20)
    approved_by: UUID | None = Field(default=None, foreign_key="users.id")
    approved_at: datetime | None = Field(default=None)
    rejection_reason: str | None = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


# ---------------------------------------------------------------------------
# Attendance Tracking
# ---------------------------------------------------------------------------


class WorkSchedule(SQLModel, table=True):
    """Defines a work shift with start/end times and thresholds.

    The default schedule (is_default=True) is used for employees
    without a specific schedule assignment.
    """

    __tablename__ = "work_schedules"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(max_length=100, nullable=False)
    start_time: time = Field(nullable=False)
    end_time: time = Field(nullable=False)
    break_minutes: int = Field(default=60)
    late_threshold_minutes: int = Field(default=15)
    early_leave_threshold_minutes: int = Field(default=15)
    is_default: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class AttendanceRecord(SQLModel, table=True):
    """Records daily attendance for an employee.

    One record per employee per day. Status is determined by comparing
    check-in/out times against the work schedule thresholds.
    """

    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint("employee_id", "work_date", name="uq_attendance_employee_date"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    employee_id: UUID = Field(foreign_key="employees.id", nullable=False, index=True)
    work_date: date = Field(nullable=False)
    schedule_id: UUID | None = Field(default=None, foreign_key="work_schedules.id")
    check_in: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    check_out: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    work_hours: Decimal | None = Field(default=None, max_digits=4, decimal_places=2)
    overtime_hours: Decimal = Field(default=Decimal("0"), max_digits=4, decimal_places=2)
    status: str = Field(max_length=20, nullable=False)
    note: str | None = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class OvertimeRequest(SQLModel, table=True):
    """Tracks overtime registration and approval.

    HR creates OT requests for employees. Once approved, the actual
    hours are recorded from the attendance check-out time.
    """

    __tablename__ = "overtime_requests"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    employee_id: UUID = Field(foreign_key="employees.id", nullable=False, index=True)
    work_date: date = Field(nullable=False)
    planned_hours: Decimal = Field(max_digits=4, decimal_places=2, nullable=False)
    actual_hours: Decimal | None = Field(default=None, max_digits=4, decimal_places=2)
    reason: str = Field(nullable=False)
    status: str = Field(default="pending", max_length=20)
    approved_by: UUID | None = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class Holiday(SQLModel, table=True):
    """Represents a public holiday or company day off.

    Used to exclude holidays from working day calculations
    and to mark attendance records as 'holiday' status.
    """

    __tablename__ = "holidays"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    holiday_date: date = Field(nullable=False)
    name: str = Field(max_length=200, nullable=False)
    is_recurring: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
