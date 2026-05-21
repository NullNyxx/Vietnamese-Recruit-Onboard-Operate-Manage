"""Repository for overtime requests persistence."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from src.modules.attendance.domain.entities import OvertimeRequest


class OvertimeRepository:
    """Repository for OvertimeRequest CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, request: OvertimeRequest) -> OvertimeRequest:
        """Create a new overtime request."""
        self._session.add(request)
        await self._session.flush()
        await self._session.refresh(request)
        return request

    async def get_by_id(self, request_id: UUID) -> OvertimeRequest | None:
        """Get an overtime request by ID."""
        stmt = select(OvertimeRequest).where(OvertimeRequest.id == request_id)
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def update(self, request: OvertimeRequest) -> OvertimeRequest:
        """Update an overtime request."""
        self._session.add(request)
        await self._session.flush()
        await self._session.refresh(request)
        return request

    async def get_weekly_hours(
        self, employee_id: UUID, reference_date: date
    ) -> Decimal:
        """Get total approved OT hours for the week containing reference_date."""
        # Find Monday of the week
        monday = reference_date - timedelta(days=reference_date.weekday())
        sunday = monday + timedelta(days=6)

        stmt = select(func.coalesce(func.sum(OvertimeRequest.planned_hours), 0)).where(
            OvertimeRequest.employee_id == employee_id,
            OvertimeRequest.status == "approved",
            OvertimeRequest.work_date >= monday,
            OvertimeRequest.work_date <= sunday,
        )
        result = await self._session.execute(stmt)
        return Decimal(str(result.scalar() or 0))

    async def list_by_status(
        self, status: str | None = None, page: int = 1, page_size: int = 20
    ) -> tuple[list[OvertimeRequest], int]:
        """List overtime requests with optional status filter."""
        stmt = select(OvertimeRequest)
        count_base = select(OvertimeRequest)

        if status:
            stmt = stmt.where(OvertimeRequest.status == status)
            count_base = count_base.where(OvertimeRequest.status == status)

        count_result = await self._session.execute(
            select(func.count()).select_from(count_base.subquery())
        )
        total = count_result.scalar() or 0

        stmt = (
            stmt.order_by(col(OvertimeRequest.created_at).desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_approved_monthly(
        self, employee_id: UUID, year: int, month: int
    ) -> list[OvertimeRequest]:
        """Get approved OT requests for an employee in a month."""
        import calendar
        from datetime import date as date_type

        start = date_type(year, month, 1)
        _, last_day = calendar.monthrange(year, month)
        end = date_type(year, month, last_day)

        stmt = select(OvertimeRequest).where(
            OvertimeRequest.employee_id == employee_id,
            OvertimeRequest.status == "approved",
            OvertimeRequest.work_date >= start,
            OvertimeRequest.work_date <= end,
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
