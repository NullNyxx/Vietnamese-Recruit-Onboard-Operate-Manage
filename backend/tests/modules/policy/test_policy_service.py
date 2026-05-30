"""Tests for PolicyRule validation service."""

import pytest

from src.modules.policy.application.policy_service import validate_policy_rule
from src.modules.policy.domain.exceptions import PolicyValidationError


def _valid_rule_data() -> dict:
    """Return a minimal valid PolicyRule dict."""
    return {
        "rule_id": "attendance-late-threshold",
        "domain": "attendance",
        "name": "Late Threshold Rule",
        "description": "Flags employees arriving more than 15 minutes late.",
        "rule_condition": {
            "field": "minutes_late",
            "operator": "greater_than",
            "value": 15,
        },
        "rule_action": {
            "type": "flag",
            "parameters": {"status": "late"},
        },
        "priority": 100,
        "enabled": True,
    }


class TestValidateValidRule:
    """Verify that valid rule definitions pass without error."""

    def test_valid_rule_passes(self) -> None:
        data = _valid_rule_data()
        # Should not raise
        validate_policy_rule(data)

    def test_valid_rule_with_all_operators(self) -> None:
        operators = [
            "equals",
            "not_equals",
            "greater_than",
            "less_than",
            "greater_than_or_equal",
            "less_than_or_equal",
            "in_list",
            "not_in_list",
            "between",
            "is_null",
        ]
        for op in operators:
            data = _valid_rule_data()
            data["rule_condition"]["operator"] = op
            validate_policy_rule(data)

    def test_valid_rule_with_all_action_types(self) -> None:
        action_types = ["flag", "notify", "calculate", "restrict", "escalate"]
        for at in action_types:
            data = _valid_rule_data()
            data["rule_action"]["type"] = at
            validate_policy_rule(data)

    def test_valid_rule_with_all_domains(self) -> None:
        domains = ["attendance", "leave", "overtime", "disciplinary"]
        for domain in domains:
            data = _valid_rule_data()
            data["domain"] = domain
            validate_policy_rule(data)

    def test_priority_boundary_min(self) -> None:
        data = _valid_rule_data()
        data["priority"] = 1
        validate_policy_rule(data)

    def test_priority_boundary_max(self) -> None:
        data = _valid_rule_data()
        data["priority"] = 1000
        validate_policy_rule(data)

    def test_rule_id_at_max_length(self) -> None:
        data = _valid_rule_data()
        data["rule_id"] = "a" * 64
        validate_policy_rule(data)

    def test_name_at_max_length(self) -> None:
        data = _valid_rule_data()
        data["name"] = "x" * 128
        validate_policy_rule(data)

    def test_description_at_max_length(self) -> None:
        data = _valid_rule_data()
        data["description"] = "d" * 512
        validate_policy_rule(data)


class TestValidateMissingFields:
    """Verify that missing required fields produce errors."""

    def test_empty_dict_reports_all_missing(self) -> None:
        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule({})

        error = exc_info.value
        field_names = [e["field"] for e in error.fields]
        assert "rule_id" in field_names
        assert "domain" in field_names
        assert "name" in field_names
        assert "description" in field_names
        assert "rule_condition" in field_names
        assert "rule_action" in field_names
        assert "priority" in field_names
        assert "enabled" in field_names

    def test_missing_single_field(self) -> None:
        data = _valid_rule_data()
        del data["rule_id"]

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        error = exc_info.value
        assert len(error.fields) == 1
        assert error.fields[0]["field"] == "rule_id"


class TestValidatePriority:
    """Verify priority range validation."""

    def test_priority_zero_rejected(self) -> None:
        data = _valid_rule_data()
        data["priority"] = 0

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        error = exc_info.value
        assert any(e["field"] == "priority" for e in error.fields)

    def test_priority_negative_rejected(self) -> None:
        data = _valid_rule_data()
        data["priority"] = -5

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        error = exc_info.value
        assert any(e["field"] == "priority" for e in error.fields)

    def test_priority_above_max_rejected(self) -> None:
        data = _valid_rule_data()
        data["priority"] = 1001

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        error = exc_info.value
        fields = [e for e in error.fields if e["field"] == "priority"]
        assert len(fields) == 1
        assert fields[0]["value"] == 1001

    def test_priority_not_integer_rejected(self) -> None:
        data = _valid_rule_data()
        data["priority"] = 3.14

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        assert any(e["field"] == "priority" for e in exc_info.value.fields)

    def test_priority_boolean_rejected(self) -> None:
        data = _valid_rule_data()
        data["priority"] = True

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        assert any(e["field"] == "priority" for e in exc_info.value.fields)


class TestValidateFieldLengths:
    """Verify field length constraints."""

    def test_rule_id_exceeds_max(self) -> None:
        data = _valid_rule_data()
        data["rule_id"] = "x" * 65

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        assert any(e["field"] == "rule_id" for e in exc_info.value.fields)

    def test_name_exceeds_max(self) -> None:
        data = _valid_rule_data()
        data["name"] = "n" * 129

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        assert any(e["field"] == "name" for e in exc_info.value.fields)

    def test_description_exceeds_max(self) -> None:
        data = _valid_rule_data()
        data["description"] = "d" * 513

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        assert any(e["field"] == "description" for e in exc_info.value.fields)

    def test_empty_rule_id_rejected(self) -> None:
        data = _valid_rule_data()
        data["rule_id"] = ""

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        assert any(e["field"] == "rule_id" for e in exc_info.value.fields)

    def test_empty_name_rejected(self) -> None:
        data = _valid_rule_data()
        data["name"] = ""

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        assert any(e["field"] == "name" for e in exc_info.value.fields)


