# Feature: company-policy-engine, Property 25: Leave Balance Rejection
# Feature: company-policy-engine, Property 26: Leave Balance Deduction
# Feature: company-policy-engine, Property 27: Advance Notice Rejection
# Feature: company-policy-engine, Property 28: Seniority Bonus Calculation
# Feature: company-policy-engine, Property 29: Protected Period Blocking
# Feature: company-policy-engine, Property 30: Leave Overlap Rejection
# Feature: company-policy-engine, Property 31: Leave Cancellation Restores Balance
"""Property-based tests for leave policy evaluation.

Property 25: For any leave request where the requested number of days exceeds
the employee's remaining balance for that leave type, the request SHALL be
rejected with an insufficient balance message.
**Validates: Requirements 8.2**

Property 26: For any approved leave request, the deduction from the employee's
leave balance SHALL equal the count of working days in the requested period
(total calendar days minus weekends minus tenant-configured holidays).
**Validates: Requirements 8.5**

Property 27: For any non-emergency leave request where the number of calendar
days between submission date and requested start date is less than the tenant's
configured minimum advance notice days, the request SHALL be rejected.
**Validates: Requirements 8.6**

Property 28: For any employee with Y years of continuous service, the annual
leave entitlement SHALL equal base_annual_days + floor(Y/5).
**Validates: Requirements 8.7**

Property 29: For any employee currently in a protected period, any disciplinary
action initiated against that employee SHALL be blocked.
**Validates: Requirements 8.8**

Property 30: For any leave request whose date range overlaps with an existing
approved leave request for the same employee, the new request SHALL be rejected.
**Validates: Requirements 8.9**

Property 31: For any approved leave request that is cancelled before or on its
start date, the employee's leave balance SHALL be restored by exactly the number
of working days that were previously deducted.
**Validates: Requirements 8.10**
"""

import math
from datetime import date, timedelta

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from src.modules.policy.application.leave_evaluator import (
    LeaveEvaluationStatus,
    LeaveEvaluator,
    LeaveRequest,
    LeaveType,
    calculate_annual_entitlement,
    calculate_seniority_bonus,
    calculate_working_days,
)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_leave_types_non_emergency = st.sampled_from([
    LeaveType.ANNUAL,
    LeaveType.WEDDING,
    LeaveType.UNPAID,
    LeaveType.OTHER,
])

_leave_types_emergency = st.sampled_from([
    LeaveType.SICK,
    LeaveType.MATERNITY,
    LeaveType.FUNERAL,
])

_all_leave_types = st.sampled_from(list(LeaveType))

# Dates in a reasonable range
_date_st = st.dates(min_value=date(2023, 1, 1), max_value=date(2026, 12, 31))


@st.composite
def leave_period(draw: st.DrawFn) -> tuple[date, date]:
    """Generate a valid leave period (start <= end, max 30 days)."""
    start = draw(_date_st)
    duration = draw(st.integers(min_value=0, max_value=30))
    end = start + timedelta(days=duration)
    return start, end


@st.composite
def holiday_list(draw: st.DrawFn, start: date, end: date) -> list[date]:
    """Generate a list of holidays within a date range."""
    if start > end:
        return []
    num_holidays = draw(st.integers(min_value=0, max_value=5))
    total_days = (end - start).days + 1
    if total_days <= 0:
        return []
    offsets = draw(
        st.lists(
            st.integers(min_value=0, max_value=total_days - 1),
            min_size=0,
            max_size=min(num_holidays, total_days),
            unique=True,
        )
    )
    return [start + timedelta(days=o) for o in offsets]


# ---------------------------------------------------------------------------
# Property 25: Leave Balance Rejection
# ---------------------------------------------------------------------------


class TestProperty25LeaveBalanceRejection:
    """Property 25: Leave Balance Rejection.

    For any leave request where the requested number of days exceeds the
    employee's remaining balance for that leave type, the request SHALL be
    rejected with an insufficient balance message.

    **Validates: Requirements 8.2**
    """

    @settings(max_examples=100)
    @given(
        leave_type=_all_leave_types,
        period=leave_period(),
        balance=st.floats(min_value=0.0, max_value=30.0, allow_nan=False),
    )
    def test_insufficient_balance_rejected(
        self,
        leave_type: LeaveType,
        period: tuple[date, date],
        balance: float,
    ) -> None:
        """Requested days > remaining balance → rejected.

        **Validates: Requirements 8.2**
        """
        start, end = period

        # Calculate working days for this period (no holidays for simplicity)
        working_days = calculate_working_days(start, end, [])

        # Only test cases where working days exceed balance
        assume(working_days > balance)
        assume(working_days > 0)

        request = LeaveRequest(
            leave_type=leave_type,
            start_date=start,
            end_date=end,
            current_balance=balance,
            submission_date=start - timedelta(days=30),
            is_emergency=True,  # Skip advance notice check
            requires_approval=False,
            requires_document=False,
        )

        evaluator = LeaveEvaluator()
        result = evaluator.evaluate(request)

        assert result.status == LeaveEvaluationStatus.REJECTED, (
            f"Expected REJECTED but got {result.status}. "
            f"working_days={working_days}, balance={balance}"
        )
        assert result.rejection_reason is not None
        assert "balance" in result.rejection_reason.lower() or (
            "insufficient" in result.rejection_reason.lower()
        )


