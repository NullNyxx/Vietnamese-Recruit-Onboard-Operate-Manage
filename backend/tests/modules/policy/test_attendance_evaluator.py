"""Unit tests for the AttendanceEvaluator class.

Tests attendance-specific evaluation logic including late detection,
early leave detection, absent marking, incomplete marking, violation
counter management, and alert triggering.
"""

from datetime import UTC, datetime, timedelta

import pytest

from src.modules.policy.application.attendance_evaluator import (
    AttendanceContext,
    AttendanceEvaluator,
    ViolationCounters,
    build_attendance_context,
)

UTC = UTC


@pytest.fixture
def evaluator() -> AttendanceEvaluator:
    """Create an AttendanceEvaluator instance."""
    return AttendanceEvaluator()


@pytest.fixture
def base_schedule() -> tuple[datetime, datetime]:
    """Standard 8-hour shift: 08:00 to 17:00."""
    start = datetime(2024, 6, 10, 8, 0, 0, tzinfo=UTC)
    end = datetime(2024, 6, 10, 17, 0, 0, tzinfo=UTC)
    return start, end


class TestLateDetection:
    """Tests for late arrival detection."""

    def test_on_time_check_in(
        self, evaluator: AttendanceEvaluator, base_schedule: tuple[datetime, datetime]
    ) -> None:
        """Employee checking in at scheduled start is not late."""
        start, end = base_schedule
        context = AttendanceContext(
            check_in_time=start,
            check_out_time=end,
            scheduled_start=start,
            scheduled_end=end,
        )
        result = evaluator.evaluate(context)
        assert result.status == "on_time"
        assert len(result.violations) == 0

    def test_within_threshold_not_late(
        self, evaluator: AttendanceEvaluator, base_schedule: tuple[datetime, datetime]
    ) -> None:
        """Employee checking in within threshold is not late."""
        start, end = base_schedule
        context = AttendanceContext(
            check_in_time=start + timedelta(minutes=14),
            check_out_time=end,
            scheduled_start=start,
            scheduled_end=end,
            late_threshold=timedelta(minutes=15),
        )
        result = evaluator.evaluate(context)
        assert result.status == "on_time"
        assert len(result.violations) == 0

    def test_exactly_at_threshold_not_late(
        self, evaluator: AttendanceEvaluator, base_schedule: tuple[datetime, datetime]
    ) -> None:
        """Employee checking in exactly at threshold boundary is not late."""
        start, end = base_schedule
        context = AttendanceContext(
            check_in_time=start + timedelta(minutes=15),
            check_out_time=end,
            scheduled_start=start,
            scheduled_end=end,
            late_threshold=timedelta(minutes=15),
        )
        result = evaluator.evaluate(context)
        assert result.status == "on_time"
        assert len(result.violations) == 0

    def test_exceeds_threshold_is_late(
        self, evaluator: AttendanceEvaluator, base_schedule: tuple[datetime, datetime]
    ) -> None:
        """Employee checking in beyond threshold is marked late."""
        start, end = base_schedule
        context = AttendanceContext(
            check_in_time=start + timedelta(minutes=16),
            check_out_time=end,
            scheduled_start=start,
            scheduled_end=end,
            late_threshold=timedelta(minutes=15),
        )
        result = evaluator.evaluate(context)
        assert result.status == "late"
        assert len(result.violations) == 1
        assert result.violations[0].violation_type == "late"

    def test_custom_threshold(
        self, evaluator: AttendanceEvaluator, base_schedule: tuple[datetime, datetime]
    ) -> None:
        """Custom late threshold is respected."""
        start, end = base_schedule
        context = AttendanceContext(
            check_in_time=start + timedelta(minutes=25),
            check_out_time=end,
            scheduled_start=start,
            scheduled_end=end,
            late_threshold=timedelta(minutes=30),
        )
        result = evaluator.evaluate(context)
        assert result.status == "on_time"

    def test_late_increments_counters(
        self, evaluator: AttendanceEvaluator, base_schedule: tuple[datetime, datetime]
    ) -> None:
        """Late violation increments monthly and yearly counters."""
        start, end = base_schedule
        context = AttendanceContext(
            check_in_time=start + timedelta(minutes=20),
            check_out_time=end,
            scheduled_start=start,
            scheduled_end=end,
            violation_counters=ViolationCounters(monthly_count=2, yearly_count=5),
        )
        result = evaluator.evaluate(context)
        assert result.violation_counters.monthly_count == 3
        assert result.violation_counters.yearly_count == 6


