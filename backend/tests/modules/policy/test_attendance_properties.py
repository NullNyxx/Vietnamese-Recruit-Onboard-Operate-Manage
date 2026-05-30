# Feature: company-policy-engine, Property 22: Attendance Threshold Violation Detection
# Feature: company-policy-engine, Property 23: Violation Counter Increment
# Feature: company-policy-engine, Property 24: Dismissal Alert Threshold
"""Property-based tests for attendance policy evaluation.

Property 22: For any attendance event where (check_in_time − scheduled_start)
exceeds the configured late_threshold, the evaluation SHALL produce a "late"
status; and for any event where (scheduled_end − check_out_time) exceeds the
configured early_leave_threshold, the evaluation SHALL produce an "early_leave"
status. Conversely, if the difference does not exceed the threshold, the
violation status SHALL NOT be applied.
**Validates: Requirements 7.2, 7.3**

Property 23: For any attendance violation that is flagged, the employee's
violation counter for the current calendar month SHALL increase by exactly 1,
and the counter for the current calendar year SHALL increase by exactly 1.
**Validates: Requirements 7.5**

Property 24: For any employee whose unauthorized absence count reaches 5 days
within a rolling 30-day window OR 20 days within a rolling 365-day window, the
engine SHALL trigger a dismissal-eligible alert. For counts below both
thresholds, no dismissal alert SHALL be triggered.
**Validates: Requirements 7.6**
"""

from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.modules.policy.application.attendance_evaluator import (
    AttendanceContext,
    AttendanceEvaluator,
    ViolationCounters,
)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Generate threshold durations between 1 and 60 minutes
_threshold_minutes_st = st.integers(min_value=1, max_value=60)

# Generate a base schedule date (fixed to avoid timezone issues)
_base_date_st = st.dates(
    min_value=datetime(2023, 1, 1).date(),
    max_value=datetime(2025, 12, 31).date(),
)

# Generate hour offsets for scheduled start (6-12 range for realistic shifts)
_start_hour_st = st.integers(min_value=6, max_value=12)

# Generate shift duration in hours (4-12 hours)
_shift_duration_st = st.integers(min_value=4, max_value=12)


@st.composite
def attendance_late_scenario(draw: st.DrawFn) -> tuple[AttendanceContext, bool]:
    """Generate an attendance context and whether it should be late.

    Returns a tuple of (context, expected_is_late).
    The late_minutes is drawn to be either within or exceeding the threshold.
    """
    threshold_minutes = draw(_threshold_minutes_st)
    threshold = timedelta(minutes=threshold_minutes)

    # Decide if this scenario should be a violation or not
    is_violation = draw(st.booleans())

    if is_violation:
        # Late by more than threshold (threshold + 1 to threshold + 120 min)
        late_minutes = draw(st.integers(min_value=threshold_minutes + 1, max_value=180))
    else:
        # Within threshold (0 to threshold minutes inclusive)
        late_minutes = draw(st.integers(min_value=0, max_value=threshold_minutes))

    scheduled_start = datetime(2024, 6, 10, 8, 0, 0, tzinfo=UTC)
    scheduled_end = datetime(2024, 6, 10, 17, 0, 0, tzinfo=UTC)
    check_in_time = scheduled_start + timedelta(minutes=late_minutes)

    context = AttendanceContext(
        check_in_time=check_in_time,
        check_out_time=scheduled_end,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        late_threshold=threshold,
        early_leave_threshold=timedelta(minutes=15),
    )

    return context, is_violation


@st.composite
def attendance_early_leave_scenario(draw: st.DrawFn) -> tuple[AttendanceContext, bool]:
    """Generate an attendance context and whether it should be early_leave.

    Returns a tuple of (context, expected_is_early_leave).
    """
    threshold_minutes = draw(_threshold_minutes_st)
    threshold = timedelta(minutes=threshold_minutes)

    # Decide if this scenario should be a violation or not
    is_violation = draw(st.booleans())

    if is_violation:
        # Left early by more than threshold
        early_minutes = draw(st.integers(min_value=threshold_minutes + 1, max_value=180))
    else:
        # Within threshold (0 to threshold minutes inclusive)
        early_minutes = draw(st.integers(min_value=0, max_value=threshold_minutes))

    scheduled_start = datetime(2024, 6, 10, 8, 0, 0, tzinfo=UTC)
    scheduled_end = datetime(2024, 6, 10, 17, 0, 0, tzinfo=UTC)
    check_out_time = scheduled_end - timedelta(minutes=early_minutes)

    context = AttendanceContext(
        check_in_time=scheduled_start,
        check_out_time=check_out_time,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        late_threshold=timedelta(minutes=15),
        early_leave_threshold=threshold,
    )

    return context, is_violation


