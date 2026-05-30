# Feature: company-policy-engine, Property 14: PolicyRule Structure Completeness
# Feature: company-policy-engine, Property 16: Invalid Rule Rejection
"""Property-based tests for PolicyRule validation properties.

Property 14: For any valid PolicyRule object, it SHALL contain all required fields
(rule_id, domain, name, description, rule_condition, rule_action, priority, enabled)
with correct types, and the rule_condition SHALL contain (field, operator, value),
and the rule_action SHALL contain (type, parameters).
**Validates: Requirements 5.1, 5.2**

Property 16: For any PolicyRule definition that is missing a required field,
contains an unsupported operator value, or contains an unsupported action type,
validation SHALL fail and return an error identifying the invalid field and reason.
**Validates: Requirements 5.5, 10.3, 11.8**
"""

import string

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.modules.policy.application.policy_service import validate_policy_rule
from src.modules.policy.domain.enums import ActionType, PolicyDomain, RuleOperator
from src.modules.policy.domain.exceptions import PolicyValidationError

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_OPERATORS: list[str] = [op.value for op in RuleOperator]
SUPPORTED_ACTION_TYPES: list[str] = [at.value for at in ActionType]
SUPPORTED_DOMAINS: list[str] = [d.value for d in PolicyDomain]

REQUIRED_TOP_LEVEL_FIELDS: list[str] = [
    "rule_id",
    "domain",
    "name",
    "description",
    "rule_condition",
    "rule_action",
    "priority",
    "enabled",
]

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------


@st.composite
def valid_rule_data(draw: st.DrawFn) -> dict:
    """Generate a valid PolicyRule dict that passes validation."""
    rule_id = draw(st.text(alphabet=string.ascii_lowercase + string.digits + "-_", min_size=1, max_size=64))
    domain = draw(st.sampled_from(SUPPORTED_DOMAINS))
    name = draw(st.text(min_size=1, max_size=128).filter(lambda s: len(s.strip()) > 0))
    description = draw(st.text(min_size=0, max_size=512))
    operator = draw(st.sampled_from(SUPPORTED_OPERATORS))
    action_type = draw(st.sampled_from(SUPPORTED_ACTION_TYPES))
    priority = draw(st.integers(min_value=1, max_value=1000))
    field_name = draw(
        st.text(alphabet=string.ascii_lowercase + "_", min_size=1, max_size=32)
    )

    return {
        "rule_id": rule_id,
        "domain": domain,
        "name": name,
        "description": description,
        "rule_condition": {
            "field": field_name,
            "operator": operator,
            "value": draw(st.integers(min_value=0, max_value=1000)),
        },
        "rule_action": {
            "type": action_type,
            "parameters": {"status": "flagged"},
        },
        "priority": priority,
        "enabled": draw(st.booleans()),
    }


@st.composite
def unsupported_operator(draw: st.DrawFn) -> str:
    """Generate a string that is NOT a supported operator."""
    candidate = draw(
        st.text(alphabet=string.ascii_lowercase + "_", min_size=1, max_size=30)
    )
    if candidate in SUPPORTED_OPERATORS:
        return candidate + "_invalid"
    return candidate


@st.composite
def unsupported_action_type(draw: st.DrawFn) -> str:
    """Generate a string that is NOT a supported action type."""
    candidate = draw(
        st.text(alphabet=string.ascii_lowercase + "_", min_size=1, max_size=30)
    )
    if candidate in SUPPORTED_ACTION_TYPES:
        return candidate + "_invalid"
    return candidate


@st.composite
def invalid_priority(draw: st.DrawFn) -> int:
    """Generate a priority value outside the valid 1-1000 range."""
    return draw(
        st.one_of(
            st.integers(max_value=0),
            st.integers(min_value=1001),
        )
    )


# ---------------------------------------------------------------------------
# Property Tests
# ---------------------------------------------------------------------------


