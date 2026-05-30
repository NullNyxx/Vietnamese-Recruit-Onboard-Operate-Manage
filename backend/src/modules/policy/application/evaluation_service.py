"""Evaluation service for the Policy Engine module.

Provides rule matching, condition evaluation, and action triggering
for policy evaluation requests. Loads rules from Redis cache with
PostgreSQL fallback, resolves active versions by date, and produces
deterministic evaluation results sorted by priority and rule_id.

Every evaluation is logged for audit purposes.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from src.modules.policy.domain.entities import (
    PolicyAuditLog,
    PolicyRule,
    RuleCondition,
)
from src.modules.policy.domain.enums import PolicyDomain, RuleOperator
from src.modules.policy.infrastructure.cache_client import PolicyCacheClient
from src.modules.policy.infrastructure.policy_repository import PolicyRepository
from src.modules.policy.infrastructure.version_repository import VersionRepository

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type alias for evaluation context
# ---------------------------------------------------------------------------

PolicyEvaluationContext = dict[str, Any]
"""A dict containing tenant_id, domain, event_type, and context data."""


# ---------------------------------------------------------------------------
# Result data classes
# ---------------------------------------------------------------------------


@dataclass
class RuleMatch:
    """A single matched rule with its identifier and name.

    Attributes:
        rule_id: The rule's string identifier.
        name: The human-readable rule name.
    """

    rule_id: str
    name: str


@dataclass
class RuleEvaluationDetail:
    """Pass/fail result for a single rule evaluation.

    Attributes:
        rule_id: The rule's string identifier.
        passed: Whether the rule's condition was satisfied.
        condition: The evaluated RuleCondition as a dict.
    """

    rule_id: str
    passed: bool
    condition: dict[str, Any]


@dataclass
class EvaluationResult:
    """Complete result of a policy evaluation.

    Attributes:
        matched_rules: List of rules whose conditions matched.
        evaluation_results: Pass/fail detail for every evaluated rule.
        triggered_actions: List of RuleAction dicts for matched rules.
    """

    matched_rules: list[RuleMatch] = field(default_factory=list)
    evaluation_results: list[RuleEvaluationDetail] = field(default_factory=list)
    triggered_actions: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the evaluation result to a plain dictionary."""
        return {
            "matched_rules": [{"rule_id": m.rule_id, "name": m.name} for m in self.matched_rules],
            "evaluation_results": [
                {
                    "rule_id": r.rule_id,
                    "passed": r.passed,
                    "condition": r.condition,
                }
                for r in self.evaluation_results
            ],
            "triggered_actions": self.triggered_actions,
        }


# ---------------------------------------------------------------------------
# Condition Evaluator
# ---------------------------------------------------------------------------


def evaluate_condition(
    condition: RuleCondition,
    context: dict[str, Any],
) -> bool:
    """Evaluate a single RuleCondition against context data.

    Retrieves the field value from the context and compares it
    against the condition's value using the specified operator.

    Args:
        condition: The RuleCondition to evaluate.
        context: The context data dict containing field values.

    Returns:
        True if the condition is satisfied, False otherwise.
    """
    field_value = context.get(condition.field)
    operator = condition.operator
    expected = condition.value

    try:
        if operator == RuleOperator.IS_NULL:
            return field_value is None

        if operator == RuleOperator.EQUALS:
            return bool(field_value == expected)

        if operator == RuleOperator.NOT_EQUALS:
            return bool(field_value != expected)

        if operator == RuleOperator.GREATER_THAN:
            return field_value is not None and bool(field_value > expected)

        if operator == RuleOperator.LESS_THAN:
            return field_value is not None and bool(field_value < expected)

        if operator == RuleOperator.GREATER_THAN_OR_EQUAL:
            return field_value is not None and bool(field_value >= expected)

        if operator == RuleOperator.LESS_THAN_OR_EQUAL:
            return field_value is not None and bool(field_value <= expected)

        if operator == RuleOperator.IN_LIST:
            if not isinstance(expected, list):
                return False
            return bool(field_value in expected)

        if operator == RuleOperator.NOT_IN_LIST:
            if not isinstance(expected, list):
                return True
            return bool(field_value not in expected)

        if operator == RuleOperator.BETWEEN:
            if not isinstance(expected, list) or len(expected) != 2 or field_value is None:
                return False
            return bool(expected[0] <= field_value <= expected[1])

    except (TypeError, ValueError):
        # Comparison failed due to incompatible types
        return False

    return False


# ---------------------------------------------------------------------------
# Evaluation Service
# ---------------------------------------------------------------------------


