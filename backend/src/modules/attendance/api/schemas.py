"""Pydantic schemas for the Leave Management API."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Leave Type
# ---------------------------------------------------------------------------


class LeaveTypeResponse(BaseModel):
    """Response model for a leave type."""

    id: UUID
    name: str
    display_name: str
    default_days_per_year: int
    is_paid: bool
    requires_approval: bool
    requires_document: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Leave Balance
# ---------------------------------------------------------------------------


class LeaveBalanceResponse(BaseModel):
    """Response model for a leave balance."""

    id: UUID
    employee_id: UUID
    leave_type_id: UUID
    year: int
    total_days: Decimal
    used_days: Decimal
    remaining_days: Decimal

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Leave Request
# ---------------------------------------------------------------------------


class LeaveRequestCreate(BaseModel):
    """Request body for creating a leave request."""

    employee_id: UUID
    leave_type_id: UUID
    start_date: date
    end_date: date
    reason: str | None = None


class LeaveRequestResponse(BaseModel):
    """Response model for a leave request."""

    id: UUID
    employee_id: UUID
    leave_type_id: UUID
    start_date: date
    end_date: date
    total_days: Decimal
    reason: str | None = None
    status: str
    approved_by: UUID | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeaveRequestListResponse(BaseModel):
    """Paginated response for leave requests."""

    items: list[LeaveRequestResponse]
    total: int
    page: int
    page_size: int


class RejectRequest(BaseModel):
    """Request body for rejecting a leave request."""

    reason: str | None = Field(default=None, max_length=500)


# ---------------------------------------------------------------------------
# Balance Initialization
# ---------------------------------------------------------------------------


class InitializeBalanceRequest(BaseModel):
    """Request body for initializing balances for an employee."""

    employee_id: UUID
    year: int = Field(ge=2020, le=2100)
    start_date: date | None = None
