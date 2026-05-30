"""Unit tests for the leave policy evaluator.

Tests cover balance validation, working day calculation, advance notice,
seniority bonus, protected period blocking, overlap detection, and
cancellation handling.
"""

from datetime import date

from src.modules.policy.application.leave_evaluator import (
    LeaveEvaluationStatus,
    LeaveEvaluator,
    LeaveRequest,
    LeaveType,
    calculate_annual_entitlement,
    calculate_seniority_bonus,
    calculate_working_days,
    check_advance_notice,
    detect_date_overlap,
    is_emergency_leave_type,
)

# ---------------------------------------------------------------------------
# Tests for calculate_working_days
# ---------------------------------------------------------------------------


class TestCalculateWorkingDays:
    """Tests for the calculate_working_days function."""

    def test_full_week_no_holidays(self) -> None:
        """A Monday-to-Friday range yields 5 working days."""
        # 2024-01-08 is Monday, 2024-01-12 is Friday
        result = calculate_working_days(date(2024, 1, 8), date(2024, 1, 12), [])
        assert result == 5

    def test_includes_weekend_days_excluded(self) -> None:
        """A Monday-to-Sunday range still yields 5 working days."""
        # 2024-01-08 (Mon) to 2024-01-14 (Sun) = 5 weekdays
        result = calculate_working_days(date(2024, 1, 8), date(2024, 1, 14), [])
        assert result == 5

    def test_holidays_excluded(self) -> None:
        """Holidays within the range are excluded from working days."""
        # 2024-01-08 (Mon) to 2024-01-12 (Fri), with Wed as holiday
        holidays = [date(2024, 1, 10)]
        result = calculate_working_days(date(2024, 1, 8), date(2024, 1, 12), holidays)
        assert result == 4

    def test_holiday_on_weekend_no_effect(self) -> None:
        """A holiday falling on a weekend doesn't reduce working days."""
        # 2024-01-08 (Mon) to 2024-01-12 (Fri), holiday on Saturday
        result = calculate_working_days(date(2024, 1, 8), date(2024, 1, 12), [date(2024, 1, 13)])
        assert result == 5

    def test_single_day_weekday(self) -> None:
        """A single weekday yields 1 working day."""
        result = calculate_working_days(date(2024, 1, 8), date(2024, 1, 8), [])
        assert result == 1

    def test_single_day_weekend(self) -> None:
        """A single weekend day yields 0 working days."""
        # 2024-01-13 is Saturday
        result = calculate_working_days(date(2024, 1, 13), date(2024, 1, 13), [])
        assert result == 0

    def test_start_after_end_returns_zero(self) -> None:
        """If start > end, returns 0."""
        result = calculate_working_days(date(2024, 1, 12), date(2024, 1, 8), [])
        assert result == 0

    def test_two_weeks(self) -> None:
        """Two full weeks yield 10 working days."""
        # 2024-01-08 (Mon) to 2024-01-19 (Fri)
        result = calculate_working_days(date(2024, 1, 8), date(2024, 1, 19), [])
        assert result == 10

    def test_multiple_holidays(self) -> None:
        """Multiple holidays reduce working days accordingly."""
        holidays = [date(2024, 1, 9), date(2024, 1, 11)]
        result = calculate_working_days(date(2024, 1, 8), date(2024, 1, 12), holidays)
        assert result == 3


# ---------------------------------------------------------------------------
# Tests for calculate_seniority_bonus
# ---------------------------------------------------------------------------


class TestCalculateSeniorityBonus:
    """Tests for the seniority bonus calculation."""

    def test_zero_years(self) -> None:
        """0 years of service yields 0 bonus days."""
        assert calculate_seniority_bonus(0) == 0

    def test_four_years(self) -> None:
        """4 years yields 0 bonus days (floor(4/5) = 0)."""
        assert calculate_seniority_bonus(4) == 0

    def test_five_years(self) -> None:
        """5 years yields 1 bonus day."""
        assert calculate_seniority_bonus(5) == 1

    def test_nine_years(self) -> None:
        """9 years yields 1 bonus day (floor(9/5) = 1)."""
        assert calculate_seniority_bonus(9) == 1

    def test_ten_years(self) -> None:
        """10 years yields 2 bonus days."""
        assert calculate_seniority_bonus(10) == 2

    def test_twenty_five_years(self) -> None:
        """25 years yields 5 bonus days."""
        assert calculate_seniority_bonus(25) == 5

    def test_negative_years(self) -> None:
        """Negative years yields 0 bonus days."""
        assert calculate_seniority_bonus(-1) == 0