class EvaluationService:
    """Orchestrates policy rule evaluation for a given context.

    Loads rules from Redis cache (with PostgreSQL fallback), filters
    by domain and enabled status, evaluates conditions, applies
    precedence ordering, and logs every evaluation for audit.

    Args:
        policy_repository: Repository for PolicyRule queries.
        version_repository: Repository for PolicyVersion resolution.
        cache_client: Redis cache client for active policy snapshots.
    """

    def __init__(
        self,
        policy_repository: PolicyRepository,
        version_repository: VersionRepository,
        cache_client: PolicyCacheClient,
    ) -> None:
        """Initialize EvaluationService with required dependencies.

        Args:
            policy_repository: Repository for PolicyRule persistence.
            version_repository: Repository for PolicyVersion resolution.
            cache_client: Redis cache for active policy snapshots.
        """
        self._policy_repo = policy_repository
        self._version_repo = version_repository
        self._cache = cache_client

    async def evaluate(
        self,
        tenant_id: str,
        domain: PolicyDomain,
        event_type: str,
        context: dict[str, Any],
        evaluation_date: date | None = None,
        user_id: UUID | None = None,
    ) -> EvaluationResult:
        """Evaluate policy rules against the provided context.

        Execution flow:
        1. Try Redis cache for active policy snapshot
        2. On cache miss, resolve active version by evaluation date
        3. If no version found, get current rules from repository
        4. Filter rules: skip disabled, filter by domain
        5. Evaluate each rule's condition against context
        6. Sort matched rules by (priority ASC, rule_id ASC)
        7. Collect triggered actions from matched rules
        8. Log evaluation for audit

        Args:
            tenant_id: The tenant identifier.
            domain: The policy domain to evaluate.
            event_type: The type of event triggering evaluation.
            context: The evaluation context data.
            evaluation_date: The date for version resolution.
                Defaults to today if not provided.
            user_id: Optional user ID for audit logging.

        Returns:
            An EvaluationResult with matched rules, pass/fail details,
            and triggered actions.
        """
        if evaluation_date is None:
            evaluation_date = date.today()

        # Step 1-3: Load rules
        rules = await self._load_rules(tenant_id, domain, evaluation_date)

        # Step 4: Filter rules (skip disabled, filter by domain)
        active_rules = self._filter_rules(rules, domain)

        # Step 5-7: Evaluate and build result
        result = self._evaluate_rules(active_rules, context)

        # Step 8: Log evaluation for audit
        await self._log_evaluation(
            tenant_id=tenant_id,
            domain=domain,
            event_type=event_type,
            evaluation_date=evaluation_date,
            matched_count=len(result.matched_rules),
            action_count=len(result.triggered_actions),
            user_id=user_id,
        )

        return result

    # -----------------------------------------------------------------------
    # Private: Rule loading
    # -----------------------------------------------------------------------

    async def _load_rules(
        self,
        tenant_id: str,
        domain: PolicyDomain,
        evaluation_date: date,
    ) -> list[PolicyRule | dict[str, Any]]:
        """Load rules from cache or database with version resolution.

        Priority:
        1. Redis cache (active policy snapshot)
        2. Active version by evaluation date (from VersionRepository)
        3. Current rules from PolicyRepository

        Args:
            tenant_id: The tenant identifier.
            domain: The policy domain filter.
            evaluation_date: The date for version resolution.

        Returns:
            A list of rules (either PolicyRule entities or dicts from
            a version snapshot).
        """
        # Try cache first
        cached_snapshot = await self._cache.get_active_policy(tenant_id)
        if cached_snapshot is not None:
            rules_data: list[dict[str, Any]] = cached_snapshot.get("rules", [])
            return rules_data  # type: ignore[return-value]

        # Try active version by date
        active_version = await self._version_repo.get_active_version(tenant_id, evaluation_date)
        if active_version is not None:
            # Cache the snapshot for future requests
            await self._cache.set_active_policy(tenant_id, active_version.snapshot)
            version_rules: list[dict[str, Any]] = active_version.snapshot.get("rules", [])
            return version_rules  # type: ignore[return-value]

        # Fallback: get current rules from repository
        rules = await self._policy_repo.get_rules_by_tenant(tenant_id, domain)
        return list(rules)

    # -----------------------------------------------------------------------
    # Private: Rule filtering
    # -----------------------------------------------------------------------

    def _filter_rules(
        self,
        rules: list[PolicyRule | dict[str, Any]],
        domain: PolicyDomain,
    ) -> list[PolicyRule | dict[str, Any]]:
        """Filter rules by enabled status and domain.

        Skips disabled rules and filters to the requested domain.

        Args:
            rules: The raw list of rules (entities or dicts).
            domain: The policy domain to filter by.

        Returns:
            A filtered list of active rules for the domain.
        """
        filtered: list[PolicyRule | dict[str, Any]] = []
        domain_value = domain.value if isinstance(domain, PolicyDomain) else domain

        for rule in rules:
            if isinstance(rule, dict):
                # Rule from snapshot/cache
                if not rule.get("enabled", True):
                    continue
                rule_domain = rule.get("domain", "")
                if rule_domain != domain_value:
                    continue
                filtered.append(rule)
            else:
                # PolicyRule entity
                if not rule.enabled:
                    continue
                rule_domain_val = (
                    rule.domain.value if isinstance(rule.domain, PolicyDomain) else rule.domain
                )
                if rule_domain_val != domain_value:
                    continue
                filtered.append(rule)

        return filtered

    # -----------------------------------------------------------------------
    # Private: Rule evaluation
    # -----------------------------------------------------------------------

    def _evaluate_rules(
        self,
        rules: list[PolicyRule | dict[str, Any]],
        context: dict[str, Any],
    ) -> EvaluationResult:
        """Evaluate all rules against the context and build the result.

        Evaluates each rule's condition, collects matches, sorts by
        (priority ASC, rule_id ASC), and gathers triggered actions.

        Args:
            rules: The filtered list of active rules.
            context: The evaluation context data.

        Returns:
            An EvaluationResult with matched rules, evaluation details,
            and triggered actions.
        """
        matched: list[tuple[int, str, str, dict[str, Any]]] = []
        evaluation_results: list[RuleEvaluationDetail] = []

        for rule in rules:
            rule_id, name, priority, condition_dict, action_dict = self._extract_rule_fields(rule)

            # Parse condition
            condition = self._parse_condition(condition_dict)
            if condition is None:
                # Invalid condition structure, skip
                evaluation_results.append(
                    RuleEvaluationDetail(
                        rule_id=rule_id,
                        passed=False,
                        condition=condition_dict,
                    )
                )
                continue

            # Evaluate condition
            passed = evaluate_condition(condition, context)

            evaluation_results.append(
                RuleEvaluationDetail(
                    rule_id=rule_id,
                    passed=passed,
                    condition=condition_dict,
                )
            )

            if passed:
                matched.append((priority, rule_id, name, action_dict))

        # Sort matched rules by (priority ASC, rule_id ASC)
        matched.sort(key=lambda x: (x[0], x[1]))

        # Build result
        result = EvaluationResult()
        result.evaluation_results = evaluation_results

        for priority, rule_id, name, action_dict in matched:
            result.matched_rules.append(RuleMatch(rule_id=rule_id, name=name))
            result.triggered_actions.append(action_dict)

        return result

    def _extract_rule_fields(
        self,
        rule: PolicyRule | dict[str, Any],
    ) -> tuple[str, str, int, dict[str, Any], dict[str, Any]]:
        """Extract common fields from a rule (entity or dict).

        Args:
            rule: A PolicyRule entity or a dict from a snapshot.

        Returns:
            A tuple of (rule_id, name, priority, condition_dict, action_dict).
        """
        if isinstance(rule, dict):
            return (
                rule.get("rule_id", ""),
                rule.get("name", ""),
                rule.get("priority", 999),
                rule.get("rule_condition", {}),
                rule.get("rule_action", {}),
            )
        else:
            return (
                rule.rule_id,
                rule.name,
                rule.priority,
                rule.rule_condition,
                rule.rule_action,
            )

    def _parse_condition(
        self,
        condition_dict: dict[str, Any],
    ) -> RuleCondition | None:
        """Parse a condition dict into a RuleCondition value object.

        Args:
            condition_dict: The raw condition dictionary.

        Returns:
            A RuleCondition instance, or None if parsing fails.
        """
        try:
            field_name = condition_dict.get("field")
            operator_str = condition_dict.get("operator")
            value = condition_dict.get("value")

            if field_name is None or operator_str is None:
                return None

            operator = RuleOperator(operator_str)
            return RuleCondition(field=field_name, operator=operator, value=value)
        except (ValueError, KeyError):
            return None

    # -----------------------------------------------------------------------
    # Private: Audit logging
    # -----------------------------------------------------------------------

    async def _log_evaluation(
        self,
        tenant_id: str,
        domain: PolicyDomain,
        event_type: str,
        evaluation_date: date,
        matched_count: int,
        action_count: int,
        user_id: UUID | None = None,
    ) -> None:
        """Create an audit log entry for the evaluation.

        Args:
            tenant_id: The tenant identifier.
            domain: The policy domain evaluated.
            event_type: The event type that triggered evaluation.
            evaluation_date: The date used for version resolution.
            matched_count: Number of rules that matched.
            action_count: Number of actions triggered.
            user_id: Optional user ID for the audit entry.
        """
        from uuid import uuid4

        audit_log = PolicyAuditLog(
            tenant_id=tenant_id,
            user_id=user_id or uuid4(),
            action_type="policy_evaluation",
            details={
                "domain": domain.value if isinstance(domain, PolicyDomain) else domain,
                "event_type": event_type,
                "evaluation_date": evaluation_date.isoformat(),
                "matched_rules_count": matched_count,
                "triggered_actions_count": action_count,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

        try:
            self._policy_repo.session.add(audit_log)
            await self._policy_repo.session.flush()
        except Exception as exc:
            logger.warning(
                "Failed to log evaluation audit for tenant '%s': %s",
                tenant_id,
                exc,
            )
