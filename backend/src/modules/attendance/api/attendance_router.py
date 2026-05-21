"""FastAPI router for Attendance endpoints.

HR manages attendance records: check-in/out, reports, manual entry.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.attendance.application.attendance_service import AttendanceService
from src.modules.attendance.application.export_service import ExportService
from src.modules.attendance.domain.entities import AttendanceRecord
from src.modules.attendance.infrastructure.attendance_repository import AttendanceRepository
from src.modules.attendance.infrastructure.config import AttendanceSettings
from src.modules.attendance.infrastructure.schedule_repository import (
    HolidayRepository,
    ScheduleRepository,
)
from src.modules.identity.container import get_current_user, get_db_session
from src.modules.identity.domain.entities import User

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CheckInRequest(BaseModel):
    employee_id: UUID
    check_in_time: datetime | None = None  # Defaults to now


class CheckOutRequest(BaseModel):
    employee_id: UUID
    check_out_time: datetime | None = None


class ManualRecordRequest(BaseModel):
    employee_id: UUID
    work_date: date
    check_in: datetime | None = None
    check_out: datetime | None = None
    status: str = Field(max_length=20)
    note: str | None = None


class AttendanceRecordResponse(BaseModel):
    id: UUID
    employee_id: UUID
    work_date: date
    check_in: datetime | None = None
    check_out: datetime | None = None
    work_hours: float | None = None
    overtime_hours: float = 0
    status: str
    note: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MonthlyReportResponse(BaseModel):
    employee_id: UUID
    year: int
    month: int
    summary: dict
    records: list[AttendanceRecordResponse]


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

CurrentUserDep = Annotated[User, Depends(get_current_user)]
DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


async def _get_attendance_service(session: DbSessionDep) -> AttendanceService:
    return AttendanceService(
        attendance_repo=AttendanceRepository(session),
        schedule_repo=ScheduleRepository(session),
        holiday_repo=HolidayRepository(session),
        session=session,
    )


AttendanceServiceDep = Annotated[AttendanceService, Depends(_get_attendance_service)]

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

attendance_router = APIRouter(prefix="/api/attendance", tags=["attendance"])


@attendance_router.post("/check-in", response_model=AttendanceRecordResponse, status_code=201)
async def check_in(
    body: CheckInRequest,
    current_user: CurrentUserDep,
    service: AttendanceServiceDep,
) -> AttendanceRecordResponse:
    """Record check-in for an employee (HR action)."""
    record = await service.check_in(body.employee_id, body.check_in_time)
    return AttendanceRecordResponse.model_validate(record)


@attendance_router.post("/check-out", response_model=AttendanceRecordResponse)
async def check_out(
    body: CheckOutRequest,
    current_user: CurrentUserDep,
    service: AttendanceServiceDep,
) -> AttendanceRecordResponse:
    """Record check-out for an employee (HR action)."""
    record = await service.check_out(body.employee_id, body.check_out_time)
    return AttendanceRecordResponse.model_validate(record)


@attendance_router.get("/today/{employee_id}", response_model=AttendanceRecordResponse | None)
async def get_today(
    employee_id: UUID,
    current_user: CurrentUserDep,
    service: AttendanceServiceDep,
) -> AttendanceRecordResponse | None:
    """Get today's attendance record for an employee."""
    record = await service.get_today(employee_id)
    if record is None:
        return None
    return AttendanceRecordResponse.model_validate(record)


@attendance_router.get("/report/{employee_id}", response_model=MonthlyReportResponse)
async def get_monthly_report(
    employee_id: UUID,
    current_user: CurrentUserDep,
    service: AttendanceServiceDep,
    year: int = Query(default=2026, ge=2020, le=2100),
    month: int = Query(default=5, ge=1, le=12),
) -> MonthlyReportResponse:
    """Get monthly attendance report for an employee."""
    report = await service.get_monthly_report(employee_id, year, month)
    return MonthlyReportResponse(
        employee_id=report["employee_id"],
        year=report["year"],
        month=report["month"],
        summary=report["summary"],
        records=[AttendanceRecordResponse.model_validate(r) for r in report["records"]],
    )


@attendance_router.get("/team", response_model=list[AttendanceRecordResponse])
async def get_team_today(
    current_user: CurrentUserDep,
    service: AttendanceServiceDep,
    work_date: date | None = Query(default=None),
) -> list[AttendanceRecordResponse]:
    """Get attendance records for all employees on a date (default: today)."""
    records = await service.get_team_today(work_date)
    return [AttendanceRecordResponse.model_validate(r) for r in records]


@attendance_router.post("/manual", response_model=AttendanceRecordResponse, status_code=201)
async def manual_record(
    body: ManualRecordRequest,
    current_user: CurrentUserDep,
    service: AttendanceServiceDep,
) -> AttendanceRecordResponse:
    """HR manually creates/updates an attendance record."""
    try:
        record = await service.manual_record(
            employee_id=body.employee_id,
            work_date=body.work_date,
            check_in=body.check_in,
            check_out=body.check_out,
            status=body.status,
            note=body.note,
        )
        return AttendanceRecordResponse.model_validate(record)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("manual_record error: %s", exc, exc_info=True)
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail={"code": "INTERNAL_ERROR", "message": str(exc)})


@attendance_router.get("/export")
async def export_attendance(
    current_user: CurrentUserDep,
    service: AttendanceServiceDep,
    employee_id: UUID = Query(...),
    year: int = Query(default=2026, ge=2020, le=2100),
    month: int = Query(default=5, ge=1, le=12),
    format: str = Query(default="xlsx"),
) -> StreamingResponse:
    """Export monthly attendance report as Excel file."""
    report = await service.get_monthly_report(employee_id, year, month)

    export_service = ExportService()
    buffer = export_service.generate_monthly_excel(
        records=report["records"],
        employee_name=str(employee_id),  # In production, resolve employee name
        year=year,
        month=month,
    )

    filename = f"cham_cong_{year}_{month:02d}_{str(employee_id)[:8]}.xlsx"

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