class TestEarlyLeaveDetection:
    """Tests for early leave detection."""

    def test_normal_checkout_not_early(
        self, evaluator: AttendanceEvaluator, base_schedule: tuple[datetime, datetime]
    ) -> None:
        """Employee checking out at scheduled end is not early leave."""
        start, end = base_schedule
        context = AttendanceContext(
            check_in_time=start,
            check_out_time=end,
            scheduled_start=start,
            scheduled_end=end,
        )
        result = evaluator.evaluate(context)
        assert result.status == "on_time"

    def test_within_threshold_not_early(
        self, evaluator: AttendanceEvaluator, base_schedule: tuple[datetime, datetime]
    ) -> None:
        """Employee leaving within threshold is not early leave."""
        start, end = base_schedule
        context = AttendanceContext(
            check_in_time=start,
            check_out_time=end - timedelta(minutes=14),
            scheduled_start=start,
            scheduled_end=end,
            early_leave_threshold=timedelta(minutes=15),
        )
        result = evaluator.evaluate(context)
        assert result.status == "on_time"

    def test_exactly_at_threshold_not_early(
        self, evaluator: AttendanceEvaluator, base_schedule: tuple[datetime, datetime]
    ) -> None:
        """Employee leaving exactly at threshold boundary is not early leave."""
        start, end = base_schedule
        context = AttendanceContext(
            check_in_time=start,
            check_out_time=end - timedelta(minutes=15),
            scheduled_start=start,
            scheduled_end=end,
            early_leave_threshold=timedelta(minutes=15),
        )
        result = evaluator.evaluate(context)
        assert result.status == "on_time"

    def test_exceeds_threshold_is_early_leave(
        self, evaluator: AttendanceEvaluator, base_schedule: tuple[datetime, datetime]
    ) -> None:
        """Employee leaving beyond threshold is marked early_leave."""
        start, end = base_schedule
        context = AttendanceContext(
            check_in_time=start,
            check_out_time=end - timedelta(minutes=16),
            scheduled_start=start,
            scheduled_end=end,
            early_leave_threshold=timedelta(minutes=15),
        )
        result = evaluator.evaluate(context)
        assert result.status == "early_leave"
        assert len(result.violations) == 1
        assert result.violations[0].violation_type == "early_leave"

    def test_early_leave_increments_counters(
        self, evaluator: AttendanceEvaluator, base_schedule: tuple[datetime, datetime]
    ) -> None:
        """Early leave violation increments monthly and yearly counters."""
        start, end = base_schedule
        context = AttendanceContext(
            check_in_time=start,
            check_out_time=end - timedelta(minutes=20),
            scheduled_start=start,
            scheduled_end=end,
            violation_counters=ViolationCounters(monthly_count=1, yearly_count=3),
        )
        result = evaluator.evaluate(context)
        assert result.violation_counters.monthly_count == 2
        assert result.violation_counters.yearly_count == 4


