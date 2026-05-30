"""Unit tests for EvaluationService.

Tests rule loading (cache/version/fallback), condition evaluation for
all supported operators, rule filtering, precedence sorting, and
audit logging.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.modules.policy.application.evaluation_service import (
    EvaluationResult,
    EvaluationService,
    RuleCondition,
    RuleEvaluationDetail,
    RuleMatch,
    evaluate_condition,
)
from src.modules.policy.domain.enums import PolicyDomain, RuleOperator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service() -> tuple[EvaluationService, AsyncMock, AsyncMock, AsyncMock]:
    """Create an EvaluationService with mocked dependencies."""
    policy_repo = AsyncMock()
    session_mock = MagicMock()
    session_mock.flush = AsyncMock()
    policy_repo.session = session_mock

    version_repo = AsyncMock()
    cache_client = AsyncMock()

    service = EvaluationService(
        policy_repository=policy_repo,
        version_repository=version_repo,
        cache_client=cache_client,
    )
    return service, policy_repo, version_repo, cache_client


def _make_rule_dict(
    rule_id: str = "ATT-001",
    domain: str = "attendance",
    name: str = "Late Threshold",
    priority: int = 100,
    enabled: bool = True,
    field: str = "late_minutes",
    operator: str = "greater_than",
    value: int | list | None = 15,
    action_type: str = "flag",
    action_params: dict | None = None,
) -> dict:
    """Create a rule dict as it would appear in a snapshot."""
    return {
        "rule_id": rule_id,
        "domain": domain,
        "name": name,
        "priority": priority,
        "enabled": enabled,
        "rule_condition": {"field": field, "operator": operator, "value": value},
        "rule_action": {
            "type": action_type,
            "parameters": action_params or {"status": "late"},
        },
        "is_custom": False,
        "template_rule_id": None,
        "id": str(uuid4()),
    }


# ---------------------------------------------------------------------------
# Tests: evaluate_condition function
# ---------------------------------------------------------------------------


class TestEvaluateCondition:
    """Tests for the evaluate_condition function."""

    def test_equals_true(self) -> None:
        condition = RuleCondition(field="status", operator=RuleOperator.EQUALS, value="active")
        assert evaluate_condition(condition, {"status": "active"}) is True

    def test_equals_false(self) -> None:
        condition = RuleCondition(field="status", operator=RuleOperator.EQUALS, value="active")
        assert evaluate_condition(condition, {"status": "inactive"}) is False

    def test_not_equals_true(self) -> None:
        condition = RuleCondition(field="status", operator=RuleOperator.NOT_EQUALS, value="active")
        assert evaluate_condition(condition, {"status": "inactive"}) is True

    def test_not_equals_false(self) -> None:
        condition = RuleCondition(field="status", operator=RuleOperator.NOT_EQUALS, value="active")
        assert evaluate_condition(condition, {"status": "active"}) is False

    def test_greater_than_true(self) -> None:
        condition = RuleCondition(field="minutes", operator=RuleOperator.GREATER_THAN, value=15)
        assert evaluate_condition(condition, {"minutes": 20}) is True

    def test_greater_than_false(self) -> None:
        condition = RuleCondition(field="minutes", operator=RuleOperator.GREATER_THAN, value=15)
        assert evaluate_condition(condition, {"minutes": 10}) is False

    def test_greater_than_none_field(self) -> None:
        condition = RuleCondition(field="minutes", operator=RuleOperator.GREATER_THAN, value=15)
        assert evaluate_condition(condition, {"minutes": None}) is False

    def test_less_than_true(self) -> None:
        condition = RuleCondition(field="hours", operator=RuleOperator.LESS_THAN, value=8)
        assert evaluate_condition(condition, {"hours": 5}) is True

    def test_less_than_false(self) -> None:
        condition = RuleCondition(field="hours", operator=RuleOperator.LESS_THAN, value=8)
        assert evaluate_condition(condition, {"hours": 10}) is False

    def test_greater_than_or_equal_true(self) -> None:
        condition = RuleCondition(
            field="score", operator=RuleOperator.GREATER_THAN_OR_EQUAL, value=80
        )
        assert evaluate_condition(condition, {"score": 80}) is True

    def test_greater_than_or_equal_false(self) -> None:
        condition = RuleCondition(
            field="score", operator=RuleOperator.GREATER_THAN_OR_EQUAL, value=80
        )
        assert evaluate_condition(condition, {"score": 79}) is False

    def test_less_than_or_equal_true(self) -> None:
        condition = RuleCondition(field="days", operator=RuleOperator.LESS_THAN_OR_EQUAL, value=30)
        assert evaluate_condition(condition, {"days": 30}) is True

    def test_less_than_or_equal_false(self) -> None:
        condition = RuleCondition(field="days", operator=RuleOperator.LESS_THAN_OR_EQUAL, value=30)
        assert evaluate_condition(condition, {"days": 31}) is False

    def test_in_list_true(self) -> None:
        condition = RuleCondition(
            field="dept", operator=RuleOperator.IN_LIST, value=["HR", "IT", "Finance"]
        )
        assert evaluate_condition(condition, {"dept": "HR"}) is True

    def test_in_list_false(self) -> None:
        condition = RuleCondition(
            field="dept", operator=RuleOperator.IN_LIST, value=["HR", "IT", "Finance"]
        )
        assert evaluate_condition(condition, {"dept": "Sales"}) is False

    def test_not_in_list_true(self) -> None:
        condition = RuleCondition(
            field="dept", operator=RuleOperator.NOT_IN_LIST, value=["HR", "IT"]
        )
        assert evaluate_condition(condition, {"dept": "Sales"}) is True

    def test_not_in_list_false(self) -> None:
        condition = RuleCondition(
            field="dept", operator=RuleOperator.NOT_IN_LIST, value=["HR", "IT"]
        )
        assert evaluate_condition(condition, {"dept": "HR"}) is False

    def test_between_true(self) -> None:
        condition = RuleCondition(field="age", operator=RuleOperator.BETWEEN, value=[18, 65])
        assert evaluate_condition(condition, {"age": 30}) is True

    def test_between_false(self) -> None:
        condition = RuleCondition(field="age", operator=RuleOperator.BETWEEN, value=[18, 65])
        assert evaluate_condition(condition, {"age": 70}) is False

    def test_between_boundary_inclusive(self) -> None:
        condition = RuleCondition(field="age", operator=RuleOperator.BETWEEN, value=[18, 65])
        assert evaluate_condition(condition, {"age": 18}) is True
        assert evaluate_condition(condition, {"age": 65}) is True

    def test_is_null_true(self) -> None:
        condition = RuleCondition(field="manager", operator=RuleOperator.IS_NULL, value=None)
        assert evaluate_condition(condition, {"manager": None}) is True

    def test_is_null_false(self) -> None:
        condition = RuleCondition(field="manager", operator=RuleOperator.IS_NULL, value=None)
        assert evaluate_condition(condition, {"manager": "John"}) is False

    def test_is_null_missing_field(self) -> None:
        condition = RuleCondition(field="manager", operator=RuleOperator.IS_NULL, value=None)
        assert evaluate_condition(condition, {}) is True

    def test_incompatible_types_returns_false(self) -> None:
        condition = RuleCondition(field="value", operator=RuleOperator.GREATER_THAN, value=10)
        assert evaluate_condition(condition, {"value": "not_a_number"}) is False

    def test_between_invalid_value_returns_false(self) -> None:
        condition = RuleCondition(field="age", operator=RuleOperator.BETWEEN, value="not_a_list")
        assert evaluate_condition(condition, {"age": 30}) is False

    def test_in_list_non_list_value_returns_false(self) -> None:
        condition = RuleCondition(field="dept", operator=RuleOperator.IN_LIST, value="not_a_list")
        assert evaluate_condition(condition, {"dept": "HR"}) is False


# ---------------------------------------------------------------------------
# Tests: EvaluationService.evaluate
# ---------------------------------------------------------------------------


class TestEvaluationServiceEvaluate:
    """Tests for EvaluationService.evaluate method."""

    async def test_loads_from_cache_when_available(self) -> None:
        """Uses cached snapshot when Redis returns data."""
        service, policy_repo, version_repo, cache = _make_service()
        rule = _make_rule_dict(field="late_minutes", operator="greater_than", value=15)
        cache.get_active_policy.return_value = {"rules": [rule]}

        result = await service.evaluate(
            tenant_id="tenant-001",
            domain=PolicyDomain.ATTENDANCE,
            event_type="check_in",
            context={"late_minutes": 20},
        )

        assert len(result.matched_rules) == 1
        assert result.matched_rules[0].rule_id == "ATT-001"
        version_repo.get_active_version.assert_not_called()
        policy_repo.get_rules_by_tenant.assert_not_called()

    async def test_falls_back_to_version_on_cache_miss(self) -> None:
        """Falls back to version repository when cache returns None."""
        service, policy_repo, version_repo, cache = _make_service()
        cache.get_active_policy.return_value = None
        rule = _make_rule_dict(field="late_minutes", operator="greater_than", value=15)
        version_mock = MagicMock()
        version_mock.snapshot = {"rules": [rule]}
        version_repo.get_active_version.return_value = version_mock

        result = await service.evaluate(
            tenant_id="tenant-001",
            domain=PolicyDomain.ATTENDANCE,
            event_type="check_in",
            context={"late_minutes": 20},
        )

        assert len(result.matched_rules) == 1
        cache.set_active_policy.assert_called_once()

    async def test_falls_back_to_repository_when_no_version(self) -> None:
        """Falls back to PolicyRepository when no version exists."""
        service, policy_repo, version_repo, cache = _make_service()
        cache.get_active_policy.return_value = None
        version_repo.get_active_version.return_value = None
        policy_repo.get_rules_by_tenant.return_value = []

        result = await service.evaluate(
            tenant_id="tenant-001",
            domain=PolicyDomain.ATTENDANCE,
            event_type="check_in",
            context={"late_minutes": 20},
        )

        assert len(result.matched_rules) == 0
        policy_repo.get_rules_by_tenant.assert_called_once()

    async def test_filters_disabled_rules(self) -> None:
        """Disabled rules are skipped during evaluation."""
        service, _, _, cache = _make_service()
        enabled_rule = _make_rule_dict(
            rule_id="ATT-001", enabled=True, field="x", operator="equals", value=1
        )
        disabled_rule = _make_rule_dict(
            rule_id="ATT-002", enabled=False, field="x", operator="equals", value=1
        )
        cache.get_active_policy.return_value = {"rules": [enabled_rule, disabled_rule]}

        result = await service.evaluate(
            tenant_id="tenant-001",
            domain=PolicyDomain.ATTENDANCE,
            event_type="check_in",
            context={"x": 1},
        )

        matched_ids = [m.rule_id for m in result.matched_rules]
        assert "ATT-001" in matched_ids
        assert "ATT-002" not in matched_ids

    async def test_filters_by_domain(self) -> None:
        """Only rules matching the requested domain are evaluated."""
        service, _, _, cache = _make_service()
        attendance_rule = _make_rule_dict(
            rule_id="ATT-001", domain="attendance", field="x", operator="equals", value=1
        )
        leave_rule = _make_rule_dict(
            rule_id="LV-001", domain="leave", field="x", operator="equals", value=1
        )
        cache.get_active_policy.return_value = {"rules": [attendance_rule, leave_rule]}

        result = await service.evaluate(
            tenant_id="tenant-001",
            domain=PolicyDomain.ATTENDANCE,
            event_type="check_in",
            context={"x": 1},
        )

        matched_ids = [m.rule_id for m in result.matched_rules]
        assert "ATT-001" in matched_ids
        assert "LV-001" not in matched_ids

    async def test_sorts_by_priority_then_rule_id(self) -> None:
        """Matched rules are sorted by priority ASC, then rule_id ASC."""
        service, _, _, cache = _make_service()
        rule_c = _make_rule_dict(
            rule_id="C-001", priority=200, field="x", operator="equals", value=1
        )
        rule_a = _make_rule_dict(
            rule_id="A-001", priority=100, field="x", operator="equals", value=1
        )
        rule_b = _make_rule_dict(
            rule_id="B-001", priority=100, field="x", operator="equals", value=1
        )
        cache.get_active_policy.return_value = {"rules": [rule_c, rule_a, rule_b]}

        result = await service.evaluate(
            tenant_id="tenant-001",
            domain=PolicyDomain.ATTENDANCE,
            event_type="check_in",
            context={"x": 1},
        )

        assert result.matched_rules[0].rule_id == "A-001"
        assert result.matched_rules[1].rule_id == "B-001"
        assert result.matched_rules[2].rule_id == "C-001"

    async def test_returns_triggered_actions_for_matched_rules(self) -> None:
        """Triggered actions are collected from matched rules."""
        service, _, _, cache = _make_service()
        rule = _make_rule_dict(
            field="late_minutes",
            operator="greater_than",
            value=15,
            action_type="flag",
            action_params={"status": "late"},
        )
        cache.get_active_policy.return_value = {"rules": [rule]}

        result = await service.evaluate(
            tenant_id="tenant-001",
            domain=PolicyDomain.ATTENDANCE,
            event_type="check_in",
            context={"late_minutes": 20},
        )

        assert len(result.triggered_actions) == 1
        assert result.triggered_actions[0]["type"] == "flag"
        assert result.triggered_actions[0]["parameters"]["status"] == "late"

    async def test_no_match_returns_empty_result(self) -> None:
        """When no rules match, returns empty matched_rules and actions."""
        service, _, _, cache = _make_service()
        rule = _make_rule_dict(field="late_minutes", operator="greater_than", value=15)
        cache.get_active_policy.return_value = {"rules": [rule]}

        result = await service.evaluate(
            tenant_id="tenant-001",
            domain=PolicyDomain.ATTENDANCE,
            event_type="check_in",
            context={"late_minutes": 5},  # Below threshold
        )

        assert len(result.matched_rules) == 0
        assert len(result.triggered_actions) == 0

    async def test_evaluation_results_include_all_rules(self) -> None:
        """Evaluation results include pass/fail for every evaluated rule."""
        service, _, _, cache = _make_service()
        rule_pass = _make_rule_dict(rule_id="ATT-001", field="x", operator="equals", value=1)
        rule_fail = _make_rule_dict(rule_id="ATT-002", field="x", operator="equals", value=99)
        cache.get_active_policy.return_value = {"rules": [rule_pass, rule_fail]}

        result = await service.evaluate(
            tenant_id="tenant-001",
            domain=PolicyDomain.ATTENDANCE,
            event_type="check_in",
            context={"x": 1},
        )

        assert len(result.evaluation_results) == 2
        results_by_id = {r.rule_id: r for r in result.evaluation_results}
        assert results_by_id["ATT-001"].passed is True
        assert results_by_id["ATT-002"].passed is False

    async def test_creates_audit_log(self) -> None:
        """Evaluation creates an audit log entry."""
        service, policy_repo, _, cache = _make_service()
        cache.get_active_policy.return_value = {"rules": []}

        await service.evaluate(
            tenant_id="tenant-001",
            domain=PolicyDomain.ATTENDANCE,
            event_type="check_in",
            context={},
        )

        policy_repo.session.add.assert_called_once()
        audit_log = policy_repo.session.add.call_args[0][0]
        assert audit_log.tenant_id == "tenant-001"
        assert audit_log.action_type == "policy_evaluation"
        assert audit_log.details["domain"] == "attendance"
        assert audit_log.details["event_type"] == "check_in"


# ---------------------------------------------------------------------------
# Tests: EvaluationResult.to_dict
# ---------------------------------------------------------------------------


class TestEvaluationResultToDict:
    """Tests for EvaluationResult.to_dict serialization."""

    def test_serializes_correctly(self) -> None:
        result = EvaluationResult(
            matched_rules=[RuleMatch(rule_id="ATT-001", name="Late")],
            evaluation_results=[
                RuleEvaluationDetail(
                    rule_id="ATT-001",
                    passed=True,
                    condition={"field": "x", "operator": "equals", "value": 1},
                )
            ],
            triggered_actions=[{"type": "flag", "parameters": {"status": "late"}}],
        )

        d = result.to_dict()

        assert len(d["matched_rules"]) == 1
        assert d["matched_rules"][0]["rule_id"] == "ATT-001"
        assert len(d["evaluation_results"]) == 1
        assert d["evaluation_results"][0]["passed"] is True
        assert len(d["triggered_actions"]) == 1
