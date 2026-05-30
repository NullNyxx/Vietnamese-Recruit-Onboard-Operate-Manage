"""Attendance policy evaluator for the Policy Engine module.

Implements domain-specific attendance evaluation logic including:
- Late detection based on configurable threshold
- Early leave detection based on configurable threshold
- Absent marking when no check-in by 30 min after shift end
- Incomplete marking when check-in but no check-out by 60 min after shift end
- Violation counter management (monthly and yearly)
- Dismissal-eligible alert triggering (Article 125)
- Disciplinary escalation when monthly threshold reached

This evaluator extends the generic evaluation service with attendance-
specific business rules aligned with the Vietnamese Labor Code 2019.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes for attendance evaluation context and results
# ---------------------------------------------------------------------------


@dataclass
class AttendanceContext:
    """Input context for attendance policy evaluation.

    Attributes:
        check_in_time: The employee's actual check-in time, or None if absent.
        check_out_time: The employee's actual check-out time, or None if missing.
        scheduled_start: The scheduled start time for the shift.
        scheduled_end: The scheduled end time for the shift.
        approved_leave: Whether the employee has approved leave for this date.
        approved_overtime: Whether the employee has approved overtime for this date.
        late_threshold: Configurable late threshold (default 15 minutes).
        early_leave_threshold: Configurable early leave threshold (default 15 minutes).
        violation_counters: Current violation counters for the employee.
        current_time: The current evaluation time (for absent/incomplete checks).
    """

    check_in_time: datetime | None
    check_out_time: datetime | None
    scheduled_start: datetime
    scheduled_end: datetime
    approved_leave: bool = False
    approved_overtime: bool = False
    late_threshold: timedelta = field(default_factory=lambda: timedelta(minutes=15))
    early_leave_threshold: timedelta = field(default_factory=lambda: timedelta(minutes=15))
    violation_counters: ViolationCounters | None = None
    current_time: datetime | None = None


@dataclass
class ViolationCounters:
    """Tracks violation counts for an employee.

    Attributes:
        monthly_count: Number of violations in the current calendar month.
        yearly_count: Number of violations in the current calendar year.
        absent_days_30d: Number of unauthorized absent days in rolling 30-day window.
        absent_days_365d: Number of unauthorized absent days in rolling 365-day window.
        monthly_disciplinary_threshold: Threshold for triggering disciplinary escalation.
    """

    monthly_count: int = 0
    yearly_count: int = 0
    absent_days_30d: int = 0
    absent_days_365d: int = 0
    monthly_disciplinary_threshold: int = 3


@dataclass
class AttendanceViolation:
    """Represents a single attendance violation detected.

    Attributes:
        violation_type: The type of violation (late, early_leave, absent, incomplete).
        details: Additional details about the violation.
    """

    violation_type: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class TriggeredAlert:
    """Represents an alert triggered by the evaluation.

    Attributes:
        alert_type: The type of alert (dismissal_eligible, disciplinary_escalation).
        message: Human-readable description of the alert.
        details: Additional alert context data.
    """

    alert_type: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class AttendanceEvaluationResult:
    """Complete result of an attendance policy evaluation.

    Attributes:
        status: The attendance status (on_time, late, early_leave, absent, incomplete).
        violations: List of violations detected.
        violation_counters: Updated violation counters after evaluation.
        triggered_alerts: List of alerts triggered by the evaluation.
        actions: List of action dicts for downstream processing.
    """

    status: str = "on_time"
    violations: list[AttendanceViolation] = field(default_factory=list)
    violation_counters: ViolationCounters = field(default_factory=ViolationCounters)
    triggered_alerts: list[TriggeredAlert] = field(default_factory=list)
    actions: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the evaluation result to a plain dictionary."""
        return {
            "status": self.status,
            "violations": [
                {"violation_type": v.violation_type, "details": v.details} for v in self.violations
            ],
            "violation_counters": {
                "monthly_count": self.violation_counters.monthly_count,
                "yearly_count": self.violation_counters.yearly_count,
                "absent_days_30d": self.violation_counters.absent_days_30d,
                "absent_days_365d": self.violation_counters.absent_days_365d,
            },
            "triggered_alerts": [
                {
                    "alert_type": a.alert_type,
                    "message": a.message,
                    "details": a.details,
                }
                for a in self.triggered_alerts
            ],
            "actions": self.actions,
        }


# ---------------------------------------------------------------------------
# Attendance Evaluator
# ---------------------------------------------------------------------------


