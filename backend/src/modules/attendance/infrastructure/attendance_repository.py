"""Repository for attendance records persistence."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from src.modules.attendance.domain.entities import AttendanceRecord


class AttendanceRepository:
    """Repository for AttendanceRecord CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_employee_date(
        self, employee_id: UUID, work_date: date
    ) -> AttendanceRecord | None:
        """Get attendance record for an employee on a specific date."""
        stmt = select(AttendanceRecord).where(
            AttendanceRecord.employee_id == employee_id,
            AttendanceRecord.work_date == work_date,
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def create(self, record: AttendanceRecord) -> AttendanceRecord:
        """Create a new attendance record."""
        self._session.add(record)
        await self._session.flush()
        await self._session.refresh(record)
        return record

    async def update(self, record: AttendanceRecord) -> AttendanceRecord:
        """Update an attendance record."""
        self._session.add(record)
        await self._session.flush()
        await self._session.refresh(record)
        return record

    async def get_monthly_report(
        self, employee_id: UUID, year: int, month: int
    ) -> list[AttendanceRecord]:
        """Get all attendance records for an employee in a month."""
        from datetime import date as date_type
        import calendar

        start = date_type(year, month, 1)
        _, last_day = calendar.monthrange(year, month)
        end = date_type(year, month, last_day)

        stmt = (
            select(AttendanceRecord)
            .where(
                AttendanceRecord.employee_id == employee_id,
                AttendanceRecord.work_date >= start,
                AttendanceRecord.work_date <= end,
            )
            .order_by(col(AttendanceRecord.work_date))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_team_by_date(
        self, work_date: date, department_id: UUID | None = None
    ) -> list[AttendanceRecord]:
        """Get attendance records for all employees on a date."""
        stmt = select(AttendanceRecord).where(
            AttendanceRecord.work_date == work_date
        )
        # Note: department filter would require a join with employees table
        # For now, return all records for the date
        stmt = stmt.order_by(col(AttendanceRecord.employee_id))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_employees_with_records_on_date(
        self, work_date: date
    ) -> set[UUID]:
        """Get set of employee IDs that have a record on a given date."""
        stmt = select(AttendanceRecord.employee_id).where(
            AttendanceRecord.work_date == work_date
        )
        result = await self._session.execute(stmt)
        return {row[0] for row in result.all()}

    async def bulk_create(self, records: list[AttendanceRecord]) -> None:
        """Create multiple attendance records at once."""
        for record in records:
            self._session.add(record)
        await self._session.flush()