@st.composite
def violation_counter_scenario(draw: st.DrawFn) -> tuple[AttendanceContext, ViolationCounters]:
    """Generate an attendance context that will produce a violation.

    Always generates a late arrival exceeding the threshold so we can
    verify counter increments.
    """
    threshold_minutes = draw(st.integers(min_value=1, max_value=30))
    late_minutes = threshold_minutes + draw(st.integers(min_value=1, max_value=60))

    initial_monthly = draw(st.integers(min_value=0, max_value=20))
    initial_yearly = draw(st.integers(min_value=0, max_value=100))

    scheduled_start = datetime(2024, 6, 10, 8, 0, 0, tzinfo=UTC)
    scheduled_end = datetime(2024, 6, 10, 17, 0, 0, tzinfo=UTC)

    counters = ViolationCounters(
        monthly_count=initial_monthly,
        yearly_count=initial_yearly,
        absent_days_30d=0,
        absent_days_365d=0,
    )

    context = AttendanceContext(
        check_in_time=scheduled_start + timedelta(minutes=late_minutes),
        check_out_time=scheduled_end,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        late_threshold=timedelta(minutes=threshold_minutes),
        early_leave_threshold=timedelta(minutes=15),
        violation_counters=counters,
    )

    return context, counters


@st.composite
def dismissal_alert_scenario(
    draw: st.DrawFn,
) -> tuple[AttendanceContext, bool]:
    """Generate an absent scenario with counters near dismissal thresholds.

    Returns (context, expected_alert_triggered).
    The absent_days_30d and absent_days_365d are set so that after the
    current absent event is counted, the threshold may or may not be reached.
    """
    # After this absent event, counters will be incremented by 1
    # Threshold: 5 days/30d OR 20 days/365d
    should_trigger = draw(st.booleans())

    if should_trigger:
        # Pick which threshold to trigger
        trigger_30d = draw(st.booleans())
        if trigger_30d:
            # After increment, absent_days_30d >= 5
            absent_30d = draw(st.integers(min_value=4, max_value=10))
            absent_365d = draw(st.integers(min_value=0, max_value=18))
        else:
            # After increment, absent_days_365d >= 20
            absent_30d = draw(st.integers(min_value=0, max_value=3))
            absent_365d = draw(st.integers(min_value=19, max_value=30))
    else:
        # Below both thresholds after increment
        # After increment: 30d < 5 AND 365d < 20
        absent_30d = draw(st.integers(min_value=0, max_value=3))
        absent_365d = draw(st.integers(min_value=0, max_value=18))

    scheduled_start = datetime(2024, 6, 10, 8, 0, 0, tzinfo=UTC)
    scheduled_end = datetime(2024, 6, 10, 17, 0, 0, tzinfo=UTC)

    counters = ViolationCounters(
        monthly_count=0,
        yearly_count=0,
        absent_days_30d=absent_30d,
        absent_days_365d=absent_365d,
    )

    # Create an absent scenario: no check-in, past deadline, no approved leave
    context = AttendanceContext(
        check_in_time=None,
        check_out_time=None,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        approved_leave=False,
        current_time=scheduled_end + timedelta(minutes=31),
        violation_counters=counters,
    )

    return context, should_trigger


# ---------------------------------------------------------------------------
# Property 22: Attendance Threshold Violation Detection
# ---------------------------------------------------------------------------