class TestValidateOperatorAndActionType:
    """Verify unsupported operators and action types are rejected."""

    def test_unsupported_operator_rejected(self) -> None:
        data = _valid_rule_data()
        data["rule_condition"]["operator"] = "contains"

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        fields = exc_info.value.fields
        assert any(e["field"] == "rule_condition.operator" for e in fields)

    def test_unsupported_action_type_rejected(self) -> None:
        data = _valid_rule_data()
        data["rule_action"]["type"] = "terminate"

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        fields = exc_info.value.fields
        assert any(e["field"] == "rule_action.type" for e in fields)

    def test_operator_wrong_type_rejected(self) -> None:
        data = _valid_rule_data()
        data["rule_condition"]["operator"] = 123

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        assert any(e["field"] == "rule_condition.operator" for e in exc_info.value.fields)

    def test_action_type_wrong_type_rejected(self) -> None:
        data = _valid_rule_data()
        data["rule_action"]["type"] = 42

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        assert any(e["field"] == "rule_action.type" for e in exc_info.value.fields)


class TestValidateRuleConditionStructure:
    """Verify rule_condition sub-object validation."""

    def test_missing_condition_field(self) -> None:
        data = _valid_rule_data()
        del data["rule_condition"]["field"]

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        assert any(e["field"] == "rule_condition.field" for e in exc_info.value.fields)

    def test_missing_condition_operator(self) -> None:
        data = _valid_rule_data()
        del data["rule_condition"]["operator"]

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        assert any(e["field"] == "rule_condition.operator" for e in exc_info.value.fields)

    def test_missing_condition_value(self) -> None:
        data = _valid_rule_data()
        del data["rule_condition"]["value"]

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        assert any(e["field"] == "rule_condition.value" for e in exc_info.value.fields)

    def test_condition_not_dict_rejected(self) -> None:
        data = _valid_rule_data()
        data["rule_condition"] = "not a dict"

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        assert any(e["field"] == "rule_condition" for e in exc_info.value.fields)

    def test_condition_field_empty_string_rejected(self) -> None:
        data = _valid_rule_data()
        data["rule_condition"]["field"] = ""

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        assert any(e["field"] == "rule_condition.field" for e in exc_info.value.fields)


class TestValidateRuleActionStructure:
    """Verify rule_action sub-object validation."""

    def test_missing_action_type(self) -> None:
        data = _valid_rule_data()
        del data["rule_action"]["type"]

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        assert any(e["field"] == "rule_action.type" for e in exc_info.value.fields)

    def test_missing_action_parameters(self) -> None:
        data = _valid_rule_data()
        del data["rule_action"]["parameters"]

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        assert any(e["field"] == "rule_action.parameters" for e in exc_info.value.fields)

    def test_action_not_dict_rejected(self) -> None:
        data = _valid_rule_data()
        data["rule_action"] = [1, 2, 3]

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        assert any(e["field"] == "rule_action" for e in exc_info.value.fields)

    def test_parameters_not_dict_rejected(self) -> None:
        data = _valid_rule_data()
        data["rule_action"]["parameters"] = "not a dict"

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        assert any(e["field"] == "rule_action.parameters" for e in exc_info.value.fields)


class TestValidateCollectsAllErrors:
    """Verify that validation collects ALL errors before raising."""

    def test_multiple_errors_collected(self) -> None:
        data = {
            "rule_id": "x" * 65,  # too long
            "domain": "invalid_domain",
            "name": "",  # empty
            "description": "ok",
            "rule_condition": {"field": "", "operator": "bad_op"},
            "rule_action": {"type": "bad_type"},
            "priority": 9999,
            "enabled": "not_bool",
        }

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        error = exc_info.value
        # Should have multiple errors, not just the first one
        assert len(error.fields) >= 5

    def test_error_includes_field_and_reason(self) -> None:
        data = _valid_rule_data()
        data["priority"] = 1500

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        error_entry = exc_info.value.fields[0]
        assert "field" in error_entry
        assert "reason" in error_entry

    def test_error_includes_value_when_present(self) -> None:
        data = _valid_rule_data()
        data["priority"] = 1500

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        error_entry = next(e for e in exc_info.value.fields if e["field"] == "priority")
        assert error_entry["value"] == 1500


class TestValidateDomainField:
    """Verify domain field validation."""

    def test_unsupported_domain_rejected(self) -> None:
        data = _valid_rule_data()
        data["domain"] = "payroll"

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        assert any(e["field"] == "domain" for e in exc_info.value.fields)

    def test_domain_wrong_type_rejected(self) -> None:
        data = _valid_rule_data()
        data["domain"] = 123

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        assert any(e["field"] == "domain" for e in exc_info.value.fields)


class TestValidateEnabledField:
    """Verify enabled field validation."""

    def test_enabled_string_rejected(self) -> None:
        data = _valid_rule_data()
        data["enabled"] = "true"

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        assert any(e["field"] == "enabled" for e in exc_info.value.fields)

    def test_enabled_integer_rejected(self) -> None:
        data = _valid_rule_data()
        data["enabled"] = 1

        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_rule(data)

        assert any(e["field"] == "enabled" for e in exc_info.value.fields)
