# Feature: company-policy-engine, Property 32: Overtime Limit Enforcement
# Feature: company-policy-engine, Property 33: Overtime Pay Calculation
# Feature: company-policy-engine, Property 34: Highest Multiplier Selection
"""Property-based tests for overtime policy evaluation.

Property 32: For any overtime request, if (scheduled_regular_hours +
requested_overtime_hours) > 12 for that day, OR if (current_monthly_total +
requested_hours) > configured monthly maximum, OR if (current_yearly_total +
requested_hours) > configured yearly maximum, the request SHALL be rejected.
**Validates: Requirements 9.2, 9.3, 9.4**

Property 33: For any approved overtime request, the calculated overtime pay
SHALL equal (monthly_salary ÷ standard_monthly_working_days ÷
standard_daily_working_hours) × overtime_hours × applicable_multiplier.
**Validates: Requirements 9.5**

Property 34: For any work date that qualifies as multiple day types
simultaneously, the engine SHALL apply the highest applicable multiplier.
**Validates: Requirements 9.6**
"""

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from src.modules.policy.application.overtime_evaluator import (
    MINIMUM_MULTIPLIERS,
    DayType,
    OvertimeContext,
    OvertimeEvaluator,
)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Realistic salary range (VND)
_salary_st = st.floats(min_value=5_000_000, max_value=100_000_000, allow_nan=False)

# Standard working days per month (20-26)
_standard_days_st = st.floats(min_value=20.0, max_value=26.0, allow_nan=False)

# Standard working hours per day (7-8)
_standard_hours_st = st.floats(min_value=7.0, max_value=8.0, allow_nan=False)

# Overtime hours requested (0.5 to 8)
_requested_hours_st = st.floats(min_value=0.5, max_value=8.0, allow_nan=False)

# Scheduled regular hours (4-10)
_scheduled_hours_st = st.floats(min_value=4.0, max_value=10.0, allow_nan=False)

# Monthly/yearly limits
_max_monthly_st = st.floats(min_value=30.0, max_value=60.0, allow_nan=False)
_max_yearly_st = st.floats(min_value=200.0, max_value=400.0, allow_nan=False)

# Day types
_day_type_st = st.sampled_from(list(DayType))


@st.composite
def overtime_limit_violation_scenario(
    draw: st.DrawFn,
) -> tuple[OvertimeContext, bool]:
    """Generate an overtime context that may or may not violate limits.

    Returns (context, should_be_rejected).
    """
    scheduled_hours = draw(_scheduled_hours_st)
    max_monthly = draw(_max_monthly_st)
    max_yearly = draw(_max_yearly_st)

    should_violate = draw(st.booleans())

    if should_violate:
        # Choose which limit to violate
        violation_type = draw(st.sampled_from(["daily", "monthly", "yearly"]))

        if violation_type == "daily":
            # Make daily total > 12
            max_overtime = 12.0 - scheduled_hours
            requested = draw(
                st.floats(
                    min_value=max(max_overtime + 0.1, 0.1),
                    max_value=10.0,
                    allow_nan=False,
                )
            )
            current_monthly = draw(
                st.floats(min_value=0.0, max_value=max_monthly - 10, allow_nan=False)
            )
            current_yearly = draw(
                st.floats(min_value=0.0, max_value=max_yearly - 10, allow_nan=False)
            )
        elif violation_type == "monthly":
            # Make monthly total exceed limit
            max_overtime_daily = 12.0 - scheduled_hours
            requested = draw(
                st.floats(
                    min_value=0.5,
                    max_value=min(max_overtime_daily, 8.0),
                    allow_nan=False,
                )
            )
            # current_monthly + requested > max_monthly
            current_monthly = draw(
                st.floats(
                    min_value=max_monthly - requested + 0.1,
                    max_value=max_monthly + 10,
                    allow_nan=False,
                )
            )
            current_yearly = draw(
                st.floats(min_value=0.0, max_value=max_yearly - 10, allow_nan=False)
            )
        else:  # yearly
            max_overtime_daily = 12.0 - scheduled_hours
            requested = draw(
                st.floats(
                    min_value=0.5,
                    max_value=min(max_overtime_daily, 8.0),
                    allow_nan=False,
                )
            )
            current_monthly = draw(
                st.floats(
                    min_value=0.0,
                    max_value=max(max_monthly - requested - 0.1, 0.0),
                    allow_nan=False,
                )
            )
            # current_yearly + requested > max_yearly
            current_yearly = draw(
                st.floats(
                    min_value=max_yearly - requested + 0.1,
                    max_value=max_yearly + 50,
                    allow_nan=False,
                )
            )
    else:
        # All limits pass
        max_overtime_daily = 12.0 - scheduled_hours
        assume(max_overtime_daily > 0.5)
        requested = draw(
            st.floats(
                min_value=0.5,
                max_value=min(max_overtime_daily - 0.1, 8.0),
                allow_nan=False,
            )
        )
        assume(requested > 0)
        current_monthly = draw(
            st.floats(
                min_value=0.0,
                max_value=max(max_monthly - requested - 0.1, 0.0),
                allow_nan=False,
            )
        )
        current_yearly = draw(
            st.floats(
                min_value=0.0,
                max_value=max(max_yearly - requested - 0.1, 0.0),
                allow_nan=False,
            )
        )

    context = OvertimeContext(
        requested_hours=requested,
        scheduled_hours=scheduled_hours,
        current_monthly_total=current_monthly,
        current_yearly_total=current_yearly,
        max_monthly=max_monthly,
        max_yearly=max_yearly,
        monthly_salary=15_000_000.0,
        standard_days=22.0,
        standard_hours=8.0,
        day_types=[DayType.WEEKDAY],
    )

    return context, should_violate