class TestProperty22AttendanceThresholdViolationDetection:
    """Property 22: Attendance Threshold Violation Detection.

    For any attendance event where (check_in_time − scheduled_start) exceeds
    the configured late_threshold, the evaluation SHALL produce a "late" status;
    and for any event where (scheduled_end − check_out_time) exceeds the
    configured early_leave_threshold, the evaluation SHALL produce an
    "early_leave" status. Conversely, if the difference does not exceed the
    threshold, the violation status SHALL NOT be applied.

    **Validates: Requirements 7.2, 7.3**
    """

    @settings(max_examples=100)
    @given(scenario=attendance_late_scenario())
    def test_late_threshold_detection(
        self,
        scenario: tuple[AttendanceContext, bool],
    ) -> None:
        """Late status is applied iff check-in exceeds late_threshold.

        **Validates: Requirements 7.2**
        """
        context, expected_is_late = scenario
        evaluator = AttendanceEvaluator()
        result = evaluator.evaluate(context)

        if expected_is_late:
            assert result.status == "late", (
                f"Expected 'late' but got '{result.status}'. "
                f"check_in={context.check_in_time}, "
                f"scheduled_start={context.scheduled_start}, "
                f"threshold={context.late_threshold}"
            )
            late_violations = [
                v for v in result.violations if v.violation_type == "late"
            ]
            assert len(late_violations) >= 1
        else:
            assert result.status != "late", (
                f"Expected NOT 'late' but got '{result.status}'. "
                f"check_in={context.check_in_time}, "
                f"scheduled_start={context.scheduled_start}, "
                f"threshold={context.late_threshold}"
            )
            late_violations = [
                v for v in result.violations if v.violation_type == "late"
            ]
            assert len(late_violations) == 0

    @settings(max_examples=100)
    @given(scenario=attendance_early_leave_scenario())
    def test_early_leave_threshold_detection(
        self,
        scenario: tuple[AttendanceContext, bool],
    ) -> None:
        """Early leave status is applied iff check-out exceeds early_leave_threshold.

        **Validates: Requirements 7.3**
        """
        context, expected_is_early_leave = scenario
        evaluator = AttendanceEvaluator()
        result = evaluator.evaluate(context)

        if expected_is_early_leave:
            # Status should be early_leave (or late if both apply, but we
            # ensure check-in is on time in this scenario)
            early_violations = [
                v for v in result.violations if v.violation_type == "early_leave"
            ]
            assert len(early_violations) >= 1, (
                f"Expected early_leave violation but got none. "
                f"check_out={context.check_out_time}, "
                f"scheduled_end={context.scheduled_end}, "
                f"threshold={context.early_leave_threshold}"
            )
        else:
            early_violations = [
                v for v in result.violations if v.violation_type == "early_leave"
            ]
            assert len(early_violations) == 0, (
                f"Expected NO early_leave violation but got one. "
                f"check_out={context.check_out_time}, "
                f"scheduled_end={context.scheduled_end}, "
                f"threshold={context.early_leave_threshold}"
            )


# ---------------------------------------------------------------------------
# Property 23: Violation Counter Increment
# ---------------------------------------------------------------------------


class TestProperty23ViolationCounterIncrement:
    """Property 23: Violation Counter Increment.

    For any attendance violation that is flagged, the employee's violation
    counter for the current calendar month SHALL increase by exactly 1,
    and the counter for the current calendar year SHALL increase by exactly 1.

    **Validates: Requirements 7.5**
    """

    @settings(max_examples=100)
    @given(scenario=violation_counter_scenario())
    def test_violation_increments_counters_by_one(
        self,
        scenario: tuple[AttendanceContext, ViolationCounters],
    ) -> None:
        """Any flagged violation increments monthly and yearly counters by 1.

        **Validates: Requirements 7.5**
        """
        context, initial_counters = scenario
        evaluator = AttendanceEvaluator()
        result = evaluator.evaluate(context)

        # Verify that a violation was detected
        assert len(result.violations) >= 1, "Expected at least one violation"

        # Verify counters incremented by exactly 1
        assert result.violation_counters.monthly_count == (
            initial_counters.monthly_count + 1
        ), (
            f"Monthly counter: expected {initial_counters.monthly_count + 1}, "
            f"got {result.violation_counters.monthly_count}"
        )
        assert result.violation_counters.yearly_count == (
            initial_counters.yearly_count + 1
        ), (
            f"Yearly counter: expected {initial_counters.yearly_count + 1}, "
            f"got {result.violation_counters.yearly_count}"
        )


# ---------------------------------------------------------------------------
# Property 24: Dismissal Alert Threshold
# ---------------------------------------------------------------------------


class TestProperty24DismissalAlertThreshold:
    """Property 24: Dismissal Alert Threshold.

    For any employee whose unauthorized absence count reaches 5 days within
    a rolling 30-day window OR 20 days within a rolling 365-day window, the
    engine SHALL trigger a dismissal-eligible alert. For counts below both
    thresholds, no dismissal alert SHALL be triggered.

    **Validates: Requirements 7.6**
    """

    @settings(max_examples=100)
    @given(scenario=dismissal_alert_scenario())
    def test_dismissal_alert_triggered_at_threshold(
        self,
        scenario: tuple[AttendanceContext, bool],
    ) -> None:
        """Dismissal alert triggered at 5/30d OR 20/365d, not below.

        **Validates: Requirements 7.6**
        """
        context, should_trigger = scenario
        evaluator = AttendanceEvaluator()
        result = evaluator.evaluate(context)

        # Verify the event was marked absent
        assert result.status == "absent"

        dismissal_alerts = [
            a for a in result.triggered_alerts
            if a.alert_type == "dismissal_eligible"
        ]

        if should_trigger:
            assert len(dismissal_alerts) >= 1, (
                f"Expected dismissal alert but got none. "
                f"absent_30d={result.violation_counters.absent_days_30d}, "
                f"absent_365d={result.violation_counters.absent_days_365d}"
            )
        else:
            assert len(dismissal_alerts) == 0, (
                f"Expected NO dismissal alert but got {len(dismissal_alerts)}. "
                f"absent_30d={result.violation_counters.absent_days_30d}, "
                f"absent_365d={result.violation_counters.absent_days_365d}"
            )