# ---------------------------------------------------------------------------
# Tests for calculate_annual_entitlement
# ---------------------------------------------------------------------------


class TestCalculateAnnualEntitlement:
    """Tests for annual entitlement calculation."""

    def test_base_only(self) -> None:
        """0 years: entitlement equals base days."""
        assert calculate_annual_entitlement(12, 0) == 12

    def test_with_seniority(self) -> None:
        """10 years: base + 2 bonus days."""
        assert calculate_annual_entitlement(12, 10) == 14

    def test_custom_base(self) -> None:
        """Custom base of 15 with 5 years: 15 + 1 = 16."""
        assert calculate_annual_entitlement(15, 5) == 16


# ---------------------------------------------------------------------------
# Tests for check_advance_notice
# ---------------------------------------------------------------------------


class TestCheckAdvanceNotice:
    """Tests for advance notice validation."""

    def test_sufficient_notice(self) -> None:
        """5 days notice with 3 days minimum passes."""
        assert check_advance_notice(date(2024, 1, 1), date(2024, 1, 6), 3) is True

    def test_exact_minimum(self) -> None:
        """Exactly 3 days notice with 3 days minimum passes."""
        assert check_advance_notice(date(2024, 1, 1), date(2024, 1, 4), 3) is True

    def test_insufficient_notice(self) -> None:
        """2 days notice with 3 days minimum fails."""
        assert check_advance_notice(date(2024, 1, 1), date(2024, 1, 3), 3) is False

    def test_same_day(self) -> None:
        """Same-day submission with any minimum > 0 fails."""
        assert check_advance_notice(date(2024, 1, 1), date(2024, 1, 1), 1) is False

    def test_zero_minimum(self) -> None:
        """Zero minimum always passes."""
        assert check_advance_notice(date(2024, 1, 1), date(2024, 1, 1), 0) is True


# ---------------------------------------------------------------------------
# Tests for detect_date_overlap
# ---------------------------------------------------------------------------


class TestDetectDateOverlap:
    """Tests for date overlap detection."""

    def test_no_overlap(self) -> None:
        """Non-overlapping ranges return empty list."""
        existing = [(date(2024, 1, 1), date(2024, 1, 5))]
        result = detect_date_overlap(date(2024, 1, 8), date(2024, 1, 12), existing)
        assert result == []

    def test_full_overlap(self) -> None:
        """Fully overlapping ranges return all requested dates."""
        existing = [(date(2024, 1, 8), date(2024, 1, 12))]
        result = detect_date_overlap(date(2024, 1, 8), date(2024, 1, 12), existing)
        assert len(result) == 5

    def test_partial_overlap(self) -> None:
        """Partially overlapping ranges return only conflicting dates."""
        existing = [(date(2024, 1, 10), date(2024, 1, 15))]
        result = detect_date_overlap(date(2024, 1, 8), date(2024, 1, 12), existing)
        # Overlap: Jan 10, 11, 12
        assert result == [date(2024, 1, 10), date(2024, 1, 11), date(2024, 1, 12)]

    def test_multiple_existing_leaves(self) -> None:
        """Multiple existing leaves can produce conflicts."""
        existing = [
            (date(2024, 1, 9), date(2024, 1, 9)),
            (date(2024, 1, 11), date(2024, 1, 11)),
        ]
        result = detect_date_overlap(date(2024, 1, 8), date(2024, 1, 12), existing)
        assert result == [date(2024, 1, 9), date(2024, 1, 11)]

    def test_start_after_end_returns_empty(self) -> None:
        """Invalid range (start > end) returns empty."""
        existing = [(date(2024, 1, 1), date(2024, 1, 5))]
        result = detect_date_overlap(date(2024, 1, 12), date(2024, 1, 8), existing)
        assert result == []


# ---------------------------------------------------------------------------
# Tests for is_emergency_leave_type
# ---------------------------------------------------------------------------


