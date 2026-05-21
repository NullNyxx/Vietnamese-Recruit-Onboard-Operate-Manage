"""Error handler for the Attendance module.

Maps domain exceptions to HTTP responses.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.modules.attendance.domain.exceptions import (
    AlreadyCheckedInError,
    AlreadyCheckedOutError,
    AttendanceModuleError,
    AttendanceRecordNotFoundError,
    EmployeeNotFoundError,
    InsufficientBalanceError,
    InvalidLeaveStatusTransitionError,
    LeaveDateInPastError,
    LeaveOverlapError,
    LeaveRequestNotFoundError,
    LeaveTypeNotFoundError,
    NotCheckedInError,
    OvertimeLimitExceededError,
    OvertimeRequestNotFoundError,
    ScheduleNotFoundError,
)

# Map exception types to HTTP status codes
_STATUS_MAP: dict[type, int] = {
    LeaveTypeNotFoundError: 404,
    LeaveRequestNotFoundError: 404,
    AttendanceRecordNotFoundError: 404,
    OvertimeRequestNotFoundError: 404,
    ScheduleNotFoundError: 404,
    EmployeeNotFoundError: 404,
    InsufficientBalanceError: 422,
    LeaveOverlapError: 422,
    InvalidLeaveStatusTransitionError: 422,
    LeaveDateInPastError: 422,
    OvertimeLimitExceededError: 422,
    AlreadyCheckedInError: 409,
    AlreadyCheckedOutError: 409,
    NotCheckedInError: 400,
}


def register_attendance_error_handlers(app: FastAPI) -> None:
    """Register exception handlers for attendance module errors."""

    @app.exception_handler(AttendanceModuleError)
    async def handle_attendance_error(
        request: Request, exc: AttendanceModuleError
    ) -> JSONResponse:
        status_code = _STATUS_MAP.get(type(exc), 500)
        return JSONResponse(
            status_code=status_code,
            content={
                "detail": {
                    "code": exc.error_code,
                    "message": exc.message,
                }
            },
        )