class AttendanceEvaluator:
    """Evaluates attendance policy rules for a given attendance context.

    Implements the attendance-specific evaluation logic as a pure
    domain service. All evaluation methods are deterministic and
    side-effect free, making them easily testable.

    The evaluator checks for:
    1. Late arrival (check_in_time − scheduled_start > late_threshold)
    2. Early leave (scheduled_end − check_out_time > early_leave_threshold)
    3. Absent (no check-in by 30 min after shift end, no approved leave)
    4. Incomplete (check-in but no check-out by 60 min after shift end, no overtime)

    After detecting violations, it:
    - Increments monthly and yearly violation counters
    - Checks dismissal thresholds (5 days/30-day or 20 days/365-day)
    - Triggers disciplinary escalation when monthly threshold reached
    """

    # Default thresholds for absent and incomplete detection
    ABSENT_GRACE_PERIOD = timedelta(minutes=30)
    INCOMPLETE_GRACE_PERIOD = timedelta(minutes=60)

    # Dismissal thresholds per Article 125 of Labor Code 2019
    DISMISSAL_THRESHOLD_30D = 5
    DISMISSAL_THRESHOLD_365D = 20

    def evaluate(self, context: AttendanceContext) -> AttendanceEvaluationResult:
        """Evaluate attendance rules against the provided context.

        Applies all attendance checks in order and returns the
        comprehensive evaluation result with status, violations,
        updated counters, and triggered alerts.

        Args:
            context: The attendance evaluation context.

        Returns:
            An AttendanceEvaluationResult with status, violations,
            counters, and alerts.
        """
        # Initialize counters from context or defaults
        counters = ViolationCounters(
            monthly_count=context.violation_counters.monthly_count
            if context.violation_counters
            else 0,
            yearly_count=context.violation_counters.yearly_count
            if context.violation_counters
            else 0,
            absent_days_30d=context.violation_counters.absent_days_30d
            if context.violation_counters
            else 0,
            absent_days_365d=context.violation_counters.absent_days_365d
            if context.violation_counters
            else 0,
            monthly_disciplinary_threshold=(
                context.violation_counters.monthly_disciplinary_threshold
                if context.violation_counters
                else 3
            ),
        )

        result = AttendanceEvaluationResult(violation_counters=counters)

        # Determine current time for absent/incomplete checks
        current_time = context.current_time or datetime.now(context.scheduled_start.tzinfo)

        # Check absent first (highest severity)
        if self._is_absent(context, current_time):
            result.status = "absent"
            violation = AttendanceViolation(
                violation_type="absent",
                details={
                    "reason": "No check-in recorded by 30 minutes after shift end",
                    "scheduled_end": context.scheduled_end.isoformat(),
                    "deadline": (context.scheduled_end + self.ABSENT_GRACE_PERIOD).isoformat(),
                },
            )
            result.violations.append(violation)
            self._increment_counters(counters)
            self._increment_absent_counters(counters)
            self._check_dismissal_threshold(result)
            self._check_disciplinary_escalation(result)
            result.actions.append(
                {
                    "type": "flag",
                    "parameters": {"status": "absent"},
                }
            )
            return result

        # Check incomplete (check-in but no check-out)
        if self._is_incomplete(context, current_time):
            result.status = "incomplete"
            violation = AttendanceViolation(
                violation_type="incomplete",
                details={
                    "reason": ("Check-in recorded but no check-out by 60 minutes after shift end"),
                    "check_in_time": context.check_in_time.isoformat()
                    if context.check_in_time
                    else None,
                    "scheduled_end": context.scheduled_end.isoformat(),
                    "deadline": (context.scheduled_end + self.INCOMPLETE_GRACE_PERIOD).isoformat(),
                },
            )
            result.violations.append(violation)
            self._increment_counters(counters)
            self._check_disciplinary_escalation(result)
            result.actions.append(
                {
                    "type": "flag",
                    "parameters": {"status": "incomplete"},
                }
            )
            result.actions.append(
                {
                    "type": "notify",
                    "parameters": {
                        "target": "direct_manager",
                        "message": "Employee checked in but has no check-out record",
                    },
                }
            )
            return result

        # Check late arrival
        if self._is_late(context):
            result.status = "late"
            late_duration = context.check_in_time - context.scheduled_start  # type: ignore[operator]
            violation = AttendanceViolation(
                violation_type="late",
                details={
                    "check_in_time": context.check_in_time.isoformat()  # type: ignore[union-attr]
                    if context.check_in_time
                    else None,
                    "scheduled_start": context.scheduled_start.isoformat(),
                    "late_threshold_minutes": context.late_threshold.total_seconds() / 60,
                    "late_duration_minutes": late_duration.total_seconds() / 60,
                },
            )
            result.violations.append(violation)
            self._increment_counters(counters)
            self._check_disciplinary_escalation(result)
            result.actions.append(
                {
                    "type": "flag",
                    "parameters": {"status": "late"},
                }
            )

        # Check early leave
        if self._is_early_leave(context):
            # If already marked late, status becomes late (first violation takes precedence)
            # but we still record the early_leave violation
            if result.status == "on_time":
                result.status = "early_leave"
            early_duration = (
                context.scheduled_end - context.check_out_time  # type: ignore[operator]
            )
            violation = AttendanceViolation(
                violation_type="early_leave",
                details={
                    "check_out_time": context.check_out_time.isoformat()  # type: ignore[union-attr]
                    if context.check_out_time
                    else None,
                    "scheduled_end": context.scheduled_end.isoformat(),
                    "early_leave_threshold_minutes": (
                        context.early_leave_threshold.total_seconds() / 60
                    ),
                    "early_duration_minutes": early_duration.total_seconds() / 60,
                },
            )
            result.violations.append(violation)
            # Only increment counters if this is the first violation detected
            if result.status == "early_leave":
                self._increment_counters(counters)
                self._check_disciplinary_escalation(result)
            result.actions.append(
                {
                    "type": "flag",
                    "parameters": {"status": "early_leave"},
                }
            )

        return result

    # -----------------------------------------------------------------------
    # Private: Violation detection methods
    # -----------------------------------------------------------------------

    def _is_late(self, context: AttendanceContext) -> bool:
        """Check if the employee arrived late.

        An employee is late when:
        (check_in_time − scheduled_start) > late_threshold

        Args:
            context: The attendance evaluation context.

        Returns:
            True if the employee is late, False otherwise.
        """
        if context.check_in_time is None:
            return False

        time_diff = context.check_in_time - context.scheduled_start
        return time_diff > context.late_threshold

    def _is_early_leave(self, context: AttendanceContext) -> bool:
        """Check if the employee left early.

        An employee left early when:
        (scheduled_end − check_out_time) > early_leave_threshold

        Args:
            context: The attendance evaluation context.

        Returns:
            True if the employee left early, False otherwise.
        """
        if context.check_out_time is None:
            return False

        time_diff = context.scheduled_end - context.check_out_time
        return time_diff > context.early_leave_threshold

    def _is_absent(self, context: AttendanceContext, current_time: datetime) -> bool:
        """Check if the employee is absent.

        An employee is absent when:
        - No check-in is recorded
        - Current time is past 30 minutes after the scheduled end
        - No approved leave exists for this date

        Args:
            context: The attendance evaluation context.
            current_time: The current evaluation time.

        Returns:
            True if the employee should be marked absent, False otherwise.
        """
        if context.check_in_time is not None:
            return False

        if context.approved_leave:
            return False

        deadline = context.scheduled_end + self.ABSENT_GRACE_PERIOD
        return current_time > deadline

    def _is_incomplete(self, context: AttendanceContext, current_time: datetime) -> bool:
        """Check if the attendance record is incomplete.

        An attendance record is incomplete when:
        - Check-in is recorded
        - No check-out is recorded
        - Current time is past 60 minutes after the scheduled end
        - No approved overtime exists for this date

        Args:
            context: The attendance evaluation context.
            current_time: The current evaluation time.

        Returns:
            True if the record should be marked incomplete, False otherwise.
        """
        if context.check_in_time is None:
            return False

        if context.check_out_time is not None:
            return False

        if context.approved_overtime:
            return False

        deadline = context.scheduled_end + self.INCOMPLETE_GRACE_PERIOD
        return current_time > deadline

    # -----------------------------------------------------------------------
    # Private: Counter management
    # -----------------------------------------------------------------------

    def _increment_counters(self, counters: ViolationCounters) -> None:
        """Increment monthly and yearly violation counters.

        Called when any attendance violation is flagged.

        Args:
            counters: The violation counters to increment.
        """
        counters.monthly_count += 1
        counters.yearly_count += 1

    def _increment_absent_counters(self, counters: ViolationCounters) -> None:
        """Increment absent-specific rolling window counters.

        Called specifically for absent violations to track dismissal
        thresholds per Article 125.

        Args:
            counters: The violation counters to increment.
        """
        counters.absent_days_30d += 1
        counters.absent_days_365d += 1

    # -----------------------------------------------------------------------
    # Private: Alert triggering
    # -----------------------------------------------------------------------

    def _check_dismissal_threshold(self, result: AttendanceEvaluationResult) -> None:
        """Check if dismissal-eligible alert should be triggered.

        Triggers alert when unauthorized absence reaches:
        - 5 days within a rolling 30-day window, OR
        - 20 days within a rolling 365-day window

        Per Article 125 of the Vietnamese Labor Code 2019.

        Args:
            result: The evaluation result to add alerts to.
        """
        counters = result.violation_counters

        if counters.absent_days_30d >= self.DISMISSAL_THRESHOLD_30D:
            alert = TriggeredAlert(
                alert_type="dismissal_eligible",
                message=(
                    f"Employee has {counters.absent_days_30d} unauthorized absent days "
                    f"within 30-day window (threshold: {self.DISMISSAL_THRESHOLD_30D}). "
                    f"Dismissal eligible per Article 125."
                ),
                details={
                    "threshold_type": "30_day",
                    "absent_days": counters.absent_days_30d,
                    "threshold": self.DISMISSAL_THRESHOLD_30D,
                    "legal_reference": "Article 125, Labor Code 2019",
                },
            )
            result.triggered_alerts.append(alert)
            result.actions.append(
                {
                    "type": "escalate",
                    "parameters": {
                        "action": "dismissal_eligible",
                        "notify": ["hr_admin", "direct_manager"],
                    },
                }
            )

        if counters.absent_days_365d >= self.DISMISSAL_THRESHOLD_365D:
            alert = TriggeredAlert(
                alert_type="dismissal_eligible",
                message=(
                    f"Employee has {counters.absent_days_365d} unauthorized absent days "
                    f"within 365-day window (threshold: {self.DISMISSAL_THRESHOLD_365D}). "
                    f"Dismissal eligible per Article 125."
                ),
                details={
                    "threshold_type": "365_day",
                    "absent_days": counters.absent_days_365d,
                    "threshold": self.DISMISSAL_THRESHOLD_365D,
                    "legal_reference": "Article 125, Labor Code 2019",
                },
            )
            result.triggered_alerts.append(alert)
            result.actions.append(
                {
                    "type": "escalate",
                    "parameters": {
                        "action": "dismissal_eligible",
                        "notify": ["hr_admin", "direct_manager"],
                    },
                }
            )

    def _check_disciplinary_escalation(self, result: AttendanceEvaluationResult) -> None:
        """Check if disciplinary escalation should be triggered.

        Triggers escalation when the monthly violation count reaches
        the tenant's configured disciplinary threshold.

        Args:
            result: The evaluation result to add alerts to.
        """
        counters = result.violation_counters

        if counters.monthly_count >= counters.monthly_disciplinary_threshold:
            alert = TriggeredAlert(
                alert_type="disciplinary_escalation",
                message=(
                    f"Employee has {counters.monthly_count} violations this month "
                    f"(threshold: {counters.monthly_disciplinary_threshold}). "
                    f"Disciplinary escalation triggered."
                ),
                details={
                    "monthly_count": counters.monthly_count,
                    "threshold": counters.monthly_disciplinary_threshold,
                },
            )
            result.triggered_alerts.append(alert)
            result.actions.append(
                {
                    "type": "escalate",
                    "parameters": {
                        "action": "disciplinary_escalation",
                        "notify": ["hr_admin"],
                    },
                }
            )


