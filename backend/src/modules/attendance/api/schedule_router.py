"""FastAPI router for Work Schedules and Holidays endpoints."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.attendance.domain.entities import Holiday, WorkSchedule
from src.modules.attendance.infrastructure.schedule_repository import (
    HolidayRepository,
    ScheduleRepository,
)
from src.modules.identity.container import get_current_user, get_db_session
from src.modules.identity.domain.entities import User

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class WorkScheduleResponse(BaseModel):
    id: UUID
    name: str
    start_time: time
    end_time: time
    break_minutes: int
    late_threshold_minutes: int
    early_leave_threshold_minutes: int
    is_default: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkScheduleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    start_time: time
    end_time: time
    break_minutes: int = Field(default=60, ge=0, le=120)
    late_threshold_minutes: int = Field(default=15, ge=0, le=60)
    early_leave_threshold_minutes: int = Field(default=15, ge=0, le=60)
    is_default: bool = False


class HolidayResponse(BaseModel):
    id: UUID
    holiday_date: date
    name: str
    is_recurring: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class HolidayCreate(BaseModel):
    holiday_date: date
    name: str = Field(min_length=1, max_length=200)
    is_recurring: bool = False


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

CurrentUserDep = Annotated[User, Depends(get_current_user)]
DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

schedule_router = APIRouter(prefix="/api", tags=["schedules"])


# --- Work Schedules ---

@schedule_router.get("/schedules", response_model=list[WorkScheduleResponse])
async def list_schedules(
    current_user: CurrentUserDep,
    session: DbSessionDep,
) -> list[WorkScheduleResponse]:
    """List all work schedules."""
    repo = ScheduleRepository(session)
    schedules = await repo.list_all()
    return [WorkScheduleResponse.model_validate(s) for s in schedules]


@schedule_router.post("/schedules", response_model=WorkScheduleResponse, status_code=201)
async def create_schedule(
    body: WorkScheduleCreate,
    current_user: CurrentUserDep,
    session: DbSessionDep,
) -> WorkScheduleResponse:
    """Create a new work schedule."""
    repo = ScheduleRepository(session)
    schedule = WorkSchedule(
        name=body.name,
        start_time=body.start_time,
        end_time=body.end_time,
        break_minutes=body.break_minutes,
        late_threshold_minutes=body.late_threshold_minutes,
        early_leave_threshold_minutes=body.early_leave_threshold_minutes,
        is_default=body.is_default,
    )
    created = await repo.create(schedule)
    await session.commit()
    return WorkScheduleResponse.model_validate(created)


# --- Holidays ---

@schedule_router.get("/holidays", response_model=list[HolidayResponse])
async def list_holidays(
    current_user: CurrentUserDep,
    session: DbSessionDep,
    year: int = Query(default=2026, ge=2020, le=2100),
) -> list[HolidayResponse]:
    """List all holidays for a given year."""
    repo = HolidayRepository(session)
    holidays = await repo.list_by_year(year)
    return [HolidayResponse.model_validate(h) for h in holidays]


@schedule_router.post("/holidays", response_model=HolidayResponse, status_code=201)
async def create_holiday(
    body: HolidayCreate,
    current_user: CurrentUserDep,
    session: DbSessionDep,
) -> HolidayResponse:
    """Create a new holiday."""
    repo = HolidayRepository(session)
    holiday = Holiday(
        holiday_date=body.holiday_date,
        name=body.name,
        is_recurring=body.is_recurring,
    )
    created = await repo.create(holiday)
    await session.commit()
    return HolidayResponse.model_validate(created)


@schedule_router.delete("/holidays/{holiday_id}", status_code=204)
async def delete_holiday(
    holiday_id: UUID,
    current_user: CurrentUserDep,
    session: DbSessionDep,
) -> None:
    """Delete a holiday."""
    repo = HolidayRepository(session)
    await repo.delete(holiday_id)
    await session.commit()
