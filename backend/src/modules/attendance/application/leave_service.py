"""Service for managing leave requests.

Handles submission, approval, rejection, and cancellation of leave
requests. All operations are performed by HR on behalf of employees.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.attendance.application.balance_service import BalanceService
from src.modules.attendance.domain.entities import LeaveRequest
from src.modules.attendance.domain.enums import LeaveStatus
from src.modules.attendance.domain.exceptions import (
    InvalidLeaveStatusTransitionError,
    LeaveDateInPastError,
    LeaveOverlapError,
    LeaveRequestNotFoundError,
    LeaveTypeNotFoundError,
)
from src.modules.attendance.infrastructure.leave_repository import (
    LeaveRequestRepository,
    LeaveTypeRepository,
)


class LeaveService:
    """Manages leave request lifecycle.

    All operations are HR-initiated (no employee self-service).

    Args:
        request_repo: Repository for leave request persistence.
        type_repo: Repository for leave type lookups.
        balance_service: Service for balance checks and updates.
        session: Database session for transaction management.
    """

    def __init__(
        self,
        request_repo: LeaveRequestRepository,
        type_repo: LeaveTypeRepository,
        balance_service: BalanceService,
        session: AsyncSession,
    ) -> None:
        self._request_repo = request_repo
        self._type_repo = type_repo
        self._balance_service = balance_service
        self._session = session

    async def submit_request(
        self,
        employee_id: UUID,
        leave_type_id: UUID,
        start_date: date,
        end_date: date,
        reason: str | None = None,
    ) -> LeaveRequest:
        """Submit a new leave request (HR creates on behalf of employee).

        Validates:
        - Leave type exists
        - start_date <= end_date
        - No overlap with existing requests
        - Sufficient balance (for paid leave types)

        Args:
            employee_id: The employee UUID.
            leave_type_id: The leave type UUID.
            start_date: First day of leave.
            end_date: Last day of leave (inclusive).
            reason: Optional reason for the leave.

        Returns:
            The created LeaveRequest.

        Raises:
            LeaveTypeNotFoundError: If leave type doesn't exist.
            LeaveOverlapError: If dates overlap with existing request.
            InsufficientBalanceError: If not enough days remaining.
        """
        # Validate leave type
        leave_type = await self._type_repo.get_by_id(leave_type_id)
        if leave_type is None:
            raise LeaveTypeNotFoundError(str(leave_type_id))

        # Validate dates
        if start_date > end_date:
            start_date, end_date = end_date, start_date

        # Calculate working days (exclude weekends)
        total_days = self._calculate_working_days(start_date, end_date)

        # Check overlap
        has_overlap = await self._request_repo.check_overlap(
            employee_id, start_date, end_date
        )
        if has_overlap:
            raise LeaveOverlapError()

        # Check balance (only for types with limited days)
        year = start_date.year
        if leave_type.default_days_per_year > 0:
            await self._balance_service.check_sufficient_balance(
                employee_id, leave_type_id, year, total_days
            )

        # Create request
        request = LeaveRequest(
            employee_id=employee_id,
            leave_type_id=leave_type_id,
            start_date=start_date,
            end_date=end_date,
            total_days=total_days,
            reason=reason,
            status=LeaveStatus.PENDING,
        )

        created = await self._request_repo.create(request)
        await self._session.commit()
        return created

    async def approve_request(
        self, request_id: UUID, approved_by: UUID
    ) -> LeaveRequest:
        """Approve a pending leave request and deduct balance.

        Args:
            request_id: The leave request UUID.
            approved_by: The HR user UUID who approves.

        Returns:
            The updated LeaveRequest.

        Raises:
            LeaveRequestNotFoundError: If request doesn't exist.
            InvalidLeaveStatusTransitionError: If not in pending status.
        """
        request = await self._request_repo.get_by_id(request_id)
        if request is None:
            raise LeaveRequestNotFoundError(str(request_id))

        if request.status != LeaveStatus.PENDING:
            raise InvalidLeaveStatusTransitionError(request.status, "approved")

        # Deduct balance
        year = request.start_date.year
        balance = await self._balance_service.check_sufficient_balance(
            request.employee_id, request.leave_type_id, year, request.total_days
        )
        await self._balance_service.deduct_balance(balance.id, request.total_days)

        # Update request
        request.status = LeaveStatus.APPROVED
        request.approved_by = approved_by
        request.approved_at = datetime.now(UTC)
        request.updated_at = datetime.now(UTC)

        updated = await self._request_repo.update(request)
        await self._session.commit()
        return updated

    async def reject_request(
        self, request_id: UUID, rejection_reason: str | None = None
    ) -> LeaveRequest:
        """Reject a pending leave request.

        Args:
            request_id: The leave request UUID.
            rejection_reason: Optional reason for rejection.

        Returns:
            The updated LeaveRequest.
        """
        request = await self._request_repo.get_by_id(request_id)
        if request is None:
            raise LeaveRequestNotFoundError(str(request_id))

        if request.status != LeaveStatus.PENDING:
            raise InvalidLeaveStatusTransitionError(request.status, "rejected")

        request.status = LeaveStatus.REJECTED
        request.rejection_reason = rejection_reason
        request.updated_at = datetime.now(UTC)

        updated = await self._request_repo.update(request)
        await self._session.commit()
        return updated

    async def cancel_request(self, request_id: UUID) -> LeaveRequest:
        """Cancel a leave request. Restores balance if previously approved.

        Only allowed if the leave hasn't started yet.

        Args:
            request_id: The leave request UUID.

        Returns:
            The updated LeaveRequest.

        Raises:
            LeaveDateInPastError: If leave has already started.
        """
        request = await self._request_repo.get_by_id(request_id)
        if request is None:
            raise LeaveRequestNotFoundError(str(request_id))

        if request.status not in (LeaveStatus.PENDING, LeaveStatus.APPROVED):
            raise InvalidLeaveStatusTransitionError(request.status, "cancelled")

        # Check if leave has already started
        if request.start_date <= date.today():
            raise LeaveDateInPastError()

        # Restore balance if was approved
        if request.status == LeaveStatus.APPROVED:
            year = request.start_date.year
            balance = await self._balance_service._balance_repo.get_balance(
                request.employee_id, request.leave_type_id, year
            )
            if balance:
                await self._balance_service.restore_balance(
                    balance.id, request.total_days
                )

        request.status = LeaveStatus.CANCELLED
        request.updated_at = datetime.now(UTC)

        updated = await self._request_repo.update(request)
        await self._session.commit()
        return updated

    async def list_requests(
        self,
        employee_id: UUID | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[LeaveRequest], int]:
        """List leave requests with optional filters.

        If employee_id is provided, filter by that employee.
        If status is provided, filter by status.
        If neither, return all requests (for HR overview).
        """
        if employee_id:
            return await self._request_repo.list_by_employee(
                employee_id, status=status, page=page, page_size=page_size
            )
        # HR view: return all requests (optionally filtered by status)
        return await self._request_repo.list_all(
            status=status, page=page, page_size=page_size
        )

    @staticmethod
    def _calculate_working_days(start_date: date, end_date: date) -> Decimal:
        """Calculate number of working days between two dates (exclude weekends)."""
        total = 0
        current = start_date
        from datetime import timedelta

        while current <= end_date:
            if current.weekday() < 5:  # Monday=0 to Friday=4
                total += 1
            current += timedelta(days=1)

        return Decimal(str(total))
