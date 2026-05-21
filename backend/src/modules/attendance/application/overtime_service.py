"""Service for managing overtime requests."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.attendance.domain.entities import OvertimeRequest
from src.modules.attendance.domain.enums import OvertimeStatus
from src.modules.attendance.domain.exceptions import (
    OvertimeLimitExceededError,
    OvertimeRequestNotFoundError,
)
from src.modules.attendance.infrastructure.config import AttendanceSettings
from src.modules.attendance.infrastructure.overtime_repository import OvertimeRepository


class OvertimeService:
    """Manages overtime request lifecycle.

    Args:
        ot_repo: Repository for overtime requests.
        settings: Attendance module settings.
        session: Database session.
    """

    def __init__(
        self,
        ot_repo: OvertimeRepository,
        settings: AttendanceSettings,
        session: AsyncSession,
    ) -> None:
        self._ot_repo = ot_repo
        self._settings = settings
        self._session = session

    async def submit_request(
        self,
        employee_id: UUID,
        work_date: "date",
        planned_hours: float,
        reason: str,
    ) -> OvertimeRequest:
        """Submit an overtime request.

        Validates daily and weekly OT limits.

        Raises:
            OvertimeLimitExceededError: If limits are exceeded.
        """
        from datetime import date

        # Validate daily limit
        if planned_hours > self._settings.max_ot_per_day_hours:
            raise OvertimeLimitExceededError(
                current_hours=planned_hours,
                max_hours=self._settings.max_ot_per_day_hours,
            )

        # Validate weekly limit
        weekly_hours = await self._ot_repo.get_weekly_hours(employee_id, work_date)
        if float(weekly_hours) + planned_hours > self._settings.max_ot_per_week_hours:
            raise OvertimeLimitExceededError(
                current_hours=float(weekly_hours) + planned_hours,
                max_hours=self._settings.max_ot_per_week_hours,
            )

        request = OvertimeRequest(
            employee_id=employee_id,
            work_date=work_date,
            planned_hours=Decimal(str(planned_hours)),
            reason=reason,
            status=OvertimeStatus.PENDING,
        )

        created = await self._ot_repo.create(request)
        await self._session.commit()
        return created

    async def approve(
        self, request_id: UUID, approved_by: UUID
    ) -> OvertimeRequest:
        """Approve an overtime request."""
        request = await self._ot_repo.get_by_id(request_id)
        if request is None:
            raise OvertimeRequestNotFoundError(str(request_id))

        request.status = OvertimeStatus.APPROVED
        request.approved_by = approved_by

        updated = await self._ot_repo.update(request)
        await self._session.commit()
        return updated

    async def reject(self, request_id: UUID) -> OvertimeRequest:
        """Reject an overtime request."""
        request = await self._ot_repo.get_by_id(request_id)
        if request is None:
            raise OvertimeRequestNotFoundError(str(request_id))

        request.status = OvertimeStatus.REJECTED

        updated = await self._ot_repo.update(request)
        await self._session.commit()
        return updated

    async def list_requests(
        self, status: str | None = None, page: int = 1, page_size: int = 20
    ) -> tuple[list[OvertimeRequest], int]:
        """List overtime requests with optional status filter."""
        return await self._ot_repo.list_by_status(status, page, page_size)
