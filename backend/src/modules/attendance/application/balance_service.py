"""Service for managing leave balances.

Handles balance initialization, checking, deduction, and restoration.
Calculates annual leave based on Vietnamese labor law seniority rules.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.attendance.domain.entities import LeaveBalance
from src.modules.attendance.domain.exceptions import InsufficientBalanceError
from src.modules.attendance.infrastructure.config import AttendanceSettings
from src.modules.attendance.infrastructure.leave_repository import (
    LeaveBalanceRepository,
    LeaveTypeRepository,
)


class BalanceService:
    """Manages leave balance operations.

    Args:
        balance_repo: Repository for leave balance persistence.
        type_repo: Repository for leave type lookups.
        settings: Attendance module settings.
    """

    def __init__(
        self,
        balance_repo: LeaveBalanceRepository,
        type_repo: LeaveTypeRepository,
        settings: AttendanceSettings,
    ) -> None:
        self._balance_repo = balance_repo
        self._type_repo = type_repo
        self._settings = settings

    async def get_employee_balances(
        self, employee_id: UUID, year: int
    ) -> list[LeaveBalance]:
        """Get all leave balances for an employee in a year."""
        return await self._balance_repo.get_by_employee_year(employee_id, year)

    async def check_sufficient_balance(
        self,
        employee_id: UUID,
        leave_type_id: UUID,
        year: int,
        requested_days: Decimal,
    ) -> LeaveBalance:
        """Check if employee has enough balance. Returns the balance if OK.

        Raises:
            InsufficientBalanceError: If remaining days < requested days.
        """
        balance = await self._balance_repo.get_balance(
            employee_id, leave_type_id, year
        )

        if balance is None:
            raise InsufficientBalanceError(remaining=0, requested=float(requested_days))

        if balance.remaining_days < requested_days:
            raise InsufficientBalanceError(
                remaining=float(balance.remaining_days),
                requested=float(requested_days),
            )

        return balance

    async def deduct_balance(self, balance_id: UUID, days: Decimal) -> None:
        """Deduct days from a balance (called when leave is approved)."""
        await self._balance_repo.deduct(balance_id, days)

    async def restore_balance(self, balance_id: UUID, days: Decimal) -> None:
        """Restore days to a balance (called when approved leave is cancelled)."""
        await self._balance_repo.restore(balance_id, days)

    async def initialize_employee_balance(
        self,
        employee_id: UUID,
        year: int,
        start_date: date | None = None,
    ) -> list[LeaveBalance]:
        """Initialize leave balances for an employee for a given year.

        Calculates annual leave based on seniority (Vietnamese labor law):
        - Base: 12 days
        - Bonus: +1 day per 5 years of service

        Args:
            employee_id: The employee UUID.
            year: The year to initialize.
            start_date: Employee's start date (for seniority calculation).

        Returns:
            List of created LeaveBalance records.
        """
        leave_types = await self._type_repo.list_all()
        created: list[LeaveBalance] = []

        for lt in leave_types:
            # Check if balance already exists
            existing = await self._balance_repo.get_balance(
                employee_id, lt.id, year
            )
            if existing:
                continue

            # Calculate total days
            if lt.name == "annual" and start_date:
                total = self._calculate_annual_days(start_date, year)
            else:
                total = Decimal(str(lt.default_days_per_year))

            balance = LeaveBalance(
                employee_id=employee_id,
                leave_type_id=lt.id,
                year=year,
                total_days=total,
                used_days=Decimal("0"),
                remaining_days=total,
            )
            created_balance = await self._balance_repo.create(balance)
            created.append(created_balance)

        return created

    def _calculate_annual_days(self, start_date: date, year: int) -> Decimal:
        """Calculate annual leave days based on seniority.

        Vietnamese labor law: 12 base days + 1 day per 5 years.
        """
        years_worked = year - start_date.year
        if years_worked < 0:
            years_worked = 0

        bonus = years_worked // self._settings.seniority_bonus_years
        total = self._settings.annual_leave_base_days + bonus
        return Decimal(str(total))
