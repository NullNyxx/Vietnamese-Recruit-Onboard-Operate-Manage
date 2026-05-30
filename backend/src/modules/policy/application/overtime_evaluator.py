"""Overtime policy evaluator for the Policy Engine module.

Implements overtime-specific evaluation logic including daily/monthly/yearly
limit validation, overtime pay calculation, and multiplier selection based
on day type (weekday, weekend, holiday). Compliant with Vietnamese Labor
Code 2019 (Article 98, Article 107).

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DayType(str, Enum):
    """Day type classification for overtime multiplier selection."""

    WEEKDAY = "weekday"
    WEEKEND = "weekend"
    HOLIDAY = "holiday"


# ---------------------------------------------------------------------------
# Minimum multipliers per Vietnamese Labor Code 2019, Article 98
# ---------------------------------------------------------------------------

MINIMUM_MULTIPLIERS: dict[DayType, float] = {
    DayType.WEEKDAY: 1.5,  # at least 150%
    DayType.WEEKEND: 2.0,  # at least 200%
    DayType.HOLIDAY: 3.0,  # at least 300%
}


# ---------------------------------------------------------------------------
# Data classes for overtime evaluation context and results
# ---------------------------------------------------------------------------


@dataclass
class OvertimeContext:
    """Input context for overtime policy evaluation.

    Attributes:
        requested_hours: Number of overtime hours requested.
        scheduled_hours: Employee's scheduled regular hours for the day.
        current_monthly_total: Employee's current monthly overtime total.
        current_yearly_total: Employee's current yearly overtime total.
        max_monthly: Tenant-configured maximum monthly overtime hours.
        max_yearly: Tenant-configured maximum yearly overtime hours.
        monthly_salary: Employee's monthly salary for pay calculation.
        standard_days: Standard monthly working days (for hourly rate).
        standard_hours: Standard daily working hours (for hourly rate).
        day_types: List of day types that apply to the work date.
        multipliers: Tenant-configured multipliers per day type.
            Keys are DayType values, values are multiplier floats.
            Must be >= the legal minimums defined in MINIMUM_MULTIPLIERS.
    """

    requested_hours: float
    scheduled_hours: float
    current_monthly_total: float
    current_yearly_total: float
    max_monthly: float
    max_yearly: float
    monthly_salary: float
    standard_days: float
    standard_hours: float
    day_types: list[DayType]
    multipliers: dict[DayType, float] = field(default_factory=dict)


@dataclass
class OvertimeRejection:
    """Details of a limit violation that caused rejection.

    Attributes:
        limit_type: Which limit was exceeded (daily, monthly, yearly).
        limit_value: The configured limit value.
        current_value: The current accumulated value.
        requested_value: The requested hours.
        max_allowed: Maximum hours that could be approved.
        message: Human-readable rejection message.
    """

    limit_type: str
    limit_value: float
    current_value: float
    requested_value: float
    max_allowed: float
    message: str


@dataclass
class OvertimeEvaluationResult:
    """Result of overtime policy evaluation.

    Attributes:
        approved: Whether the overtime request is approved.
        rejections: List of limit violations (if rejected).
        calculated_pay: Overtime pay amount (if approved).
        applied_multiplier: The multiplier used for pay calculation.
        hourly_rate: The computed hourly rate.
        updated_monthly_total: New monthly total after approval.
        updated_yearly_total: New yearly total after approval.
        triggered_actions: List of triggered action dicts.
    """

    approved: bool = False
    rejections: list[OvertimeRejection] = field(default_factory=list)
    calculated_pay: float = 0.0
    applied_multiplier: float = 0.0
    hourly_rate: float = 0.0
    updated_monthly_total: float = 0.0
    updated_yearly_total: float = 0.0
    triggered_actions: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the evaluation result to a plain dictionary."""
        return {
            "approved": self.approved,
            "rejections": [
                {
                    "limit_type": r.limit_type,
                    "limit_value": r.limit_value,
                    "current_value": r.current_value,
                    "requested_value": r.requested_value,
                    "max_allowed": r.max_allowed,
                    "message": r.message,
                }
                for r in self.rejections
            ],
            "calculated_pay": self.calculated_pay,
            "applied_multiplier": self.applied_multiplier,
            "hourly_rate": self.hourly_rate,
            "updated_monthly_total": self.updated_monthly_total,
            "updated_yearly_total": self.updated_yearly_total,
            "triggered_actions": self.triggered_actions,
        }


# ---------------------------------------------------------------------------
# Overtime Evaluator
# ---------------------------------------------------------------------------


