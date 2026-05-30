"""Unit tests for the OvertimeEvaluator.

Tests overtime policy evaluation including daily/monthly/yearly limit
validation, pay calculation, and multiplier selection.

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7
"""

import pytest

from src.modules.policy.application.overtime_evaluator import (
    DayType,
    OvertimeContext,
    OvertimeEvaluator,
)


@pytest.fixture
def evaluator() -> OvertimeEvaluator:
    """Create an OvertimeEvaluator instance."""
    return OvertimeEvaluator()


def _make_context(
    requested_hours: float = 2.0,
    scheduled_hours: float = 8.0,
    current_monthly_total: float = 0.0,
    current_yearly_total: float = 0.0,
    max_monthly: float = 40.0,
    max_yearly: float = 200.0,
    monthly_salary: float = 10_000_000.0,
    standard_days: float = 26.0,
    standard_hours: float = 8.0,
    day_types: list[DayType] | None = None,
    multipliers: dict[DayType, float] | None = None,
) -> OvertimeContext:
    """Helper to create an OvertimeContext with sensible defaults."""
    return OvertimeContext(
        requested_hours=requested_hours,
        scheduled_hours=scheduled_hours,
        current_monthly_total=current_monthly_total,
        current_yearly_total=current_yearly_total,
        max_monthly=max_monthly,
        max_yearly=max_yearly,
        monthly_salary=monthly_salary,
        standard_days=standard_days,
        standard_hours=standard_hours,
        day_types=day_types or [DayType.WEEKDAY],
        multipliers=multipliers or {},
    )


class TestDailyLimitValidation:
    """Tests for daily limit: (scheduled_hours + overtime_hours) ≤ 12."""

    def test_within_daily_limit(self, evaluator: OvertimeEvaluator) -> None:
        """Request within daily limit is approved."""
        ctx = _make_context(requested_hours=4.0, scheduled_hours=8.0)
        result = evaluator.evaluate(ctx)
        assert result.approved is True
        assert len(result.rejections) == 0

    def test_at_daily_limit_boundary(self, evaluator: OvertimeEvaluator) -> None:
        """Request exactly at 12h total is approved."""
        ctx = _make_context(requested_hours=4.0, scheduled_hours=8.0)
        result = evaluator.evaluate(ctx)
        assert result.approved is True

    def test_exceeds_daily_limit(self, evaluator: OvertimeEvaluator) -> None:
        """Request exceeding 12h total is rejected."""
        ctx = _make_context(requested_hours=5.0, scheduled_hours=8.0)
        result = evaluator.evaluate(ctx)
        assert result.approved is False
        assert any(r.limit_type == "daily" for r in result.rejections)

    def test_daily_limit_max_allowed_calculation(self, evaluator: OvertimeEvaluator) -> None:
        """Rejection includes correct max_allowed hours."""
        ctx = _make_context(requested_hours=6.0, scheduled_hours=8.0)
        result = evaluator.evaluate(ctx)
        daily_rejection = next(r for r in result.rejections if r.limit_type == "daily")
        assert daily_rejection.max_allowed == 4.0


class TestMonthlyLimitValidation:
    """Tests for monthly limit: (current_monthly + requested) ≤ max_monthly."""

    def test_within_monthly_limit(self, evaluator: OvertimeEvaluator) -> None:
        """Request within monthly limit is approved."""
        ctx = _make_context(
            requested_hours=2.0,
            current_monthly_total=30.0,
            max_monthly=40.0,
        )
        result = evaluator.evaluate(ctx)
        assert result.approved is True

    def test_at_monthly_limit_boundary(self, evaluator: OvertimeEvaluator) -> None:
        """Request exactly at monthly limit is approved."""
        ctx = _make_context(
            requested_hours=4.0,
            scheduled_hours=8.0,
            current_monthly_total=36.0,
            max_monthly=40.0,
        )
        result = evaluator.evaluate(ctx)
        assert result.approved is True

    def test_exceeds_monthly_limit(self, evaluator: OvertimeEvaluator) -> None:
        """Request exceeding monthly limit is rejected."""
        ctx = _make_context(
            requested_hours=3.0,
            current_monthly_total=38.0,
            max_monthly=40.0,
        )
        result = evaluator.evaluate(ctx)
        assert result.approved is False
        assert any(r.limit_type == "monthly" for r in result.rejections)

    def test_monthly_remaining_hours(self, evaluator: OvertimeEvaluator) -> None:
        """Rejection includes correct remaining monthly hours."""
        ctx = _make_context(
            requested_hours=5.0,
            current_monthly_total=38.0,
            max_monthly=40.0,
        )
        result = evaluator.evaluate(ctx)
        monthly_rejection = next(r for r in result.rejections if r.limit_type == "monthly")
        assert monthly_rejection.max_allowed == 2.0