class TestAbsentDetection:
    """Tests for absent marking."""

    def test_no_checkin_past_deadline_marked_absent(
        self, evaluator: AttendanceEvaluator, base_schedule: tuple[datetime, datetime]
    ) -> None:
        """No check-in past 30 min after shift end is marked absent."""
        start, end = base_schedule
        context = AttendanceContext(
            check_in_time=None,
            check_out_time=None,
            scheduled_start=start,
            scheduled_end=end,
            current_time=end + timedelta(minutes=31),
        )
        result = evaluator.evaluate(context)
        assert result.status == "absent"
        assert len(result.violations) == 1
        assert result.violations[0].violation_type == "absent"

    def test_no_checkin_before_deadline_not_absent(
        self, evaluator: AttendanceEvaluator, base_schedule: tuple[datetime, datetime]
    ) -> None:
        """No check-in before 30 min deadline is not yet marked absent."""
        start, end = base_schedule
        context = AttendanceContext(
            check_in_time=None,
            check_out_time=None,
            scheduled_start=start,
            scheduled_end=end,
            current_time=end + timedelta(minutes=29),
        )
        result = evaluator.evaluate(context)
        assert result.status == "on_time"
        assert len(result.violations) == 0

    def test_approved_leave_prevents_absent(
        self, evaluator: AttendanceEvaluator, base_schedule: tuple[datetime, datetime]
    ) -> None:
        """Approved leave prevents absent marking."""
        start, end = base_schedule
        context = AttendanceContext(
            check_in_time=None,
            check_out_time=None,
            scheduled_start=start,
            scheduled_end=end,
            approved_leave=True,
            current_time=end + timedelta(minutes=60),
        )
        result = evaluator.evaluate(context)
        assert result.status == "on_time"
        assert len(result.violations) == 0

    def test_absent_increments_absent_counters(
        self, evaluator: AttendanceEvaluator, base_schedule: tuple[datetime, datetime]
    ) -> None:
        """Absent violation increments absent-specific counters."""
        start, end = base_schedule
        context = AttendanceContext(
            check_in_time=None,
            check_out_time=None,
            scheduled_start=start,
            scheduled_end=end,
            current_time=end + timedelta(minutes=31),
            violation_counters=ViolationCounters(absent_days_30d=2, absent_days_365d=10),
        )
        result = evaluator.evaluate(context)
        assert result.violation_counters.absent_days_30d == 3
        assert result.violation_counters.absent_days_365d == 11


class TestIncompleteDetection:
    """Tests for incomplete attendance record detection."""

    def test_checkin_no_checkout_past_deadline_marked_incomplete(
        self, evaluator: AttendanceEvaluator, base_schedule: tuple[datetime, datetime]
    ) -> None:
        """Check-in but no check-out past 60 min after shift end is incomplete."""
        start, end = base_schedule
        context = AttendanceContext(
            check_in_time=start,
            check_out_time=None,
            scheduled_start=start,
            scheduled_end=end,
            current_time=end + timedelta(minutes=61),
        )
        result = evaluator.evaluate(context)
        assert result.status == "incomplete"
        assert len(result.violations) == 1
        assert result.violations[0].violation_type == "incomplete"

    def test_checkin_no_checkout_before_deadline_not_incomplete(
        self, evaluator: AttendanceEvaluator, base_schedule: tuple[datetime, datetime]
    ) -> None:
        """Check-in but no check-out before 60 min deadline is not incomplete."""
        start, end = base_schedule
        context = AttendanceContext(
            check_in_time=start,
            check_out_time=None,
            scheduled_start=start,
            scheduled_end=end,
            current_time=end + timedelta(minutes=59),
        )
        result = evaluator.evaluate(context)
        assert result.status == "on_time"
        assert len(result.violations) == 0

    def test_approved_overtime_prevents_incomplete(
        self, evaluator: AttendanceEvaluator, base_schedule: tuple[datetime, datetime]
    ) -> None:
        """Approved overtime prevents incomplete marking."""
        start, end = base_schedule
        context = AttendanceContext(
            check_in_time=start,
            check_out_time=None,
            scheduled_start=start,
            scheduled_end=end,
            approved_overtime=True,
            current_time=end + timedelta(minutes=120),
        )
        result = evaluator.evaluate(context)
        assert result.status == "on_time"
        assert len(result.violations) == 0

    def test_incomplete_notifies_manager(
        self, evaluator: AttendanceEvaluator, base_schedule: tuple[datetime, datetime]
    ) -> None:
        """Incomplete status triggers manager notification."""
        start, end = base_schedule
        context = AttendanceContext(
            check_in_time=start,
            check_out_time=None,
            scheduled_start=start,
            scheduled_end=end,
            current_time=end + timedelta(minutes=61),
        )
        result = evaluator.evaluate(context)
        notify_actions = [a for a in result.actions if a["type"] == "notify"]
        assert len(notify_actions) == 1
        assert notify_actions[0]["parameters"]["target"] == "direct_manager"


