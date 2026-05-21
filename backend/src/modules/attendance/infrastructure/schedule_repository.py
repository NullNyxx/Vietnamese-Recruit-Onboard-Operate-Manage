"""Repository for work schedules and holidays persistence."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from src.modules.attendance.domain.entities import Holiday, WorkSchedule


class ScheduleRepository:
    """Repository for WorkSchedule CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_default(self) -> WorkSchedule | None:
        """Get the default work schedule."""
        stmt = select(WorkSchedule).where(WorkSchedule.is_default == True)
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def get_by_id(self, schedule_id: UUID) -> WorkSchedule | None:
        """Get a work schedule by ID."""
        stmt = select(WorkSchedule).where(WorkSchedule.id == schedule_id)
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def list_all(self) -> list[WorkSchedule]:
        """List all work schedules."""
        stmt = select(WorkSchedule).order_by(col(WorkSchedule.name))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, schedule: WorkSchedule) -> WorkSchedule:
        """Create a new work schedule."""
        self._session.add(schedule)
        await self._session.flush()
        await self._session.refresh(schedule)
        return schedule

    async def update(self, schedule: WorkSchedule) -> WorkSchedule:
        """Update a work schedule."""
        self._session.add(schedule)
        await self._session.flush()
        await self._session.refresh(schedule)
        return schedule


class HolidayRepository:
    """Repository for Holiday CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_year(self, year: int) -> list[Holiday]:
        """List all holidays for a given year."""
        from datetime import date as date_type

        start = date_type(year, 1, 1)
        end = date_type(year, 12, 31)

        stmt = (
            select(Holiday)
            .where(Holiday.holiday_date >= start, Holiday.holiday_date <= end)
            .order_by(col(Holiday.holiday_date))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def is_holiday(self, check_date: date) -> bool:
        """Check if a given date is a holiday."""
        stmt = select(Holiday).where(Holiday.holiday_date == check_date)
        result = await self._session.execute(stmt)
        return result.scalars().first() is not None

    async def create(self, holiday: Holiday) -> Holiday:
        """Create a new holiday."""
        self._session.add(holiday)
        await self._session.flush()
        await self._session.refresh(holiday)
        return holiday

    async def delete(self, holiday_id: UUID) -> None:
        """Delete a holiday."""
        stmt = select(Holiday).where(Holiday.id == holiday_id)
        result = await self._session.execute(stmt)
        holiday = result.scalars().first()
        if holiday:
            await self._session.delete(holiday)
            await self._session.flush()
