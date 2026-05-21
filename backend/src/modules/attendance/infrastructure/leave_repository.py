"""Repository classes for leave management persistence.

Provides async CRUD operations for LeaveType, LeaveBalance,
and LeaveRequest entities using SQLAlchemy async sessions.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from src.modules.attendance.domain.entities import (
    LeaveBalance,
    LeaveRequest,
    LeaveType,
)


class LeaveTypeRepository:
    """Repository for LeaveType CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[LeaveType]:
        """Get all leave types."""
        stmt = select(LeaveType).order_by(col(LeaveType.name))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, leave_type_id: UUID) -> LeaveType | None:
        """Get a leave type by ID."""
        stmt = select(LeaveType).where(LeaveType.id == leave_type_id)
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def get_by_name(self, name: str) -> LeaveType | None:
        """Get a leave type by code name."""
        stmt = select(LeaveType).where(LeaveType.name == name)
        result = await self._session.execute(stmt)
        return result.scalars().first()


class LeaveBalanceRepository:
    """Repository for LeaveBalance CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_employee_year(
        self, employee_id: UUID, year: int
    ) -> list[LeaveBalance]:
        """Get all leave balances for an employee in a given year."""
        stmt = (
            select(LeaveBalance)
            .where(
                LeaveBalance.employee_id == employee_id,
                LeaveBalance.year == year,
            )
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_balance(
        self, employee_id: UUID, leave_type_id: UUID, year: int
    ) -> LeaveBalance | None:
        """Get a specific balance for employee + type + year."""
        stmt = select(LeaveBalance).where(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.leave_type_id == leave_type_id,
            LeaveBalance.year == year,
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def create(self, balance: LeaveBalance) -> LeaveBalance:
        """Create a new leave balance record."""
        self._session.add(balance)
        await self._session.flush()
        await self._session.refresh(balance)
        return balance

    async def deduct(
        self, balance_id: UUID, days: Decimal
    ) -> LeaveBalance | None:
        """Deduct days from a balance (used when approving leave)."""
        stmt = select(LeaveBalance).where(LeaveBalance.id == balance_id)
        result = await self._session.execute(stmt)
        balance = result.scalars().first()
        if balance is None:
            return None
        balance.used_days += days
        balance.remaining_days -= days
        self._session.add(balance)
        await self._session.flush()
        return balance

    async def restore(
        self, balance_id: UUID, days: Decimal
    ) -> LeaveBalance | None:
        """Restore days to a balance (used when cancelling approved leave)."""
        stmt = select(LeaveBalance).where(LeaveBalance.id == balance_id)
        result = await self._session.execute(stmt)
        balance = result.scalars().first()
        if balance is None:
            return None
        balance.used_days -= days
        balance.remaining_days += days
        self._session.add(balance)
        await self._session.flush()
        return balance


class LeaveRequestRepository:
    """Repository for LeaveRequest CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, request: LeaveRequest) -> LeaveRequest:
        """Create a new leave request."""
        self._session.add(request)
        await self._session.flush()
        await self._session.refresh(request)
        return request

    async def get_by_id(self, request_id: UUID) -> LeaveRequest | None:
        """Get a leave request by ID."""
        stmt = select(LeaveRequest).where(LeaveRequest.id == request_id)
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def list_by_employee(
        self,
        employee_id: UUID,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[LeaveRequest], int]:
        """List leave requests for an employee with optional status filter."""
        stmt = select(LeaveRequest).where(
            LeaveRequest.employee_id == employee_id
        )
        count_stmt = select(LeaveRequest).where(
            LeaveRequest.employee_id == employee_id
        )

        if status:
            stmt = stmt.where(LeaveRequest.status == status)
            count_stmt = count_stmt.where(LeaveRequest.status == status)

        # Count
        from sqlalchemy import func

        count_result = await self._session.execute(
            select(func.count()).select_from(count_stmt.subquery())
        )
        total = count_result.scalar() or 0

        # Paginate
        stmt = (
            stmt.order_by(col(LeaveRequest.created_at).desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def list_pending(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[list[LeaveRequest], int]:
        """List all pending leave requests (for HR approval)."""
        stmt = select(LeaveRequest).where(LeaveRequest.status == "pending")

        from sqlalchemy import func

        count_result = await self._session.execute(
            select(func.count()).select_from(stmt.subquery())
        )
        total = count_result.scalar() or 0

        stmt = (
            stmt.order_by(col(LeaveRequest.created_at).desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def list_all(
        self,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[LeaveRequest], int]:
        """List all leave requests with optional status filter."""
        from sqlalchemy import func

        stmt = select(LeaveRequest)
        count_stmt = select(LeaveRequest)

        if status:
            stmt = stmt.where(LeaveRequest.status == status)
            count_stmt = count_stmt.where(LeaveRequest.status == status)

        count_result = await self._session.execute(
            select(func.count()).select_from(count_stmt.subquery())
        )
        total = count_result.scalar() or 0

        stmt = (
            stmt.order_by(col(LeaveRequest.created_at).desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def check_overlap(
        self,
        employee_id: UUID,
        start_date: date,
        end_date: date,
        exclude_id: UUID | None = None,
    ) -> bool:
        """Check if a date range overlaps with existing approved/pending requests."""
        stmt = select(LeaveRequest).where(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.status.in_(["pending", "approved"]),
            LeaveRequest.start_date <= end_date,
            LeaveRequest.end_date >= start_date,
        )
        if exclude_id:
            stmt = stmt.where(LeaveRequest.id != exclude_id)

        result = await self._session.execute(stmt)
        return result.scalars().first() is not None

    async def update(self, request: LeaveRequest) -> LeaveRequest:
        """Update a leave request."""
        self._session.add(request)
        await self._session.flush()
        await self._session.refresh(request)
        return request