# ---------------------------------------------------------------------------
# Property 26: Leave Balance Deduction
# ---------------------------------------------------------------------------


class TestProperty26LeaveBalanceDeduction:
    """Property 26: Leave Balance Deduction.

    For any approved leave request, the deduction from the employee's leave
    balance SHALL equal the count of working days in the requested period
    (total calendar days minus weekends minus tenant-configured holidays).

    **Validates: Requirements 8.5**
    """

    @settings(max_examples=100)
    @given(
        period=leave_period(),
        data=st.data(),
    )
    def test_deduction_equals_working_days(
        self,
        period: tuple[date, date],
        data: st.DataObject,
    ) -> None:
        """Deduction = working days (total - weekends - holidays).

        **Validates: Requirements 8.5**
        """
        start, end = period
        holidays = data.draw(holiday_list(start, end))

        # Calculate expected working days
        expected_working_days = calculate_working_days(start, end, holidays)
        assume(expected_working_days > 0)

        # Set balance high enough to approve
        balance = float(expected_working_days + 10)

        request = LeaveRequest(
            leave_type=LeaveType.ANNUAL,
            start_date=start,
            end_date=end,
            current_balance=balance,
            holidays=holidays,
            submission_date=start - timedelta(days=30),
            is_emergency=True,  # Skip advance notice
            requires_approval=False,
            requires_document=False,
        )

        evaluator = LeaveEvaluator()
        result = evaluator.evaluate(request)

        assert result.status == LeaveEvaluationStatus.APPROVED, (
            f"Expected APPROVED but got {result.status}: {result.rejection_reason}"
        )
        assert result.working_days_requested == float(expected_working_days), (
            f"Expected {expected_working_days} working days, "
            f"got {result.working_days_requested}"
        )
        assert result.balance_after_deduction == balance - expected_working_days, (
            f"Expected balance {balance - expected_working_days}, "
            f"got {result.balance_after_deduction}"
        )


# ---------------------------------------------------------------------------
# Property 27: Advance Notice Rejection
# ---------------------------------------------------------------------------


class TestProperty27AdvanceNoticeRejection:
    """Property 27: Advance Notice Rejection.

    For any non-emergency leave request where the number of calendar days
    between submission date and requested start date is less than the tenant's
    configured minimum advance notice days, the request SHALL be rejected.

    **Validates: Requirements 8.6**
    """

    @settings(max_examples=100)
    @given(
        leave_type=_leave_types_non_emergency,
        min_notice_days=st.integers(min_value=1, max_value=14),
        data=st.data(),
    )
    def test_insufficient_advance_notice_rejected(
        self,
        leave_type: LeaveType,
        min_notice_days: int,
        data: st.DataObject,
    ) -> None:
        """Non-emergency with < minimum days notice → rejected.

        **Validates: Requirements 8.6**
        """
        # Generate notice days that are less than minimum
        actual_notice = data.draw(st.integers(min_value=0, max_value=min_notice_days - 1))

        start_date = date(2024, 6, 15)
        submission_date = start_date - timedelta(days=actual_notice)
        end_date = start_date + timedelta(days=1)

        # Ensure sufficient balance so rejection is due to notice
        request = LeaveRequest(
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            current_balance=30.0,
            submission_date=submission_date,
            is_emergency=False,
            minimum_advance_notice_days=min_notice_days,
            requires_approval=False,
            requires_document=False,
        )

        evaluator = LeaveEvaluator()
        result = evaluator.evaluate(request)

        assert result.status == LeaveEvaluationStatus.REJECTED, (
            f"Expected REJECTED but got {result.status}. "
            f"notice={actual_notice}, min_required={min_notice_days}"
        )
        assert result.rejection_reason is not None
        assert "notice" in result.rejection_reason.lower()

    @settings(max_examples=100)
    @given(
        leave_type=_leave_types_non_emergency,
        min_notice_days=st.integers(min_value=1, max_value=14),
        data=st.data(),
    )
    def test_sufficient_advance_notice_not_rejected_for_notice(
        self,
        leave_type: LeaveType,
        min_notice_days: int,
        data: st.DataObject,
    ) -> None:
        """Non-emergency with >= minimum days notice → not rejected for notice.

        **Validates: Requirements 8.6**
        """
        # Generate notice days that meet or exceed minimum
        actual_notice = data.draw(
            st.integers(min_value=min_notice_days, max_value=min_notice_days + 30)
        )

        start_date = date(2024, 6, 15)
        submission_date = start_date - timedelta(days=actual_notice)
        end_date = start_date  # Single day to ensure working day exists

        # Ensure it's a weekday
        while start_date.weekday() >= 5:
            start_date += timedelta(days=1)
            end_date = start_date
            submission_date = start_date - timedelta(days=actual_notice)

        request = LeaveRequest(
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            current_balance=30.0,
            submission_date=submission_date,
            is_emergency=False,
            minimum_advance_notice_days=min_notice_days,
            requires_approval=False,
            requires_document=False,
        )

        evaluator = LeaveEvaluator()
        result = evaluator.evaluate(request)

        # Should NOT be rejected for advance notice reasons
        if result.status == LeaveEvaluationStatus.REJECTED:
            assert "notice" not in (result.rejection_reason or "").lower(), (
                f"Rejected for notice with {actual_notice} days "
                f"(min: {min_notice_days}): {result.rejection_reason}"
            )