@st.composite
def overtime_pay_scenario(draw: st.DrawFn) -> OvertimeContext:
    """Generate an overtime context that will pass all limits (for pay calc).

    Ensures all limits are satisfied so the request is approved.
    """
    scheduled_hours = draw(st.floats(min_value=4.0, max_value=8.0, allow_nan=False))
    max_overtime_daily = 12.0 - scheduled_hours
    assume(max_overtime_daily >= 1.0)

    requested = draw(
        st.floats(
            min_value=0.5,
            max_value=min(max_overtime_daily - 0.1, 4.0),
            allow_nan=False,
        )
    )
    assume(requested > 0)

    max_monthly = draw(st.floats(min_value=40.0, max_value=60.0, allow_nan=False))
    max_yearly = draw(st.floats(min_value=200.0, max_value=400.0, allow_nan=False))

    current_monthly = draw(
        st.floats(
            min_value=0.0,
            max_value=max(max_monthly - requested - 1.0, 0.0),
            allow_nan=False,
        )
    )
    current_yearly = draw(
        st.floats(
            min_value=0.0,
            max_value=max(max_yearly - requested - 1.0, 0.0),
            allow_nan=False,
        )
    )

    monthly_salary = draw(_salary_st)
    standard_days = draw(_standard_days_st)
    standard_hours = draw(_standard_hours_st)

    day_type = draw(_day_type_st)

    # Generate a multiplier >= legal minimum for the day type
    legal_min = MINIMUM_MULTIPLIERS[day_type]
    multiplier = draw(
        st.floats(min_value=legal_min, max_value=legal_min + 1.0, allow_nan=False)
    )

    return OvertimeContext(
        requested_hours=requested,
        scheduled_hours=scheduled_hours,
        current_monthly_total=current_monthly,
        current_yearly_total=current_yearly,
        max_monthly=max_monthly,
        max_yearly=max_yearly,
        monthly_salary=monthly_salary,
        standard_days=standard_days,
        standard_hours=standard_hours,
        day_types=[day_type],
        multipliers={day_type: multiplier},
    )


@st.composite
def multiple_day_types_scenario(
    draw: st.DrawFn,
) -> tuple[list[DayType], dict[DayType, float]]:
    """Generate multiple day types with configured multipliers.

    Returns (day_types, multipliers) where at least 2 day types are present.
    """
    # Pick 2-3 day types
    num_types = draw(st.integers(min_value=2, max_value=3))
    day_types = draw(
        st.lists(
            _day_type_st,
            min_size=num_types,
            max_size=num_types,
            unique=True,
        )
    )

    multipliers: dict[DayType, float] = {}
    for dt in day_types:
        legal_min = MINIMUM_MULTIPLIERS[dt]
        mult = draw(
            st.floats(
                min_value=legal_min,
                max_value=legal_min + 1.5,
                allow_nan=False,
            )
        )
        multipliers[dt] = mult

    return day_types, multipliers


# ---------------------------------------------------------------------------
# Property 32: Overtime Limit Enforcement
# ---------------------------------------------------------------------------


class TestProperty32OvertimeLimitEnforcement:
    """Property 32: Overtime Limit Enforcement.

    For any overtime request, if (scheduled_regular_hours +
    requested_overtime_hours) > 12 for that day, OR if (current_monthly_total +
    requested_hours) > configured monthly maximum, OR if (current_yearly_total +
    requested_hours) > configured yearly maximum, the request SHALL be rejected.

    **Validates: Requirements 9.2, 9.3, 9.4**
    """

    @settings(max_examples=100)
    @given(scenario=overtime_limit_violation_scenario())
    def test_overtime_limits_enforced(
        self,
        scenario: tuple[OvertimeContext, bool],
    ) -> None:
        """Daily > 12h OR monthly > max OR yearly > max → rejected.

        **Validates: Requirements 9.2, 9.3, 9.4**
        """
        context, should_be_rejected = scenario
        evaluator = OvertimeEvaluator()
        result = evaluator.evaluate(context)

        if should_be_rejected:
            assert result.approved is False, (
                f"Expected rejection but got approved. "
                f"daily_total={context.scheduled_hours + context.requested_hours}, "
                f"monthly={context.current_monthly_total + context.requested_hours}/"
                f"{context.max_monthly}, "
                f"yearly={context.current_yearly_total + context.requested_hours}/"
                f"{context.max_yearly}"
            )
            assert len(result.rejections) >= 1
        else:
            assert result.approved is True, (
                f"Expected approval but got rejected. "
                f"daily_total={context.scheduled_hours + context.requested_hours}, "
                f"monthly={context.current_monthly_total + context.requested_hours}/"
                f"{context.max_monthly}, "
                f"yearly={context.current_yearly_total + context.requested_hours}/"
                f"{context.max_yearly}, "
                f"rejections={[r.message for r in result.rejections]}"
            )