class TestIsEmergencyLeaveType:
    """Tests for emergency leave type detection."""

    def test_sick_is_emergency(self) -> None:
        assert is_emergency_leave_type(LeaveType.SICK) is True

    def test_maternity_is_emergency(self) -> None:
        assert is_emergency_leave_type(LeaveType.MATERNITY) is True

    def test_funeral_is_emergency(self) -> None:
        assert is_emergency_leave_type(LeaveType.FUNERAL) is True

    def test_annual_is_not_emergency(self) -> None:
        assert is_emergency_leave_type(LeaveType.ANNUAL) is False

    def test_wedding_is_not_emergency(self) -> None:
        assert is_emergency_leave_type(LeaveType.WEDDING) is False


# ---------------------------------------------------------------------------
# Tests for LeaveEvaluator
# ---------------------------------------------------------------------------


class TestLeaveEvaluator:
    """Tests for the LeaveEvaluator class."""

    def setup_method(self) -> None:
        """Create evaluator instance for each test."""
        self.evaluator = LeaveEvaluator()

    def test_approve_valid_request(self) -> None:
        """A valid request with sufficient balance is approved."""
        request = LeaveRequest(
            leave_type=LeaveType.ANNUAL,
            start_date=date(2024, 1, 15),  # Monday
            end_date=date(2024, 1, 19),  # Friday
            current_balance=10.0,
            submission_date=date(2024, 1, 8),
            requires_approval=False,
        )
        result = self.evaluator.evaluate(request)
        assert result.status == LeaveEvaluationStatus.APPROVED
        assert result.working_days_requested == 5.0
        assert result.balance_after_deduction == 5.0

    def test_reject_insufficient_balance(self) -> None:
        """Request exceeding balance is rejected."""
        request = LeaveRequest(
            leave_type=LeaveType.ANNUAL,
            start_date=date(2024, 1, 8),
            end_date=date(2024, 1, 19),  # 10 working days
            current_balance=5.0,
            submission_date=date(2024, 1, 1),
        )
        result = self.evaluator.evaluate(request)
        assert result.status == LeaveEvaluationStatus.REJECTED
        assert "Insufficient balance" in (result.rejection_reason or "")

    def test_reject_insufficient_advance_notice(self) -> None:
        """Non-emergency request with insufficient notice is rejected."""
        request = LeaveRequest(
            leave_type=LeaveType.ANNUAL,
            start_date=date(2024, 1, 10),
            end_date=date(2024, 1, 10),
            current_balance=10.0,
            submission_date=date(2024, 1, 9),  # 1 day notice
            minimum_advance_notice_days=3,
        )
        result = self.evaluator.evaluate(request)
        assert result.status == LeaveEvaluationStatus.REJECTED
        assert "advance notice" in (result.rejection_reason or "").lower()

    def test_emergency_skips_advance_notice(self) -> None:
        """Emergency leave types skip advance notice check."""
        request = LeaveRequest(
            leave_type=LeaveType.SICK,
            start_date=date(2024, 1, 10),
            end_date=date(2024, 1, 10),
            current_balance=10.0,
            submission_date=date(2024, 1, 10),  # same day
            minimum_advance_notice_days=3,
            requires_approval=False,
        )
        result = self.evaluator.evaluate(request)
        assert result.status != LeaveEvaluationStatus.REJECTED

    def test_reject_date_overlap(self) -> None:
        """Request overlapping with existing leave is rejected."""
        request = LeaveRequest(
            leave_type=LeaveType.ANNUAL,
            start_date=date(2024, 1, 8),
            end_date=date(2024, 1, 12),
            current_balance=10.0,
            submission_date=date(2024, 1, 1),
            existing_approved_leaves=[(date(2024, 1, 10), date(2024, 1, 15))],
        )
        result = self.evaluator.evaluate(request)
        assert result.status == LeaveEvaluationStatus.REJECTED
        assert len(result.conflicting_dates) > 0

    def test_pending_approval(self) -> None:
        """Request requiring approval gets pending_approval status."""
        request = LeaveRequest(
            leave_type=LeaveType.ANNUAL,
            start_date=date(2024, 1, 15),
            end_date=date(2024, 1, 15),
            current_balance=10.0,
            submission_date=date(2024, 1, 8),
            requires_approval=True,
        )
        result = self.evaluator.evaluate(request)
        assert result.status == LeaveEvaluationStatus.PENDING_APPROVAL

    def test_pending_document(self) -> None:
        """Request requiring document gets pending_document status."""
        request = LeaveRequest(
            leave_type=LeaveType.SICK,
            start_date=date(2024, 1, 15),
            end_date=date(2024, 1, 15),
            current_balance=10.0,
            submission_date=date(2024, 1, 15),
            requires_document=True,
            required_document_type="medical_certificate",
            requires_approval=False,
        )
        result = self.evaluator.evaluate(request)
        assert result.status == LeaveEvaluationStatus.PENDING_DOCUMENT

    def test_seniority_bonus_calculated(self) -> None:
        """Seniority bonus is calculated in the result."""
        request = LeaveRequest(
            leave_type=LeaveType.ANNUAL,
            start_date=date(2024, 1, 15),
            end_date=date(2024, 1, 15),
            current_balance=10.0,
            years_of_service=10,
            submission_date=date(2024, 1, 8),
            requires_approval=False,
        )
        result = self.evaluator.evaluate(request)
        assert result.seniority_bonus_days == 2
        assert result.annual_entitlement == 14

    def test_cancellation_restores_balance(self) -> None:
        """Cancellation restores previously deducted days."""
        request = LeaveRequest(
            leave_type=LeaveType.ANNUAL,
            start_date=date(2024, 1, 8),
            end_date=date(2024, 1, 12),
            current_balance=7.0,
            is_cancellation=True,
            previously_deducted_days=5.0,
        )
        result = self.evaluator.evaluate(request)
        assert result.status == LeaveEvaluationStatus.CANCELLED
        assert result.restored_days == 5.0
        assert result.balance_after_deduction == 12.0

    def test_cancellation_calculates_days_if_not_provided(self) -> None:
        """Cancellation calculates working days if previously_deducted not set."""
        request = LeaveRequest(
            leave_type=LeaveType.ANNUAL,
            start_date=date(2024, 1, 8),  # Monday
            end_date=date(2024, 1, 12),  # Friday = 5 working days
            current_balance=7.0,
            is_cancellation=True,
            previously_deducted_days=0.0,
        )
        result = self.evaluator.evaluate(request)
        assert result.status == LeaveEvaluationStatus.CANCELLED
        assert result.restored_days == 5.0
        assert result.balance_after_deduction == 12.0

    def test_protected_period_blocks_disciplinary(self) -> None:
        """Disciplinary action is blocked during protected period."""
        result = self.evaluator.evaluate_protected_period_block(is_protected_period=True)
        assert result is not None
        assert result.status == LeaveEvaluationStatus.REJECTED
        assert "protected period" in (result.rejection_reason or "").lower()

    def test_no_block_outside_protected_period(self) -> None:
        """No block when not in protected period."""
        result = self.evaluator.evaluate_protected_period_block(is_protected_period=False)
        assert result is None

    def test_holidays_reduce_working_days(self) -> None:
        """Holidays within leave period reduce deducted days."""
        request = LeaveRequest(
            leave_type=LeaveType.ANNUAL,
            start_date=date(2024, 1, 8),  # Monday
            end_date=date(2024, 1, 12),  # Friday
            current_balance=10.0,
            submission_date=date(2024, 1, 1),
            holidays=[date(2024, 1, 9), date(2024, 1, 10)],
            requires_approval=False,
        )
        result = self.evaluator.evaluate(request)
        assert result.working_days_requested == 3.0
        assert result.balance_after_deduction == 7.0

    def test_weekend_only_request(self) -> None:
        """A request covering only weekends yields 0 working days."""
        request = LeaveRequest(
            leave_type=LeaveType.ANNUAL,
            start_date=date(2024, 1, 13),  # Saturday
            end_date=date(2024, 1, 14),  # Sunday
            current_balance=0.0,
            submission_date=date(2024, 1, 1),
            requires_approval=False,
        )
        result = self.evaluator.evaluate(request)
        # 0 working days requested, 0 balance needed
        assert result.working_days_requested == 0.0
        assert result.status == LeaveEvaluationStatus.APPROVED