# ---------------------------------------------------------------------------
# Property 28: Seniority Bonus Calculation
# ---------------------------------------------------------------------------


class TestProperty28SeniorityBonusCalculation:
    """Property 28: Seniority Bonus Calculation.

    For any employee with Y years of continuous service, the annual leave
    entitlement SHALL equal base_annual_days + floor(Y/5).

    **Validates: Requirements 8.7**
    """

    @settings(max_examples=100)
    @given(
        years_of_service=st.integers(min_value=0, max_value=50),
        base_annual_days=st.integers(min_value=12, max_value=20),
    )
    def test_seniority_bonus_formula(
        self,
        years_of_service: int,
        base_annual_days: int,
    ) -> None:
        """Entitlement = base + floor(Y/5).

        **Validates: Requirements 8.7**
        """
        expected_bonus = math.floor(years_of_service / 5)
        expected_entitlement = base_annual_days + expected_bonus

        # Test the helper functions directly
        actual_bonus = calculate_seniority_bonus(years_of_service)
        actual_entitlement = calculate_annual_entitlement(
            base_annual_days, years_of_service
        )

        assert actual_bonus == expected_bonus, (
            f"Bonus: expected {expected_bonus}, got {actual_bonus} "
            f"for {years_of_service} years"
        )
        assert actual_entitlement == expected_entitlement, (
            f"Entitlement: expected {expected_entitlement}, "
            f"got {actual_entitlement} for {years_of_service} years, "
            f"base={base_annual_days}"
        )

    @settings(max_examples=100)
    @given(
        years_of_service=st.integers(min_value=0, max_value=50),
        base_annual_days=st.integers(min_value=12, max_value=20),
    )
    def test_evaluator_reports_correct_seniority_bonus(
        self,
        years_of_service: int,
        base_annual_days: int,
    ) -> None:
        """LeaveEvaluator reports correct seniority bonus in result.

        **Validates: Requirements 8.7**
        """
        expected_bonus = math.floor(years_of_service / 5)
        expected_entitlement = base_annual_days + expected_bonus

        # Use a weekday to ensure working days > 0
        start_date = date(2024, 6, 10)  # Monday
        while start_date.weekday() >= 5:
            start_date += timedelta(days=1)

        request = LeaveRequest(
            leave_type=LeaveType.ANNUAL,
            start_date=start_date,
            end_date=start_date,
            current_balance=30.0,
            years_of_service=years_of_service,
            base_annual_days=base_annual_days,
            submission_date=start_date - timedelta(days=30),
            is_emergency=True,
            requires_approval=False,
            requires_document=False,
        )

        evaluator = LeaveEvaluator()
        result = evaluator.evaluate(request)

        assert result.seniority_bonus_days == expected_bonus
        assert result.annual_entitlement == expected_entitlement


# ---------------------------------------------------------------------------
# Property 29: Protected Period Blocking
# ---------------------------------------------------------------------------


class TestProperty29ProtectedPeriodBlocking:
    """Property 29: Protected Period Blocking.

    For any employee currently in a protected period (active sick leave,
    maternity leave, or raising a child under 12 months), any disciplinary
    action initiated against that employee SHALL be blocked.

    **Validates: Requirements 8.8**
    """

    @settings(max_examples=100)
    @given(is_protected=st.booleans())
    def test_disciplinary_action_blocked_during_protected_period(
        self,
        is_protected: bool,
    ) -> None:
        """Disciplinary action blocked during protected period.

        **Validates: Requirements 8.8**
        """
        evaluator = LeaveEvaluator()
        result = evaluator.evaluate_protected_period_block(is_protected)

        if is_protected:
            assert result is not None, "Expected blocking result for protected period"
            assert result.status == LeaveEvaluationStatus.REJECTED
            assert result.rejection_reason is not None
            assert "protected" in result.rejection_reason.lower()
        else:
            assert result is None, (
                "Expected None (no blocking) for non-protected period"
            )