class TestYearlyLimitValidation:
    """Tests for yearly limit: (current_yearly + requested) ≤ max_yearly."""

    def test_within_yearly_limit(self, evaluator: OvertimeEvaluator) -> None:
        """Request within yearly limit is approved."""
        ctx = _make_context(
            requested_hours=2.0,
            current_yearly_total=100.0,
            max_yearly=200.0,
        )
        result = evaluator.evaluate(ctx)
        assert result.approved is True

    def test_at_yearly_limit_boundary(self, evaluator: OvertimeEvaluator) -> None:
        """Request exactly at yearly limit is approved."""
        ctx = _make_context(
            requested_hours=2.0,
            current_yearly_total=198.0,
            max_yearly=200.0,
        )
        result = evaluator.evaluate(ctx)
        assert result.approved is True

    def test_exceeds_yearly_limit(self, evaluator: OvertimeEvaluator) -> None:
        """Request exceeding yearly limit is rejected."""
        ctx = _make_context(
            requested_hours=3.0,
            current_yearly_total=199.0,
            max_yearly=200.0,
        )
        result = evaluator.evaluate(ctx)
        assert result.approved is False
        assert any(r.limit_type == "yearly" for r in result.rejections)

    def test_special_sector_300h_yearly(self, evaluator: OvertimeEvaluator) -> None:
        """Special sector with 300h yearly limit works correctly."""
        ctx = _make_context(
            requested_hours=2.0,
            current_yearly_total=250.0,
            max_yearly=300.0,
        )
        result = evaluator.evaluate(ctx)
        assert result.approved is True


class TestMultipleLimitViolations:
    """Tests for multiple simultaneous limit violations."""

    def test_daily_and_monthly_exceeded(self, evaluator: OvertimeEvaluator) -> None:
        """Both daily and monthly limits exceeded produces both rejections."""
        ctx = _make_context(
            requested_hours=5.0,
            scheduled_hours=8.0,
            current_monthly_total=38.0,
            max_monthly=40.0,
        )
        result = evaluator.evaluate(ctx)
        assert result.approved is False
        limit_types = {r.limit_type for r in result.rejections}
        assert "daily" in limit_types
        assert "monthly" in limit_types

    def test_all_limits_exceeded(self, evaluator: OvertimeEvaluator) -> None:
        """All three limits exceeded produces all three rejections."""
        ctx = _make_context(
            requested_hours=5.0,
            scheduled_hours=8.0,
            current_monthly_total=38.0,
            max_monthly=40.0,
            current_yearly_total=199.0,
            max_yearly=200.0,
        )
        result = evaluator.evaluate(ctx)
        assert result.approved is False
        limit_types = {r.limit_type for r in result.rejections}
        assert limit_types == {"daily", "monthly", "yearly"}