# ---------------------------------------------------------------------------
# Helper: Build AttendanceContext from raw evaluation context dict
# ---------------------------------------------------------------------------


def build_attendance_context(context: dict[str, Any]) -> AttendanceContext:
    """Build an AttendanceContext from a raw evaluation context dictionary.

    Parses datetime strings and extracts relevant fields from the
    generic policy evaluation context into a typed AttendanceContext.

    Args:
        context: Raw evaluation context dict with string datetime values.

    Returns:
        A typed AttendanceContext ready for evaluation.
    """

    def _parse_datetime(value: Any) -> datetime | None:
        """Parse a datetime value from string or return as-is if already datetime."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return None

    check_in_time = _parse_datetime(context.get("check_in_time"))
    check_out_time = _parse_datetime(context.get("check_out_time"))
    scheduled_start = _parse_datetime(context.get("scheduled_start"))
    scheduled_end = _parse_datetime(context.get("scheduled_end"))
    current_time = _parse_datetime(context.get("current_time"))

    if scheduled_start is None or scheduled_end is None:
        raise ValueError("scheduled_start and scheduled_end are required")

    # Parse thresholds (in minutes)
    late_threshold_minutes = context.get("late_threshold_minutes", 15)
    early_leave_threshold_minutes = context.get("early_leave_threshold_minutes", 15)

    # Parse violation counters
    counters_data = context.get("violation_counters")
    violation_counters: ViolationCounters | None = None
    if counters_data and isinstance(counters_data, dict):
        violation_counters = ViolationCounters(
            monthly_count=counters_data.get("monthly_count", 0),
            yearly_count=counters_data.get("yearly_count", 0),
            absent_days_30d=counters_data.get("absent_days_30d", 0),
            absent_days_365d=counters_data.get("absent_days_365d", 0),
            monthly_disciplinary_threshold=counters_data.get("monthly_disciplinary_threshold", 3),
        )

    return AttendanceContext(
        check_in_time=check_in_time,
        check_out_time=check_out_time,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        approved_leave=bool(context.get("approved_leave", False)),
        approved_overtime=bool(context.get("approved_overtime", False)),
        late_threshold=timedelta(minutes=late_threshold_minutes),
        early_leave_threshold=timedelta(minutes=early_leave_threshold_minutes),
        violation_counters=violation_counters,
        current_time=current_time,
    )
