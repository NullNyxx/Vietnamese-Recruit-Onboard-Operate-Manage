"""Leave policy evaluator for the Policy Engine module.

Provides leave-specific evaluation logic including balance validation,
working day calculation, advance notice checks, seniority bonus
computation, protected period blocking, overlap detection, and
cancellation handling.

All public functions are pure where possible to facilitate testing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Any  # noqa: F401 - used in type annotations

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class LeaveType(str, Enum):
    """Supported leave types for evaluation."""

    ANNUAL = "annual"
    SICK = "sick"
    MATERNITY = "maternity"
    WEDDING = "wedding"
    FUNERAL = "funeral"
    UNPAID = "unpaid"
    OTHER = "other"


class LeaveEvaluationStatus(str, Enum):
    """Possible outcomes of a leave evaluation."""

    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING_APPROVAL = "pending_approval"
    PENDING_DOCUMENT = "pending_document"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Data classes for input/output
# ---------------------------------------------------------------------------


@dataclass
class LeaveRequest:
    """Input context for leave policy evaluation.

    Attributes:
        leave_type: The type of leave being requested.
        start_date: First day of the requested leave period.
        end_date: Last day of the requested leave period (inclusive).
        current_balance: Remaining leave days for this leave type.
        years_of_service: Employee's continuous years of service.
        submission_date: Date the request was submitted.
        existing_approved_leaves: List of (start_date, end_date) tuples
            for previously approved leave periods.
        holidays: List of dates configured as tenant holidays.
        is_protected_period: Whether the employee is currently in a
            protected period (sick leave, maternity, child < 12 months).
        is_emergency: Whether this is an emergency leave type
            (sick, maternity, funeral).
        minimum_advance_notice_days: Tenant-configured minimum advance
            notice in calendar days (default 3).
        base_annual_days: Base annual leave entitlement (default 12).
        requires_approval: Whether this leave type requires manager approval.
        requires_document: Whether this leave type requires supporting docs.
        required_document_type: Type of document required, if any.
        is_cancellation: Whether this is a cancellation of existing leave.
        previously_deducted_days: Days previously deducted (for cancellation).
    """

    leave_type: LeaveType
    start_date: date
    end_date: date
    current_balance: float
    years_of_service: int = 0
    submission_date: date | None = None
    existing_approved_leaves: list[tuple[date, date]] = field(default_factory=list)
    holidays: list[date] = field(default_factory=list)
    is_protected_period: bool = False
    is_emergency: bool = False
    minimum_advance_notice_days: int = 3
    base_annual_days: int = 12
    requires_approval: bool = True
    requires_document: bool = False
    required_document_type: str | None = None
    is_cancellation: bool = False
    previously_deducted_days: float = 0.0


@dataclass
class LeaveEvaluationResult:
    """Result of a leave policy evaluation.

    Attributes:
        status: The evaluation outcome status.
        rejection_reason: Human-readable reason if rejected.
        working_days_requested: Number of working days in the period.
        balance_after_deduction: Balance after deducting working days.
        seniority_bonus_days: Extra days from seniority bonus.
        annual_entitlement: Total annual entitlement including bonus.
        conflicting_dates: Dates that overlap with existing leave.
        restored_days: Days restored to balance (for cancellation).
        triggered_actions: List of actions triggered by the evaluation.
    """

    status: LeaveEvaluationStatus = LeaveEvaluationStatus.APPROVED
    rejection_reason: str | None = None
    working_days_requested: float = 0.0
    balance_after_deduction: float = 0.0
    seniority_bonus_days: int = 0
    annual_entitlement: int = 0
    conflicting_dates: list[date] = field(default_factory=list)
    restored_days: float = 0.0
    triggered_actions: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pure helper functions
# ---------------------------------------------------------------------------


def calculate_working_days(
    start_date: date,
    end_date: date,
    holidays: list[date],
) -> int:
    """Calculate the number of working days in a date range.

    Excludes weekends (Saturday=5, Sunday=6) and tenant-configured
    holidays from the count.

    Args:
        start_date: First day of the period (inclusive).
        end_date: Last day of the period (inclusive).
        holidays: List of tenant-configured holiday dates.

    Returns:
        Number of working days in the range.
    """
    if start_date > end_date:
        return 0

    holiday_set = set(holidays)
    working_days = 0
    current = start_date

    while current <= end_date:
        # weekday(): Monday=0 ... Sunday=6
        if current.weekday() < 5 and current not in holiday_set:
            working_days += 1
        current += timedelta(days=1)

    return working_days


def calculate_seniority_bonus(years_of_service: int) -> int:
    """Calculate seniority bonus days per Article 113.

    Formula: floor(years_of_service / 5)

    Args:
        years_of_service: Employee's continuous years of service.

    Returns:
        Number of bonus leave days.
    """
    if years_of_service < 0:
        return 0
    return math.floor(years_of_service / 5)


def calculate_annual_entitlement(base_annual_days: int, years_of_service: int) -> int:
    """Calculate total annual leave entitlement including seniority bonus.

    Formula: base_annual_days + floor(years_of_service / 5)

    Args:
        base_annual_days: Base annual leave days (default 12).
        years_of_service: Employee's continuous years of service.

    Returns:
        Total annual leave entitlement in days.
    """
    bonus = calculate_seniority_bonus(years_of_service)
    return base_annual_days + bonus


def check_advance_notice(
    submission_date: date,
    start_date: date,
    minimum_days: int,
) -> bool:
    """Check if the leave request meets advance notice requirements.

    Args:
        submission_date: Date the request was submitted.
        start_date: First day of the requested leave.
        minimum_days: Minimum calendar days of advance notice required.

    Returns:
        True if advance notice is sufficient, False otherwise.
    """
    notice_days = (start_date - submission_date).days
    return notice_days >= minimum_days


def detect_date_overlap(
    start_date: date,
    end_date: date,
    existing_leaves: list[tuple[date, date]],
) -> list[date]:
    """Detect dates that overlap with existing approved leave.

    Args:
        start_date: First day of the new request (inclusive).
        end_date: Last day of the new request (inclusive).
        existing_leaves: List of (start, end) tuples for approved leaves.

    Returns:
        Sorted list of dates that conflict with existing leave.
    """
    if start_date > end_date:
        return []

    requested_dates: set[date] = set()
    current = start_date
    while current <= end_date:
        requested_dates.add(current)
        current += timedelta(days=1)

    conflicting: set[date] = set()
    for existing_start, existing_end in existing_leaves:
        if existing_start > existing_end:
            continue
        existing_current = existing_start
        while existing_current <= existing_end:
            if existing_current in requested_dates:
                conflicting.add(existing_current)
            existing_current += timedelta(days=1)

    return sorted(conflicting)


def is_emergency_leave_type(leave_type: LeaveType) -> bool:
    """Determine if a leave type is considered emergency.

    Emergency types (sick, maternity, funeral) are exempt from
    advance notice requirements.

    Args:
        leave_type: The leave type to check.

    Returns:
        True if the leave type is emergency, False otherwise.
    """
    return leave_type in (LeaveType.SICK, LeaveType.MATERNITY, LeaveType.FUNERAL)


# ---------------------------------------------------------------------------
# Leave Evaluator class
# ---------------------------------------------------------------------------


class LeaveEvaluator:
    """Evaluates leave policy rules against a leave request context.

    Performs the following checks in order:
    1. Handle cancellation (restore balance)
    2. Calculate working days
    3. Calculate seniority bonus and annual entitlement
    4. Validate balance sufficiency
    5. Validate advance notice
    6. Detect date overlap with existing approved leave
    7. Block disciplinary actions during protected periods
    8. Check approval/document requirements

    The evaluator is stateless — all context is provided via the
    LeaveRequest dataclass.
    """

    def evaluate(self, request: LeaveRequest) -> LeaveEvaluationResult:
        """Evaluate leave policy rules against the provided request.

        Args:
            request: The leave request context to evaluate.

        Returns:
            A LeaveEvaluationResult with the evaluation outcome.
        """
        result = LeaveEvaluationResult()

        # Step 1: Handle cancellation
        if request.is_cancellation:
            return self._handle_cancellation(request, result)

        # Step 2: Calculate working days
        working_days = calculate_working_days(
            request.start_date,
            request.end_date,
            request.holidays,
        )
        result.working_days_requested = float(working_days)

        # Step 3: Calculate seniority bonus and annual entitlement
        result.seniority_bonus_days = calculate_seniority_bonus(request.years_of_service)
        result.annual_entitlement = calculate_annual_entitlement(
            request.base_annual_days,
            request.years_of_service,
        )

        # Step 4: Validate balance sufficiency
        if working_days > request.current_balance:
            result.status = LeaveEvaluationStatus.REJECTED
            result.rejection_reason = (
                f"Insufficient balance: requested {working_days} working days "
                f"but only {request.current_balance} days remaining"
            )
            result.triggered_actions.append(
                {
                    "type": "restrict",
                    "parameters": {
                        "reason": "insufficient_balance",
                        "requested_days": working_days,
                        "remaining_balance": request.current_balance,
                    },
                }
            )
            return result

        # Step 5: Validate advance notice (non-emergency only)
        submission_date = request.submission_date or request.start_date
        is_emergency = request.is_emergency or is_emergency_leave_type(request.leave_type)

        if not is_emergency:
            if not check_advance_notice(
                submission_date,
                request.start_date,
                request.minimum_advance_notice_days,
            ):
                notice_given = (request.start_date - submission_date).days
                result.status = LeaveEvaluationStatus.REJECTED
                result.rejection_reason = (
                    f"Insufficient advance notice: {notice_given} days given, "
                    f"minimum {request.minimum_advance_notice_days} days required"
                )
                result.triggered_actions.append(
                    {
                        "type": "restrict",
                        "parameters": {
                            "reason": "insufficient_advance_notice",
                            "notice_given_days": notice_given,
                            "minimum_required_days": request.minimum_advance_notice_days,
                        },
                    }
                )
                return result

        # Step 6: Detect date overlap
        conflicting_dates = detect_date_overlap(
            request.start_date,
            request.end_date,
            request.existing_approved_leaves,
        )
        if conflicting_dates:
            result.status = LeaveEvaluationStatus.REJECTED
            result.rejection_reason = (
                f"Leave dates overlap with existing approved leave: "
                f"{', '.join(d.isoformat() for d in conflicting_dates)}"
            )
            result.conflicting_dates = conflicting_dates
            result.triggered_actions.append(
                {
                    "type": "restrict",
                    "parameters": {
                        "reason": "date_overlap",
                        "conflicting_dates": [d.isoformat() for d in conflicting_dates],
                    },
                }
            )
            return result

        # Step 7: Calculate balance after deduction
        result.balance_after_deduction = request.current_balance - working_days

        # Step 8: Check document requirements
        if request.requires_document:
            result.status = LeaveEvaluationStatus.PENDING_DOCUMENT
            result.triggered_actions.append(
                {
                    "type": "notify",
                    "parameters": {
                        "reason": "document_required",
                        "document_type": request.required_document_type or "supporting_document",
                    },
                }
            )
            return result

        # Step 9: Check approval requirements
        if request.requires_approval:
            result.status = LeaveEvaluationStatus.PENDING_APPROVAL
            result.triggered_actions.append(
                {
                    "type": "notify",
                    "parameters": {
                        "reason": "approval_required",
                        "approver": "direct_manager",
                    },
                }
            )
            return result

        # All checks passed — approved
        result.status = LeaveEvaluationStatus.APPROVED
        result.triggered_actions.append(
            {
                "type": "calculate",
                "parameters": {
                    "action": "deduct_balance",
                    "days_to_deduct": working_days,
                    "leave_type": request.leave_type.value,
                },
            }
        )
        return result

    def evaluate_protected_period_block(
        self,
        is_protected_period: bool,
    ) -> LeaveEvaluationResult | None:
        """Check if disciplinary action should be blocked.

        Per Article 122, disciplinary actions are blocked during
        protected periods (active sick leave, maternity leave, or
        raising a child under 12 months).

        Args:
            is_protected_period: Whether the employee is in a
                protected period.

        Returns:
            A rejection result if blocked, None if not blocked.
        """
        if not is_protected_period:
            return None

        result = LeaveEvaluationResult()
        result.status = LeaveEvaluationStatus.REJECTED
        result.rejection_reason = (
            "Disciplinary action blocked: employee is in a protected period "
            "(active sick leave, maternity leave, or raising a child under 12 months)"
        )
        result.triggered_actions.append(
            {
                "type": "restrict",
                "parameters": {
                    "reason": "protected_period",
                    "action_blocked": "disciplinary_action",
                },
            }
        )
        return result

    def _handle_cancellation(
        self,
        request: LeaveRequest,
        result: LeaveEvaluationResult,
    ) -> LeaveEvaluationResult:
        """Handle leave cancellation by restoring deducted days.

        Args:
            request: The cancellation request context.
            result: The result object to populate.

        Returns:
            The populated result with restored balance info.
        """
        # Calculate working days that were originally deducted
        if request.previously_deducted_days > 0:
            restored = request.previously_deducted_days
        else:
            restored = float(
                calculate_working_days(
                    request.start_date,
                    request.end_date,
                    request.holidays,
                )
            )

        result.status = LeaveEvaluationStatus.CANCELLED
        result.restored_days = restored
        result.balance_after_deduction = request.current_balance + restored
        result.triggered_actions.append(
            {
                "type": "calculate",
                "parameters": {
                    "action": "restore_balance",
                    "days_restored": restored,
                    "leave_type": request.leave_type.value,
                    "new_balance": request.current_balance + restored,
                },
            }
        )
        return result