class TestDismissalAlert:
    """Tests for dismissal-eligible alert triggering."""

    def test_5_absent_days_in_30d_triggers_alert(
        self, evaluator: AttendanceEvaluator, base_schedule: tuple[datetime, datetime]
    ) -> None:
        """5 absent days in 30-day window triggers dismissal alert."""
        start, end = base_schedule
        context = AttendanceContext(
            check_in_time=None,
            check_out_time=None,
            scheduled_start=start,
            scheduled_end=end,
            current_time=end + timedelta(minutes=31),
            violation_counters=ViolationCounters(absent_days_30d=4),
        )
        result = evaluator.evaluate(context)
        dismissal_alerts = [
            a for a in result.triggered_alerts if a.alert_type == "dismissal_eligible"
        ]
        assert len(dismissal_alerts) >= 1
        assert any(a.details.get("threshold_type") == "30_day" for a in dismissal_alerts)

    def test_20_absent_days_in_365d_triggers_alert(
        self, evaluator: AttendanceEvaluator, base_schedule: tuple[datetime, datetime]
    ) -> None:
        """20 absent days in 365-day window triggers dismissal alert."""
        start, end = base_schedule
        context = AttendanceContext(
            check_in_time=None,
            check_out_time=None,
            scheduled_start=start,
            scheduled_end=end,
            current_time=end + timedelta(minutes=31),
            violation_counters=ViolationCounters(absent_days_365d=19),
        )
        result = evaluator.evaluate(context)
        dismissal_alerts = [
            a for a in result.triggered_alerts if a.alert_type == "dismissal_eligible"
        ]
        assert len(dismissal_alerts) >= 1
        assert any(a.details.get("threshold_type") == "365_day" for a in dismissal_alerts)

    def test_below_threshold_no_alert(
        self, evaluator: AttendanceEvaluator, base_schedule: tuple[datetime, datetime]
    ) -> None:
        """Below both thresholds does not trigger dismissal alert."""
        start, end = base_schedule
        context = AttendanceContext(
            check_in_time=None,
            check_out_time=None,
            scheduled_start=start,
            scheduled_end=end,
            current_time=end + timedelta(minutes=31),
            violation_counters=ViolationCounters(absent_days_30d=3, absent_days_365d=15),
        )
        result = evaluator.evaluate(context)
        dismissal_alerts = [
            a for a in result.triggered_alerts if a.alert_type == "dismissal_eligible"
        ]
        assert len(dismissal_alerts) == 0


class TestDisciplinaryEscalation:
    """Tests for disciplinary escalation triggering."""

    def test_monthly_threshold_triggers_escalation(
        self, evaluator: AttendanceEvaluator, base_schedule: tuple[datetime, datetime]
    ) -> None:
        """Reaching monthly threshold triggers disciplinary escalation."""
        start, end = base_schedule
        context = AttendanceContext(
            check_in_time=start + timedelta(minutes=20),
            check_out_time=end,
            scheduled_start=start,
            scheduled_end=end,
            violation_counters=ViolationCounters(monthly_count=2, monthly_disciplinary_threshold=3),
        )
        result = evaluator.evaluate(context)
        escalation_alerts = [
            a for a in result.triggered_alerts if a.alert_type == "disciplinary_escalation"
        ]
        assert len(escalation_alerts) == 1

    def test_below_monthly_threshold_no_escalation(
        self, evaluator: AttendanceEvaluator, base_schedule: tuple[datetime, datetime]
    ) -> None:
        """Below monthly threshold does not trigger escalation."""
        start, end = base_schedule
        context = AttendanceContext(
            check_in_time=start + timedelta(minutes=20),
            check_out_time=end,
            scheduled_start=start,
            scheduled_end=end,
            violation_counters=ViolationCounters(monthly_count=1, monthly_disciplinary_threshold=3),
        )
        result = evaluator.evaluate(context)
        escalation_alerts = [
            a for a in result.triggered_alerts if a.alert_type == "disciplinary_escalation"
        ]
        assert len(escalation_alerts) == 0