class TestOvertimePayCalculation:
    """Tests for overtime pay calculation formula."""

    def test_weekday_pay_calculation(self, evaluator: OvertimeEvaluator) -> None:
        """Weekday overtime pay uses 150% multiplier."""
        # monthly_salary=10,000,000 / 26 days / 8 hours = 48,076.92 hourly
        # pay = 48,076.92 * 2 hours * 1.5 = 144,230.77
        ctx = _make_context(
            requested_hours=2.0,
            monthly_salary=10_000_000.0,
            standard_days=26.0,
            standard_hours=8.0,
            day_types=[DayType.WEEKDAY],
        )
        result = evaluator.evaluate(ctx)
        assert result.approved is True
        hourly_rate = 10_000_000.0 / 26.0 / 8.0
        expected_pay = hourly_rate * 2.0 * 1.5
        assert abs(result.calculated_pay - expected_pay) < 0.01
        assert result.applied_multiplier == 1.5

    def test_weekend_pay_calculation(self, evaluator: OvertimeEvaluator) -> None:
        """Weekend overtime pay uses 200% multiplier."""
        ctx = _make_context(
            requested_hours=3.0,
            monthly_salary=10_000_000.0,
            standard_days=26.0,
            standard_hours=8.0,
            day_types=[DayType.WEEKEND],
        )
        result = evaluator.evaluate(ctx)
        assert result.approved is True
        hourly_rate = 10_000_000.0 / 26.0 / 8.0
        expected_pay = hourly_rate * 3.0 * 2.0
        assert abs(result.calculated_pay - expected_pay) < 0.01
        assert result.applied_multiplier == 2.0

    def test_holiday_pay_calculation(self, evaluator: OvertimeEvaluator) -> None:
        """Holiday overtime pay uses 300% multiplier."""
        ctx = _make_context(
            requested_hours=2.0,
            monthly_salary=10_000_000.0,
            standard_days=26.0,
            standard_hours=8.0,
            day_types=[DayType.HOLIDAY],
        )
        result = evaluator.evaluate(ctx)
        assert result.approved is True
        hourly_rate = 10_000_000.0 / 26.0 / 8.0
        expected_pay = hourly_rate * 2.0 * 3.0
        assert abs(result.calculated_pay - expected_pay) < 0.01
        assert result.applied_multiplier == 3.0

    def test_hourly_rate_in_result(self, evaluator: OvertimeEvaluator) -> None:
        """Result includes the computed hourly rate."""
        ctx = _make_context(
            monthly_salary=10_000_000.0,
            standard_days=26.0,
            standard_hours=8.0,
        )
        result = evaluator.evaluate(ctx)
        expected_rate = 10_000_000.0 / 26.0 / 8.0
        assert abs(result.hourly_rate - expected_rate) < 0.01

    def test_zero_standard_days_returns_zero_rate(self, evaluator: OvertimeEvaluator) -> None:
        """Zero standard days produces zero hourly rate (no division error)."""
        ctx = _make_context(standard_days=0.0)
        result = evaluator.evaluate(ctx)
        assert result.hourly_rate == 0.0
        assert result.calculated_pay == 0.0

    def test_zero_standard_hours_returns_zero_rate(self, evaluator: OvertimeEvaluator) -> None:
        """Zero standard hours produces zero hourly rate (no division error)."""
        ctx = _make_context(standard_hours=0.0)
        result = evaluator.evaluate(ctx)
        assert result.hourly_rate == 0.0
        assert result.calculated_pay == 0.0


class TestHighestMultiplierSelection:
    """Tests for highest multiplier selection when multiple day types apply."""

    def test_weekend_and_holiday_uses_holiday_multiplier(
        self, evaluator: OvertimeEvaluator
    ) -> None:
        """When date is both weekend and holiday, holiday multiplier (300%) wins."""
        ctx = _make_context(day_types=[DayType.WEEKEND, DayType.HOLIDAY])
        result = evaluator.evaluate(ctx)
        assert result.applied_multiplier == 3.0

    def test_weekday_and_weekend_uses_weekend_multiplier(
        self, evaluator: OvertimeEvaluator
    ) -> None:
        """When date is both weekday and weekend, weekend multiplier (200%) wins."""
        ctx = _make_context(day_types=[DayType.WEEKDAY, DayType.WEEKEND])
        result = evaluator.evaluate(ctx)
        assert result.applied_multiplier == 2.0

    def test_all_day_types_uses_holiday_multiplier(self, evaluator: OvertimeEvaluator) -> None:
        """When all day types apply, holiday multiplier (300%) wins."""
        ctx = _make_context(day_types=[DayType.WEEKDAY, DayType.WEEKEND, DayType.HOLIDAY])
        result = evaluator.evaluate(ctx)
        assert result.applied_multiplier == 3.0

    def test_empty_day_types_defaults_to_weekday(self, evaluator: OvertimeEvaluator) -> None:
        """Empty day_types list defaults to weekday multiplier."""
        ctx = _make_context(day_types=[])
        result = evaluator.evaluate(ctx)
        assert result.applied_multiplier == 1.5

    def test_configured_multiplier_above_minimum(self, evaluator: OvertimeEvaluator) -> None:
        """Tenant-configured multiplier above legal minimum is used."""
        ctx = _make_context(
            day_types=[DayType.WEEKDAY],
            multipliers={DayType.WEEKDAY: 2.0},  # above 1.5 minimum
        )
        result = evaluator.evaluate(ctx)
        assert result.applied_multiplier == 2.0

    def test_configured_multiplier_below_minimum_uses_minimum(
        self, evaluator: OvertimeEvaluator
    ) -> None:
        """Tenant-configured multiplier below legal minimum falls back to minimum."""
        ctx = _make_context(
            day_types=[DayType.WEEKDAY],
            multipliers={DayType.WEEKDAY: 1.0},  # below 1.5 minimum
        )
        result = evaluator.evaluate(ctx)
        assert result.applied_multiplier == 1.5