# ---------------------------------------------------------------------------
# Property 33: Overtime Pay Calculation
# ---------------------------------------------------------------------------


class TestProperty33OvertimePayCalculation:
    """Property 33: Overtime Pay Calculation.

    For any approved overtime request, the calculated overtime pay SHALL equal
    (monthly_salary ÷ standard_monthly_working_days ÷ standard_daily_working_hours)
    × overtime_hours × applicable_multiplier.

    **Validates: Requirements 9.5**
    """

    @settings(max_examples=100)
    @given(context=overtime_pay_scenario())
    def test_overtime_pay_formula(
        self,
        context: OvertimeContext,
    ) -> None:
        """Pay = (salary ÷ days ÷ hours) × overtime_hours × multiplier.

        **Validates: Requirements 9.5**
        """
        evaluator = OvertimeEvaluator()
        result = evaluator.evaluate(context)

        assert result.approved is True, (
            f"Expected approval for pay calculation test. "
            f"Rejections: {[r.message for r in result.rejections]}"
        )

        # Calculate expected pay
        hourly_rate = (
            context.monthly_salary / context.standard_days / context.standard_hours
        )

        # Determine expected multiplier
        day_type = context.day_types[0]
        legal_min = MINIMUM_MULTIPLIERS[day_type]
        configured = context.multipliers.get(day_type, legal_min)
        expected_multiplier = max(configured, legal_min)

        expected_pay = hourly_rate * context.requested_hours * expected_multiplier

        # Use relative tolerance for floating point comparison
        assert abs(result.calculated_pay - expected_pay) < 1e-6 * max(
            abs(expected_pay), 1.0
        ), (
            f"Pay mismatch: expected {expected_pay}, got {result.calculated_pay}. "
            f"hourly_rate={hourly_rate}, hours={context.requested_hours}, "
            f"multiplier={expected_multiplier}"
        )
        assert abs(result.hourly_rate - hourly_rate) < 1e-6 * max(
            abs(hourly_rate), 1.0
        )
        assert abs(result.applied_multiplier - expected_multiplier) < 1e-9


# ---------------------------------------------------------------------------
# Property 34: Highest Multiplier Selection
# ---------------------------------------------------------------------------


class TestProperty34HighestMultiplierSelection:
    """Property 34: Highest Multiplier Selection.

    For any work date that qualifies as multiple day types simultaneously
    (e.g., a rest day that is also a public holiday), the engine SHALL apply
    the highest applicable multiplier among all qualifying day types.

    **Validates: Requirements 9.6**
    """

    @settings(max_examples=100)
    @given(scenario=multiple_day_types_scenario())
    def test_highest_multiplier_applied(
        self,
        scenario: tuple[list[DayType], dict[DayType, float]],
    ) -> None:
        """Multiple day types → highest multiplier applied.

        **Validates: Requirements 9.6**
        """
        day_types, multipliers = scenario

        # Calculate expected highest multiplier
        expected_highest = 0.0
        for dt in day_types:
            legal_min = MINIMUM_MULTIPLIERS[dt]
            configured = multipliers.get(dt, legal_min)
            effective = max(configured, legal_min)
            if effective > expected_highest:
                expected_highest = effective

        # Create a context that will pass all limits
        context = OvertimeContext(
            requested_hours=1.0,
            scheduled_hours=8.0,
            current_monthly_total=0.0,
            current_yearly_total=0.0,
            max_monthly=40.0,
            max_yearly=200.0,
            monthly_salary=15_000_000.0,
            standard_days=22.0,
            standard_hours=8.0,
            day_types=day_types,
            multipliers=multipliers,
        )

        evaluator = OvertimeEvaluator()
        result = evaluator.evaluate(context)

        assert result.approved is True, (
            f"Expected approval but got rejected: "
            f"{[r.message for r in result.rejections]}"
        )
        assert abs(result.applied_multiplier - expected_highest) < 1e-9, (
            f"Expected multiplier {expected_highest}, "
            f"got {result.applied_multiplier}. "
            f"day_types={day_types}, multipliers={multipliers}"
        )