class TestBuildAttendanceContext:
    """Tests for the build_attendance_context helper function."""

    def test_builds_from_dict_with_strings(self) -> None:
        """Builds context from dict with ISO datetime strings."""
        raw = {
            "check_in_time": "2024-06-10T08:20:00+00:00",
            "check_out_time": "2024-06-10T17:00:00+00:00",
            "scheduled_start": "2024-06-10T08:00:00+00:00",
            "scheduled_end": "2024-06-10T17:00:00+00:00",
            "late_threshold_minutes": 15,
            "early_leave_threshold_minutes": 15,
            "approved_leave": False,
            "approved_overtime": False,
        }
        ctx = build_attendance_context(raw)
        assert ctx.check_in_time is not None
        assert ctx.scheduled_start == datetime(2024, 6, 10, 8, 0, 0, tzinfo=UTC)
        assert ctx.late_threshold == timedelta(minutes=15)

    def test_builds_with_none_check_in(self) -> None:
        """Builds context with None check-in time."""
        raw = {
            "check_in_time": None,
            "check_out_time": None,
            "scheduled_start": "2024-06-10T08:00:00+00:00",
            "scheduled_end": "2024-06-10T17:00:00+00:00",
        }
        ctx = build_attendance_context(raw)
        assert ctx.check_in_time is None
        assert ctx.check_out_time is None

    def test_raises_on_missing_schedule(self) -> None:
        """Raises ValueError when scheduled times are missing."""
        raw = {"check_in_time": "2024-06-10T08:00:00+00:00"}
        with pytest.raises(ValueError, match="scheduled_start and scheduled_end are required"):
            build_attendance_context(raw)

    def test_builds_with_violation_counters(self) -> None:
        """Builds context with violation counters from dict."""
        raw = {
            "scheduled_start": "2024-06-10T08:00:00+00:00",
            "scheduled_end": "2024-06-10T17:00:00+00:00",
            "violation_counters": {
                "monthly_count": 2,
                "yearly_count": 5,
                "absent_days_30d": 1,
                "absent_days_365d": 3,
                "monthly_disciplinary_threshold": 5,
            },
        }
        ctx = build_attendance_context(raw)
        assert ctx.violation_counters is not None
        assert ctx.violation_counters.monthly_count == 2
        assert ctx.violation_counters.yearly_count == 5
        assert ctx.violation_counters.monthly_disciplinary_threshold == 5


class TestEvaluationResultSerialization:
    """Tests for AttendanceEvaluationResult.to_dict()."""

    def test_to_dict_on_time(
        self, evaluator: AttendanceEvaluator, base_schedule: tuple[datetime, datetime]
    ) -> None:
        """On-time result serializes correctly."""
        start, end = base_schedule
        context = AttendanceContext(
            check_in_time=start,
            check_out_time=end,
            scheduled_start=start,
            scheduled_end=end,
        )
        result = evaluator.evaluate(context)
        d = result.to_dict()
        assert d["status"] == "on_time"
        assert d["violations"] == []
        assert d["triggered_alerts"] == []

    def test_to_dict_with_violations(
        self, evaluator: AttendanceEvaluator, base_schedule: tuple[datetime, datetime]
    ) -> None:
        """Result with violations serializes correctly."""
        start, end = base_schedule
        context = AttendanceContext(
            check_in_time=start + timedelta(minutes=20),
            check_out_time=end,
            scheduled_start=start,
            scheduled_end=end,
        )
        result = evaluator.evaluate(context)
        d = result.to_dict()
        assert d["status"] == "late"
        assert len(d["violations"]) == 1
        assert d["violations"][0]["violation_type"] == "late"