# ---------------------------------------------------------------------------
# Property 30: Leave Overlap Rejection
# ---------------------------------------------------------------------------


class TestProperty30LeaveOverlapRejection:
    """Property 30: Leave Overlap Rejection.

    For any leave request whose date range overlaps (partially or fully) with
    an existing approved leave request for the same employee, the new request
    SHALL be rejected with a message indicating the conflicting dates.

    **Validates: Requirements 8.9**
    """

    @settings(max_examples=100)
    @given(data=st.data())
    def test_overlapping_leave_rejected(
        self,
        data: st.DataObject,
    ) -> None:
        """Overlapping dates → rejected.

        **Validates: Requirements 8.9**
        """
        # Generate an existing approved leave period
        existing_start = data.draw(
            st.dates(min_value=date(2024, 3, 1), max_value=date(2024, 6, 30))
        )
        existing_duration = data.draw(st.integers(min_value=1, max_value=10))
        existing_end = existing_start + timedelta(days=existing_duration)

        # Generate a new request that overlaps with the existing one
        # Overlap can be: starts before existing ends, or starts during existing
        overlap_offset = data.draw(
            st.integers(min_value=0, max_value=existing_duration)
        )
        new_start = existing_start + timedelta(days=overlap_offset)
        new_duration = data.draw(st.integers(min_value=0, max_value=10))
        new_end = new_start + timedelta(days=new_duration)

        # Ensure there's actual overlap
        assume(new_start <= existing_end and new_end >= existing_start)

        request = LeaveRequest(
            leave_type=LeaveType.ANNUAL,
            start_date=new_start,
            end_date=new_end,
            current_balance=30.0,
            submission_date=new_start - timedelta(days=30),
            existing_approved_leaves=[(existing_start, existing_end)],
            is_emergency=True,  # Skip advance notice
            requires_approval=False,
            requires_document=False,
        )

        evaluator = LeaveEvaluator()
        result = evaluator.evaluate(request)

        assert result.status == LeaveEvaluationStatus.REJECTED, (
            f"Expected REJECTED for overlap but got {result.status}. "
            f"new=[{new_start}, {new_end}], "
            f"existing=[{existing_start}, {existing_end}]"
        )
        assert result.rejection_reason is not None
        assert "overlap" in result.rejection_reason.lower()
        assert len(result.conflicting_dates) > 0


# ---------------------------------------------------------------------------
# Property 31: Leave Cancellation Restores Balance
# ---------------------------------------------------------------------------


class TestProperty31LeaveCancellationRestoresBalance:
    """Property 31: Leave Cancellation Restores Balance.

    For any approved leave request that is cancelled before or on its start
    date, the employee's leave balance SHALL be restored by exactly the number
    of working days that were previously deducted.

    **Validates: Requirements 8.10**
    """

    @settings(max_examples=100)
    @given(
        period=leave_period(),
        data=st.data(),
    )
    def test_cancellation_restores_exact_working_days(
        self,
        period: tuple[date, date],
        data: st.DataObject,
    ) -> None:
        """Cancelled leave restores exactly the deducted working days.

        **Validates: Requirements 8.10**
        """
        start, end = period
        holidays = data.draw(holiday_list(start, end))

        # Calculate the working days that would have been deducted
        working_days = calculate_working_days(start, end, holidays)
        assume(working_days > 0)

        # Current balance after the original deduction
        current_balance = data.draw(
            st.floats(min_value=0.0, max_value=50.0, allow_nan=False)
        )

        request = LeaveRequest(
            leave_type=LeaveType.ANNUAL,
            start_date=start,
            end_date=end,
            current_balance=current_balance,
            holidays=holidays,
            is_cancellation=True,
            previously_deducted_days=float(working_days),
        )

        evaluator = LeaveEvaluator()
        result = evaluator.evaluate(request)

        assert result.status == LeaveEvaluationStatus.CANCELLED
        assert result.restored_days == float(working_days), (
            f"Expected {working_days} restored days, got {result.restored_days}"
        )
        expected_balance = current_balance + float(working_days)
        assert abs(result.balance_after_deduction - expected_balance) < 1e-9, (
            f"Expected balance {expected_balance}, "
            f"got {result.balance_after_deduction}"
        )