class TestProperty16InvalidRuleRejection:
    """Property 16: Invalid Rule Rejection.

    For any PolicyRule definition that is missing a required field,
    contains an unsupported operator value, or contains an unsupported
    action type, validation SHALL fail and return an error identifying
    the invalid field and reason.
    """

    @settings(max_examples=100)
    @given(data=valid_rule_data(), field_to_remove=st.sampled_from(REQUIRED_TOP_LEVEL_FIELDS))
    def test_missing_required_field_rejected(
        self, data: dict, field_to_remove: str
    ) -> None:
        """Removing any required field from a valid rule SHALL cause rejection."""
        del data[field_to_remove]

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        error = exc_info.value
        assert len(error.fields) >= 1
        # The error must identify the missing field
        error_fields = [e["field"] for e in error.fields]
        assert field_to_remove in error_fields
        # Each error entry must have a reason
        for entry in error.fields:
            assert "reason" in entry
            assert len(entry["reason"]) > 0

    @settings(max_examples=100)
    @given(data=valid_rule_data(), bad_operator=unsupported_operator())
    def test_unsupported_operator_rejected(
        self, data: dict, bad_operator: str
    ) -> None:
        """An unsupported operator value SHALL cause rejection."""
        data["rule_condition"]["operator"] = bad_operator

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        error = exc_info.value
        assert len(error.fields) >= 1
        error_fields = [e["field"] for e in error.fields]
        assert "rule_condition.operator" in error_fields
        # Error must include reason
        op_error = next(
            e for e in error.fields if e["field"] == "rule_condition.operator"
        )
        assert "reason" in op_error
        assert len(op_error["reason"]) > 0

    @settings(max_examples=100)
    @given(data=valid_rule_data(), bad_action=unsupported_action_type())
    def test_unsupported_action_type_rejected(
        self, data: dict, bad_action: str
    ) -> None:
        """An unsupported action type SHALL cause rejection."""
        data["rule_action"]["type"] = bad_action

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        error = exc_info.value
        assert len(error.fields) >= 1
        error_fields = [e["field"] for e in error.fields]
        assert "rule_action.type" in error_fields
        # Error must include reason
        action_error = next(
            e for e in error.fields if e["field"] == "rule_action.type"
        )
        assert "reason" in action_error
        assert len(action_error["reason"]) > 0

    @settings(max_examples=100)
    @given(data=valid_rule_data(), bad_priority=invalid_priority())
    def test_priority_outside_range_rejected(
        self, data: dict, bad_priority: int
    ) -> None:
        """A priority outside 1-1000 SHALL cause rejection."""
        data["priority"] = bad_priority

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        error = exc_info.value
        assert len(error.fields) >= 1
        error_fields = [e["field"] for e in error.fields]
        assert "priority" in error_fields
        # Error must include the invalid value
        priority_error = next(
            e for e in error.fields if e["field"] == "priority"
        )
        assert "reason" in priority_error
        assert priority_error["value"] == bad_priority


# ---------------------------------------------------------------------------
# Feature: company-policy-engine, Property 14: PolicyRule Structure Completeness
# ---------------------------------------------------------------------------


class TestProperty14PolicyRuleStructureCompleteness:
    """Property 14: PolicyRule Structure Completeness.

    For any valid PolicyRule object, it SHALL contain all required fields
    (rule_id, domain, name, description, rule_condition, rule_action, priority,
    enabled) with correct types, and the rule_condition SHALL contain
    (field, operator, value), and the rule_action SHALL contain (type, parameters).

    **Validates: Requirements 5.1, 5.2**
    """

    @settings(max_examples=100)
    @given(rule=valid_rule_data())
    def test_valid_rule_passes_validation(self, rule: dict) -> None:
        """Any generated valid PolicyRule SHALL pass validate_policy_rule()."""
        # Should not raise PolicyValidationError
        validate_policy_rule(rule)

    @settings(max_examples=100)
    @given(rule=valid_rule_data())
    def test_valid_rule_has_all_required_top_level_fields(self, rule: dict) -> None:
        """Any valid PolicyRule SHALL contain all required top-level fields."""
        for field in REQUIRED_TOP_LEVEL_FIELDS:
            assert field in rule, f"Missing required field: {field}"

    @settings(max_examples=100)
    @given(rule=valid_rule_data())
    def test_valid_rule_has_correct_top_level_types(self, rule: dict) -> None:
        """Any valid PolicyRule SHALL have correct types for all fields."""
        assert isinstance(rule["rule_id"], str)
        assert isinstance(rule["domain"], str)
        assert isinstance(rule["name"], str)
        assert isinstance(rule["description"], str)
        assert isinstance(rule["rule_condition"], dict)
        assert isinstance(rule["rule_action"], dict)
        assert isinstance(rule["priority"], int)
        assert isinstance(rule["enabled"], bool)

    @settings(max_examples=100)
    @given(rule=valid_rule_data())
    def test_valid_rule_condition_has_required_fields(self, rule: dict) -> None:
        """rule_condition SHALL contain (field, operator, value)."""
        condition = rule["rule_condition"]
        assert "field" in condition
        assert "operator" in condition
        assert "value" in condition

    @settings(max_examples=100)
    @given(rule=valid_rule_data())
    def test_valid_rule_action_has_required_fields(self, rule: dict) -> None:
        """rule_action SHALL contain (type, parameters)."""
        action = rule["rule_action"]
        assert "type" in action
        assert "parameters" in action

    @settings(max_examples=100)
    @given(rule=valid_rule_data())
    def test_valid_rule_condition_field_types(self, rule: dict) -> None:
        """rule_condition fields SHALL have correct types."""
        condition = rule["rule_condition"]
        assert isinstance(condition["field"], str)
        assert isinstance(condition["operator"], str)
        # value can be any type per the schema

    @settings(max_examples=100)
    @given(rule=valid_rule_data())
    def test_valid_rule_action_field_types(self, rule: dict) -> None:
        """rule_action fields SHALL have correct types."""
        action = rule["rule_action"]
        assert isinstance(action["type"], str)
        assert isinstance(action["parameters"], dict)
