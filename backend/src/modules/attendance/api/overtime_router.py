"""FastAPI router for Overtime endpoints."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.attendance.application.overtime_service import OvertimeService
from src.modules.attendance.infrastructure.config import AttendanceSettings
from src.modules.attendance.infrastructure.overtime_repository import OvertimeRepository
from src.modules.identity.container import get_current_user, get_db_session
from src.modules.identity.domain.entities import User

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class OvertimeRequestCreate(BaseModel):
    employee_id: UUID
    work_date: date
    planned_hours: float = Field(gt=0, le=4)
    reason: str = Field(min_length=1, max_length=500)


class OvertimeRequestResponse(BaseModel):
    id: UUID
    employee_id: UUID
    work_date: date
    planned_hours: float
    actual_hours: float | None = None
    reason: str
    status: str
    approved_by: UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class OvertimeListResponse(BaseModel):
    items: list[OvertimeRequestResponse]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

CurrentUserDep = Annotated[User, Depends(get_current_user)]
DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


async def _get_overtime_service(session: DbSessionDep) -> OvertimeService:
    settings = AttendanceSettings()
    return OvertimeService(
        ot_repo=OvertimeRepository(session),
        settings=settings,
        session=session,
    )


OvertimeServiceDep = Annotated[OvertimeService, Depends(_get_overtime_service)]

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

overtime_router = APIRouter(prefix="/api/overtime", tags=["overtime"])


@overtime_router.post("/requests", response_model=OvertimeRequestResponse, status_code=201)
async def create_overtime_request(
    body: OvertimeRequestCreate,
    current_user: CurrentUserDep,
    service: OvertimeServiceDep,
) -> OvertimeRequestResponse:
    """Create an overtime request for an employee."""
    request = await service.submit_request(
        employee_id=body.employee_id,
        work_date=body.work_date,
        planned_hours=body.planned_hours,
        reason=body.reason,
    )
    return OvertimeRequestResponse.model_validate(request)


@overtime_router.get("/requests", response_model=OvertimeListResponse)
async def list_overtime_requests(
    current_user: CurrentUserDep,
    service: OvertimeServiceDep,
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> OvertimeListResponse:
    """List overtime requests with optional status filter."""
    items, total = await service.list_requests(status, page, page_size)
    return OvertimeListResponse(
        items=[OvertimeRequestResponse.model_validate(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@overtime_router.put("/requests/{request_id}/approve", response_model=OvertimeRequestResponse)
async def approve_overtime(
    request_id: UUID,
    current_user: CurrentUserDep,
    service: OvertimeServiceDep,
) -> OvertimeRequestResponse:
    """Approve an overtime request."""
    request = await service.approve(request_id, current_user.id)
    return OvertimeRequestResponse.model_validate(request)


@overtime_router.put("/requests/{request_id}/reject", response_model=OvertimeRequestResponse)
async def reject_overtime(
    request_id: UUID,
    current_user: CurrentUserDep,
    service: OvertimeServiceDep,
) -> OvertimeRequestResponse:
    """Reject an overtime request."""
    request = await service.reject(request_id)
    return OvertimeRequestResponse.model_validate(request)
