"""Dependency injection container for the Attendance module."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.attendance.application.balance_service import BalanceService
from src.modules.attendance.application.leave_service import LeaveService
from src.modules.attendance.infrastructure.config import AttendanceSettings
from src.modules.attendance.infrastructure.leave_repository import (
    LeaveBalanceRepository,
    LeaveRequestRepository,
    LeaveTypeRepository,
)
from src.modules.identity.container import get_db_session


def get_attendance_settings() -> AttendanceSettings:
    """Provide AttendanceSettings singleton."""
    return AttendanceSettings()


async def get_leave_service(
    session: AsyncSession = None,
) -> LeaveService:
    """Provide a LeaveService with all dependencies.

    This is used as a FastAPI dependency.
    """
    from fastapi import Depends

    # This function is called via Depends, session comes from get_db_session
    if session is None:
        raise RuntimeError("Session must be provided")

    settings = get_attendance_settings()
    type_repo = LeaveTypeRepository(session)
    balance_repo = LeaveBalanceRepository(session)
    request_repo = LeaveRequestRepository(session)
    balance_service = BalanceService(balance_repo, type_repo, settings)

    return LeaveService(
        request_repo=request_repo,
        type_repo=type_repo,
        balance_service=balance_service,
        session=session,
    )


async def get_balance_service(
    session: AsyncSession = None,
) -> BalanceService:
    """Provide a BalanceService with all dependencies."""
    if session is None:
        raise RuntimeError("Session must be provided")

    settings = get_attendance_settings()
    type_repo = LeaveTypeRepository(session)
    balance_repo = LeaveBalanceRepository(session)

    return BalanceService(balance_repo, type_repo, settings)


async def get_leave_type_repo(
    session: AsyncSession = None,
) -> LeaveTypeRepository:
    """Provide a LeaveTypeRepository."""
    if session is None:
        raise RuntimeError("Session must be provided")
    return LeaveTypeRepository(session)
