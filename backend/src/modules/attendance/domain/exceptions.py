"""Domain exceptions for the Attendance & Leave module."""

from __future__ import annotations


class AttendanceModuleError(Exception):
    """Base exception for the attendance module."""

    def __init__(self, message: str, error_code: str = "ATTENDANCE_ERROR") -> None:
        self.message = message
        self.error_code = error_code
        super().__init__(message)


# ---------------------------------------------------------------------------
# Leave exceptions
# ---------------------------------------------------------------------------


class LeaveTypeNotFoundError(AttendanceModuleError):
    """Raised when a leave type is not found."""

    def __init__(self, leave_type_id: str = "") -> None:
        super().__init__(
            message=f"Leave type not found: {leave_type_id}",
            error_code="LEAVE_TYPE_NOT_FOUND",
        )


class LeaveRequestNotFoundError(AttendanceModuleError):
    """Raised when a leave request is not found."""

    def __init__(self, request_id: str = "") -> None:
        super().__init__(
            message=f"Leave request not found: {request_id}",
            error_code="LEAVE_REQUEST_NOT_FOUND",
        )


class InsufficientBalanceError(AttendanceModuleError):
    """Raised when employee doesn't have enough leave days."""

    def __init__(self, remaining: float = 0, requested: float = 0) -> None:
        super().__init__(
            message=f"Insufficient leave balance: {remaining} days remaining, {requested} requested",
            error_code="INSUFFICIENT_LEAVE_BALANCE",
        )


class LeaveOverlapError(AttendanceModuleError):
    """Raised when a leave request overlaps with an existing one."""

    def __init__(self) -> None:
        super().__init__(
            message="Leave request overlaps with an existing approved/pending request",
            error_code="LEAVE_OVERLAP",
        )


class InvalidLeaveStatusTransitionError(AttendanceModuleError):
    """Raised when a leave status transition is not allowed."""

    def __init__(self, current: str, target: str) -> None:
        super().__init__(
            message=f"Cannot transition from '{current}' to '{target}'",
            error_code="INVALID_LEAVE_STATUS_TRANSITION",
        )


class LeaveDateInPastError(AttendanceModuleError):
    """Raised when trying to cancel a leave that has already started."""

    def __init__(self) -> None:
        super().__init__(
            message="Cannot cancel leave that has already started",
            error_code="LEAVE_DATE_IN_PAST",
        )


# ---------------------------------------------------------------------------
# Attendance exceptions
# ---------------------------------------------------------------------------


class AlreadyCheckedInError(AttendanceModuleError):
    """Raised when employee has already checked in today."""

    def __init__(self) -> None:
        super().__init__(
            message="Already checked in today",
            error_code="ALREADY_CHECKED_IN",
        )


class NotCheckedInError(AttendanceModuleError):
    """Raised when trying to check out without checking in."""

    def __init__(self) -> None:
        super().__init__(
            message="Not checked in today",
            error_code="NOT_CHECKED_IN",
        )


class AlreadyCheckedOutError(AttendanceModuleError):
    """Raised when employee has already checked out today."""

    def __init__(self) -> None:
        super().__init__(
            message="Already checked out today",
            error_code="ALREADY_CHECKED_OUT",
        )


class AttendanceRecordNotFoundError(AttendanceModuleError):
    """Raised when an attendance record is not found."""

    def __init__(self, record_id: str = "") -> None:
        super().__init__(
            message=f"Attendance record not found: {record_id}",
            error_code="ATTENDANCE_RECORD_NOT_FOUND",
        )


# ---------------------------------------------------------------------------
# Overtime exceptions
# ---------------------------------------------------------------------------


class OvertimeRequestNotFoundError(AttendanceModuleError):
    """Raised when an overtime request is not found."""

    def __init__(self, request_id: str = "") -> None:
        super().__init__(
            message=f"Overtime request not found: {request_id}",
            error_code="OVERTIME_REQUEST_NOT_FOUND",
        )


class OvertimeLimitExceededError(AttendanceModuleError):
    """Raised when overtime exceeds weekly limit."""

    def __init__(self, current_hours: float = 0, max_hours: float = 20) -> None:
        super().__init__(
            message=f"Overtime limit exceeded: {current_hours}h this week (max {max_hours}h)",
            error_code="OVERTIME_LIMIT_EXCEEDED",
        )


# ---------------------------------------------------------------------------
# Schedule / Holiday exceptions
# ---------------------------------------------------------------------------


class ScheduleNotFoundError(AttendanceModuleError):
    """Raised when a work schedule is not found."""

    def __init__(self) -> None:
        super().__init__(
            message="Work schedule not found",
            error_code="SCHEDULE_NOT_FOUND",
        )


class EmployeeNotFoundError(AttendanceModuleError):
    """Raised when an employee is not found."""

    def __init__(self, employee_id: str = "") -> None:
        super().__init__(
            message=f"Employee not found: {employee_id}",
            error_code="EMPLOYEE_NOT_FOUND",
        )
