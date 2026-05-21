"""Enums for the Attendance & Leave module."""

from enum import Enum


class LeaveStatus(str, Enum):
    """Status of a leave request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class LeaveTypeCode(str, Enum):
    """Predefined leave type codes."""

    ANNUAL = "annual"
    SICK = "sick"
    UNPAID = "unpaid"
    MATERNITY = "maternity"
    WEDDING = "wedding"
    FUNERAL = "funeral"
    PERSONAL = "personal"


class AttendanceStatus(str, Enum):
    """Status of an attendance record for a given day."""

    PRESENT = "present"
    LATE = "late"
    EARLY_LEAVE = "early_leave"
    ABSENT = "absent"
    ON_LEAVE = "on_leave"
    HOLIDAY = "holiday"


class OvertimeStatus(str, Enum):
    """Status of an overtime request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