class OvertimeEvaluator:
    """Evaluates overtime requests against configured policy limits.

    Validates daily, monthly, and yearly overtime limits per Article 107,
    calculates overtime pay per Article 98, and applies the highest
    multiplier when a date qualifies as multiple day types.

    Usage:
        evaluator = OvertimeEvaluator()
        result = evaluator.evaluate(context)
    """

    def evaluate(self, context: OvertimeContext) -> OvertimeEvaluationResult:
        """Evaluate an overtime request against policy rules.

        Execution flow:
        1. Validate daily limit: (scheduled_hours + overtime_hours) ≤ 12
        2. Validate monthly limit: (current_monthly + requested) ≤ max_monthly
        3. Validate yearly limit: (current_yearly + requested) ≤ max_yearly
        4. If all pass: calculate pay, update totals, approve
        5. If any fail: collect all rejections, reject

        Args:
            context: The overtime evaluation context with all required data.

        Returns:
            An OvertimeEvaluationResult with approval status, pay calculation,
            and any rejection details.
        """
        result = OvertimeEvaluationResult()
        rejections: list[OvertimeRejection] = []

        # Step 1: Validate daily limit (Article 107: max 12 hours total per day)
        daily_total = context.scheduled_hours + context.requested_hours
        daily_max_overtime = 12.0 - context.scheduled_hours
        if daily_total > 12.0:
            rejections.append(
                OvertimeRejection(
                    limit_type="daily",
                    limit_value=12.0,
                    current_value=context.scheduled_hours,
                    requested_value=context.requested_hours,
                    max_allowed=max(0.0, daily_max_overtime),
                    message=(
                        f"Daily limit exceeded: scheduled {context.scheduled_hours}h + "
                        f"requested {context.requested_hours}h = {daily_total}h > 12h. "
                        f"Maximum overtime allowed: {max(0.0, daily_max_overtime)}h."
                    ),
                )
            )

        # Step 2: Validate monthly limit
        monthly_after = context.current_monthly_total + context.requested_hours
        monthly_remaining = context.max_monthly - context.current_monthly_total
        if monthly_after > context.max_monthly:
            rejections.append(
                OvertimeRejection(
                    limit_type="monthly",
                    limit_value=context.max_monthly,
                    current_value=context.current_monthly_total,
                    requested_value=context.requested_hours,
                    max_allowed=max(0.0, monthly_remaining),
                    message=(
                        f"Monthly limit exceeded: current {context.current_monthly_total}h + "
                        f"requested {context.requested_hours}h = {monthly_after}h > "
                        f"{context.max_monthly}h. "
                        f"Remaining monthly hours: {max(0.0, monthly_remaining)}h."
                    ),
                )
            )

        # Step 3: Validate yearly limit
        yearly_after = context.current_yearly_total + context.requested_hours
        yearly_remaining = context.max_yearly - context.current_yearly_total
        if yearly_after > context.max_yearly:
            rejections.append(
                OvertimeRejection(
                    limit_type="yearly",
                    limit_value=context.max_yearly,
                    current_value=context.current_yearly_total,
                    requested_value=context.requested_hours,
                    max_allowed=max(0.0, yearly_remaining),
                    message=(
                        f"Yearly limit exceeded: current {context.current_yearly_total}h + "
                        f"requested {context.requested_hours}h = {yearly_after}h > "
                        f"{context.max_yearly}h. "
                        f"Remaining yearly hours: {max(0.0, yearly_remaining)}h."
                    ),
                )
            )

        # If any limit is violated, reject
        if rejections:
            result.approved = False
            result.rejections = rejections
            result.triggered_actions = [
                {
                    "type": "restrict",
                    "parameters": {
                        "reason": "overtime_limit_exceeded",
                        "violations": [r.limit_type for r in rejections],
                    },
                }
            ]
            return result

        # Step 4: All limits pass — calculate pay and approve
        multiplier = self._select_multiplier(context.day_types, context.multipliers)
        hourly_rate = self._calculate_hourly_rate(
            context.monthly_salary,
            context.standard_days,
            context.standard_hours,
        )
        calculated_pay = hourly_rate * context.requested_hours * multiplier

        result.approved = True
        result.calculated_pay = calculated_pay
        result.applied_multiplier = multiplier
        result.hourly_rate = hourly_rate
        result.updated_monthly_total = context.current_monthly_total + context.requested_hours
        result.updated_yearly_total = context.current_yearly_total + context.requested_hours
        result.triggered_actions = [
            {
                "type": "calculate",
                "parameters": {
                    "output_field": "overtime_pay",
                    "value": calculated_pay,
                    "hourly_rate": hourly_rate,
                    "multiplier": multiplier,
                    "hours": context.requested_hours,
                },
            }
        ]

        return result

    def _select_multiplier(
        self,
        day_types: list[DayType],
        configured_multipliers: dict[DayType, float],
    ) -> float:
        """Select the highest applicable multiplier for the given day types.

        When a date qualifies as multiple day types (e.g., a rest day that
        is also a public holiday), the highest multiplier is applied per
        Article 98 / Requirement 9.6.

        For each day type, uses the tenant-configured multiplier if it meets
        or exceeds the legal minimum; otherwise falls back to the legal minimum.

        Args:
            day_types: List of day types that apply to the work date.
            configured_multipliers: Tenant-configured multipliers per day type.

        Returns:
            The highest applicable multiplier value.
        """
        if not day_types:
            # Default to weekday if no day types specified
            day_types = [DayType.WEEKDAY]

        highest = 0.0
        for day_type in day_types:
            legal_min = MINIMUM_MULTIPLIERS.get(day_type, 1.5)
            configured = configured_multipliers.get(day_type, legal_min)
            # Ensure configured multiplier meets legal minimum
            effective = max(configured, legal_min)
            if effective > highest:
                highest = effective

        return highest

    def _calculate_hourly_rate(
        self,
        monthly_salary: float,
        standard_days: float,
        standard_hours: float,
    ) -> float:
        """Calculate the hourly wage rate for overtime pay.

        Formula: monthly_salary ÷ standard_days ÷ standard_hours

        Args:
            monthly_salary: Employee's monthly salary.
            standard_days: Standard monthly working days.
            standard_hours: Standard daily working hours.

        Returns:
            The computed hourly rate. Returns 0.0 if standard_days or
            standard_hours is zero to avoid division by zero.
        """
        if standard_days <= 0 or standard_hours <= 0:
            return 0.0
        return monthly_salary / standard_days / standard_hours