class TestTotalUpdatesOnApproval:
    """Tests for monthly and yearly total updates on approval."""

    def test_monthly_total_updated(self, evaluator: OvertimeEvaluator) -> None:
        """Approved request updates monthly total."""
        ctx = _make_context(
            requested_hours=3.0,
            current_monthly_total=10.0,
        )
        result = evaluator.evaluate(ctx)
        assert result.approved is True
        assert result.updated_monthly_total == 13.0

    def test_yearly_total_updated(self, evaluator: OvertimeEvaluator) -> None:
        """Approved request updates yearly total."""
        ctx = _make_context(
            requested_hours=3.0,
            current_yearly_total=50.0,
        )
        result = evaluator.evaluate(ctx)
        assert result.approved is True
        assert result.updated_yearly_total == 53.0

    def test_rejected_request_does_not_update_totals(self, evaluator: OvertimeEvaluator) -> None:
        """Rejected request does not update monthly or yearly totals."""
        ctx = _make_context(
            requested_hours=5.0,
            scheduled_hours=8.0,  # 8+5=13 > 12
            current_monthly_total=10.0,
            current_yearly_total=50.0,
        )
        result = evaluator.evaluate(ctx)
        assert result.approved is False
        assert result.updated_monthly_total == 0.0
        assert result.updated_yearly_total == 0.0


class TestTriggeredActions:
    """Tests for triggered actions in evaluation results."""

    def test_approved_triggers_calculate_action(self, evaluator: OvertimeEvaluator) -> None:
        """Approved request triggers a 'calculate' action with pay details."""
        ctx = _make_context(requested_hours=2.0)
        result = evaluator.evaluate(ctx)
        assert result.approved is True
        assert len(result.triggered_actions) == 1
        action = result.triggered_actions[0]
        assert action["type"] == "calculate"
        assert "overtime_pay" in action["parameters"]["output_field"]
        assert action["parameters"]["hours"] == 2.0

    def test_rejected_triggers_restrict_action(self, evaluator: OvertimeEvaluator) -> None:
        """Rejected request triggers a 'restrict' action."""
        ctx = _make_context(requested_hours=5.0, scheduled_hours=8.0)
        result = evaluator.evaluate(ctx)
        assert result.approved is False
        assert len(result.triggered_actions) == 1
        action = result.triggered_actions[0]
        assert action["type"] == "restrict"
        assert "overtime_limit_exceeded" in action["parameters"]["reason"]


class TestResultSerialization:
    """Tests for OvertimeEvaluationResult.to_dict()."""

    def test_approved_result_to_dict(self, evaluator: OvertimeEvaluator) -> None:
        """Approved result serializes correctly."""
        ctx = _make_context(requested_hours=2.0)
        result = evaluator.evaluate(ctx)
        d = result.to_dict()
        assert d["approved"] is True
        assert d["rejections"] == []
        assert d["calculated_pay"] > 0
        assert d["applied_multiplier"] == 1.5

    def test_rejected_result_to_dict(self, evaluator: OvertimeEvaluator) -> None:
        """Rejected result serializes correctly with rejection details."""
        ctx = _make_context(requested_hours=5.0, scheduled_hours=8.0)
        result = evaluator.evaluate(ctx)
        d = result.to_dict()
        assert d["approved"] is False
        assert len(d["rejections"]) > 0
        assert d["rejections"][0]["limit_type"] == "daily"
