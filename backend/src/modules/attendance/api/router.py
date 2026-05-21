"""FastAPI router for the Leave Management endpoints.

All endpoints are HR-only (authenticated via get_current_user).
HR manages leave on behalf of employees.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.attendance.api.schemas import (
    InitializeBalanceRequest,
    LeaveBalanceResponse,
    LeaveRequestCreate,
    LeaveRequestListResponse,
    LeaveRequestResponse,
    LeaveTypeResponse,
    RejectRequest,
)
from src.modules.attendance.application.balance_service import BalanceService
from src.modules.attendance.application.leave_service import LeaveService
from src.modules.attendance.infrastructure.config import AttendanceSettings
from src.modules.attendance.infrastructure.leave_repository import (
    LeaveBalanceRepository,
    LeaveRequestRepository,
    LeaveTypeRepository,
)
from src.modules.identity.container import get_current_user, get_db_session
from src.modules.identity.domain.entities import User

# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

CurrentUserDep = Annotated[User, Depends(get_current_user)]
DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


async def _get_leave_service(session: DbSessionDep) -> LeaveService:
    settings = AttendanceSettings()
    type_repo = LeaveTypeRepository(session)
    balance_repo = LeaveBalanceRepository(session)
    request_repo = LeaveRequestRepository(session)
    balance_service = BalanceService(balance_repo, type_repo, settings)
    return LeaveService(request_repo, type_repo, balance_service, session)


async def _get_balance_service(session: DbSessionDep) -> BalanceService:
    settings = AttendanceSettings()
    type_repo = LeaveTypeRepository(session)
    balance_repo = LeaveBalanceRepository(session)
    return BalanceService(balance_repo, type_repo, settings)


LeaveServiceDep = Annotated[LeaveService, Depends(_get_leave_service)]
BalanceServiceDep = Annotated[BalanceService, Depends(_get_balance_service)]

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

leave_router = APIRouter(prefix="/api/leave", tags=["leave"])


# ---------------------------------------------------------------------------
# Leave Types
# ---------------------------------------------------------------------------


@leave_router.get("/types", response_model=list[LeaveTypeResponse])
async def list_leave_types(
    current_user: CurrentUserDep,
    session: DbSessionDep,
) -> list[LeaveTypeResponse]:
    """List all available leave types."""
    repo = LeaveTypeRepository(session)
    types = await repo.list_all()
    return [LeaveTypeResponse.model_validate(t) for t in types]


# ---------------------------------------------------------------------------
# Leave Balances
# ---------------------------------------------------------------------------


@leave_router.get(
    "/balance/{employee_id}", response_model=list[LeaveBalanceResponse]
)
async def get_employee_balance(
    employee_id: UUID,
    current_user: CurrentUserDep,
    balance_service: BalanceServiceDep,
    year: int = Query(default=2026, ge=2020, le=2100),
) -> list[LeaveBalanceResponse]:
    """Get leave balances for an employee in a given year."""
    balances = await balance_service.get_employee_balances(employee_id, year)
    return [LeaveBalanceResponse.model_validate(b) for b in balances]


@leave_router.post(
    "/balance/initialize",
    response_model=list[LeaveBalanceResponse],
    status_code=201,
)
async def initialize_balance(
    body: InitializeBalanceRequest,
    current_user: CurrentUserDep,
    balance_service: BalanceServiceDep,
) -> list[LeaveBalanceResponse]:
    """Initialize leave balances for an employee (typically done at year start)."""
    balances = await balance_service.initialize_employee_balance(
        employee_id=body.employee_id,
        year=body.year,
        start_date=body.start_date,
    )
    return [LeaveBalanceResponse.model_validate(b) for b in balances]


# ---------------------------------------------------------------------------
# Leave Requests
# ---------------------------------------------------------------------------


@leave_router.get("/requests", response_model=LeaveRequestListResponse)
async def list_leave_requests(
    current_user: CurrentUserDep,
    leave_service: LeaveServiceDep,
    employee_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> LeaveRequestListResponse:
    """List leave requests with optional filters.

    If employee_id is omitted, returns pending requests (HR approval view).
    """
    items, total = await leave_service.list_requests(
        employee_id=employee_id,
        status=status,
        page=page,
        page_size=page_size,
    )
    return LeaveRequestListResponse(
        items=[LeaveRequestResponse.model_validate(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@leave_router.post(
    "/requests", response_model=LeaveRequestResponse, status_code=201
)
async def create_leave_request(
    body: LeaveRequestCreate,
    current_user: CurrentUserDep,
    leave_service: LeaveServiceDep,
) -> LeaveRequestResponse:
    """Create a new leave request (HR submits on behalf of employee)."""
    request = await leave_service.submit_request(
        employee_id=body.employee_id,
        leave_type_id=body.leave_type_id,
        start_date=body.start_date,
        end_date=body.end_date,
        reason=body.reason,
    )
    return LeaveRequestResponse.model_validate(request)


@leave_router.put(
    "/requests/{request_id}/approve", response_model=LeaveRequestResponse
)
async def approve_leave_request(
    request_id: UUID,
    current_user: CurrentUserDep,
    leave_service: LeaveServiceDep,
) -> LeaveRequestResponse:
    """Approve a pending leave request."""
    try:
        request = await leave_service.approve_request(request_id, current_user.id)
        return LeaveRequestResponse.model_validate(request)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("approve error: %s", exc, exc_info=True)
        raise


@leave_router.put(
    "/requests/{request_id}/reject", response_model=LeaveRequestResponse
)
async def reject_leave_request(
    request_id: UUID,
    current_user: CurrentUserDep,
    leave_service: LeaveServiceDep,
    body: RejectRequest | None = None,
) -> LeaveRequestResponse:
    """Reject a pending leave request."""
    reason = body.reason if body else None
    request = await leave_service.reject_request(request_id, reason)
    return LeaveRequestResponse.model_validate(request)


@leave_router.put(
    "/requests/{request_id}/cancel", response_model=LeaveRequestResponse
)
async def cancel_leave_request(
    request_id: UUID,
    current_user: CurrentUserDep,
    leave_service: LeaveServiceDep,
) -> LeaveRequestResponse:
    """Cancel a leave request. Restores balance if previously approved."""
    request = await leave_service.cancel_request(request_id)
    return LeaveRequestResponse.model_validate(request)
