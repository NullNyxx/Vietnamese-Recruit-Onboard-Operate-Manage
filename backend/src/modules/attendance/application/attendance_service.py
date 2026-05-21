"""Service for managing attendance records.

Handles check-in, check-out, status determination, and reporting.
All operations are HR-initiated.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.attendance.domain.entities import AttendanceRecord, WorkSchedule
from src.modules.attendance.domain.enums import AttendanceStatus
from src.modules.attendance.domain.exceptions import (
    AlreadyCheckedInError,
    AlreadyCheckedOutError,
    AttendanceRecordNotFoundError,
    NotCheckedInError,
    ScheduleNotFoundError,
)
from src.modules.attendance.infrastructure.attendance_repository import (
    AttendanceRepository,
)
from src.modules.attendance.infrastructure.schedule_repository import (
    HolidayRepository,
    ScheduleRepository,
)


class AttendanceService:
    """Manages daily attendance operations.

    Args:
        attendance_repo: Repository for attendance records.
        schedule_repo: Repository for work schedules.
        holiday_repo: Repository for holidays.
        session: Database session for transactions.
    """

    def __init__(
        self,
        attendance_repo: AttendanceRepository,
        schedule_repo: ScheduleRepository,
        holiday_repo: HolidayRepository,
        session: AsyncSession,
    ) -> None:
        self._attendance_repo = attendance_repo
        self._schedule_repo = schedule_repo
        self._holiday_repo = holiday_repo
        self._session = session

    async def check_in(
        self,
        employee_id: UUID,
        check_in_time: datetime | None = None,
    ) -> AttendanceRecord:
        """Record check-in for an employee.

        Args:
            employee_id: The employee UUID.
            check_in_time: Optional override time (defaults to now).

        Returns:
            The created AttendanceRecord.

        Raises:
            AlreadyCheckedInError: If already checked in today.
        """
        now = check_in_time or datetime.now(UTC)
        today = now.date()

        # Check if already checked in
        existing = await self._attendance_repo.get_by_employee_date(employee_id, today)
        if existing and existing.check_in:
            raise AlreadyCheckedInError()

        # Get schedule to determine status
        schedule = await self._schedule_repo.get_default()
        if schedule is None:
            raise ScheduleNotFoundError()

        # Determine status based on check-in time
        status = self._determine_checkin_status(now.time(), schedule)

        # Check if it's a holiday
        is_holiday = await self._holiday_repo.is_holiday(today)
        if is_holiday:
            status = AttendanceStatus.HOLIDAY

        record = AttendanceRecord(
            employee_id=employee_id,
            work_date=today,
            schedule_id=schedule.id,
            check_in=now,
            status=status,
        )

        created = await self._attendance_repo.create(record)
        await self._session.commit()
        return created

    async def check_out(
        self,
        employee_id: UUID,
        check_out_time: datetime | None = None,
    ) -> AttendanceRecord:
        """Record check-out for an employee.

        Calculates work hours and overtime based on schedule.

        Args:
            employee_id: The employee UUID.
            check_out_time: Optional override time (defaults to now).

        Returns:
            The updated AttendanceRecord.

        Raises:
            NotCheckedInError: If not checked in today.
            AlreadyCheckedOutError: If already checked out.
        """
        now = check_out_time or datetime.now(UTC)
        today = now.date()

        record = await self._attendance_repo.get_by_employee_date(employee_id, today)
        if record is None or record.check_in is None:
            raise NotCheckedInError()
        if record.check_out is not None:
            raise AlreadyCheckedOutError()

        # Get schedule
        schedule = await self._schedule_repo.get_default()
        if schedule is None:
            raise ScheduleNotFoundError()

        # Calculate work hours
        work_hours = self._calculate_work_hours(
            record.check_in, now, schedule.break_minutes
        )
        overtime = self._calculate_overtime(now.time(), schedule)

        # Update status if early leave
        status = record.status
        if self._is_early_leave(now.time(), schedule):
            status = AttendanceStatus.EARLY_LEAVE

        record.check_out = now
        record.work_hours = work_hours
        record.overtime_hours = overtime
        record.status = status
        record.updated_at = datetime.now(UTC)

        updated = await self._attendance_repo.update(record)
        await self._session.commit()
        return updated

    async def get_today(self, employee_id: UUID) -> AttendanceRecord | None:
        """Get today's attendance record for an employee."""
        today = datetime.now(UTC).date()
        return await self._attendance_repo.get_by_employee_date(employee_id, today)

    async def get_monthly_report(
        self, employee_id: UUID, year: int, month: int
    ) -> dict:
        """Get monthly attendance report for an employee.

        Returns summary statistics and daily records.
        """
        records = await self._attendance_repo.get_monthly_report(
            employee_id, year, month
        )

        # Calculate summary
        present_days = sum(1 for r in records if r.status in ("present", "late", "early_leave"))
        late_days = sum(1 for r in records if r.status == "late")
        absent_days = sum(1 for r in records if r.status == "absent")
        leave_days = sum(1 for r in records if r.status == "on_leave")
        total_work_hours = sum(float(r.work_hours or 0) for r in records)
        total_ot_hours = sum(float(r.overtime_hours or 0) for r in records)

        return {
            "employee_id": employee_id,
            "year": year,
            "month": month,
            "summary": {
                "present_days": present_days,
                "late_days": late_days,
                "absent_days": absent_days,
                "leave_days": leave_days,
                "total_work_hours": round(total_work_hours, 2),
                "total_overtime_hours": round(total_ot_hours, 2),
            },
            "records": records,
        }

    async def get_team_today(
        self, work_date: date | None = None
    ) -> list[AttendanceRecord]:
        """Get attendance records for all employees on a date."""
        target_date = work_date or datetime.now(UTC).date()
        return await self._attendance_repo.get_team_by_date(target_date)

    async def manual_record(
        self,
        employee_id: UUID,
        work_date: date,
        check_in: datetime | None,
        check_out: datetime | None,
        status: str,
        note: str | None = None,
    ) -> AttendanceRecord:
        """HR manually creates/updates an attendance record.

        Used for corrections or when importing from external systems.
        """
        existing = await self._attendance_repo.get_by_employee_date(
            employee_id, work_date
        )

        work_hours = None
        overtime = Decimal("0")

        # Keep original timezone for DB storage (DB supports TIMESTAMP WITH TIME ZONE)
        # But use local time values for schedule comparison
        check_in_local_time = check_in.replace(tzinfo=None).time() if check_in else None
        check_out_local_time = check_out.replace(tzinfo=None).time() if check_out else None

        # Auto-calculate status and hours from check-in/check-out
        if check_in and check_out:
            schedule = await self._schedule_repo.get_default()
            break_mins = schedule.break_minutes if schedule else 60
            # Calculate work hours using naive datetimes (strip tz for math)
            cin_naive = check_in.replace(tzinfo=None) if check_in.tzinfo else check_in
            cout_naive = check_out.replace(tzinfo=None) if check_out.tzinfo else check_out
            work_hours = self._calculate_work_hours(cin_naive, cout_naive, break_mins)

            if schedule and check_in_local_time and check_out_local_time:
                overtime = self._calculate_overtime(check_out_local_time, schedule)
                # Auto-determine status based on actual local times
                status = self._determine_checkin_status(check_in_local_time, schedule)
                if self._is_early_leave(check_out_local_time, schedule):
                    status = AttendanceStatus.EARLY_LEAVE
        elif check_in and not check_out:
            schedule = await self._schedule_repo.get_default()
            if schedule and check_in_local_time:
                status = self._determine_checkin_status(check_in_local_time, schedule)

        if existing:
            existing.check_in = check_in
            existing.check_out = check_out
            existing.work_hours = work_hours
            existing.overtime_hours = overtime
            existing.status = status
            existing.note = note
            existing.updated_at = datetime.now(UTC)
            updated = await self._attendance_repo.update(existing)
            await self._session.commit()
            return updated

        record = AttendanceRecord(
            employee_id=employee_id,
            work_date=work_date,
            check_in=check_in,
            check_out=check_out,
            work_hours=work_hours,
            overtime_hours=overtime,
            status=status,
            note=note,
        )
        created = await self._attendance_repo.create(record)
        await self._session.commit()
        return created

    # ─── Private helpers ───────────────────────────────────────────────

    def _determine_checkin_status(
        self, checkin_time: time, schedule: WorkSchedule
    ) -> str:
        """Determine attendance status based on check-in time."""
        threshold_minutes = schedule.late_threshold_minutes
        schedule_start = schedule.start_time

        # Calculate late threshold time
        start_dt = datetime.combine(date.today(), schedule_start)
        threshold_dt = start_dt + timedelta(minutes=threshold_minutes)
        threshold_time = threshold_dt.time()

        if checkin_time > threshold_time:
            return AttendanceStatus.LATE
        return AttendanceStatus.PRESENT

    def _is_early_leave(self, checkout_time: time, schedule: WorkSchedule) -> bool:
        """Check if checkout time counts as early leave."""
        end_dt = datetime.combine(date.today(), schedule.end_time)
        threshold_dt = end_dt - timedelta(minutes=schedule.early_leave_threshold_minutes)
        return checkout_time < threshold_dt.time()

    def _calculate_work_hours(
        self, check_in: datetime, check_out: datetime, break_minutes: int
    ) -> Decimal:
        """Calculate total work hours minus break time."""
        diff = (check_out - check_in).total_seconds() / 3600
        break_hours = break_minutes / 60
        work = max(0, diff - break_hours)
        return Decimal(str(round(work, 2)))

    def _calculate_overtime(
        self, checkout_time: time, schedule: WorkSchedule
    ) -> Decimal:
        """Calculate overtime hours (time after schedule end)."""
        end_dt = datetime.combine(date.today(), schedule.end_time)
        checkout_dt = datetime.combine(date.today(), checkout_time)

        if checkout_dt <= end_dt:
            return Decimal("0")

        ot_seconds = (checkout_dt - end_dt).total_seconds()
        ot_hours = ot_seconds / 3600
        return Decimal(str(round(ot_hours, 2)))
