"""Unit tests for the PolicyRule serializer and parser."""

import json

import pytest

from src.modules.policy.application.serializer_service import parse, serialize
from src.modules.policy.domain.entities import PolicyRule
from src.modules.policy.domain.enums import ActionType, PolicyDomain, RuleOperator
from src.modules.policy.domain.exceptions import PolicySerializationError


def _make_rule(**overrides) -> PolicyRule:
    """Create a PolicyRule with sensible defaults for testing."""
    defaults = {
        "rule_id": "attendance_late_threshold",
        "domain": PolicyDomain.ATTENDANCE,
        "name": "Late Threshold",
        "description": "Mark employee as late if check-in exceeds threshold",
        "rule_condition": {
            "field": "check_in_delay_minutes",
            "operator": RuleOperator.GREATER_THAN.value,
            "value": 15,
        },
        "rule_action": {
            "type": ActionType.FLAG.value,
            "parameters": {"status": "late"},
        },
        "priority": 100,
        "enabled": True,
        "tenant_id": "test_tenant",
        "created_by": "00000000-0000-0000-0000-000000000001",
    }
    defaults.update(overrides)
    return PolicyRule.model_validate(defaults)


class TestSerialize:
    """Tests for the serialize function."""

    def test_produces_valid_json(self) -> None:
        rule = _make_rule()
        result = serialize(rule)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_deterministic_output(self) -> None:
        rule = _make_rule()
        result1 = serialize(rule)
        result2 = serialize(rule)
        assert result1 == result2

    def test_sorted_keys(self) -> None:
        rule = _make_rule()
        result = serialize(rule)
        parsed = json.loads(result)
        keys = list(parsed.keys())
        assert keys == sorted(keys)

    def test_preserves_unicode_vietnamese(self) -> None:
        rule = _make_rule(
            name="Ngưỡng đi trễ",
            description="Đánh dấu nhân viên đi trễ nếu quá ngưỡng cho phép",
        )
        result = serialize(rule)
        assert "Ngưỡng đi trễ" in result
        assert "Đánh dấu nhân viên đi trễ" in result
        # Should not contain unicode escape sequences
        assert "\\u" not in result

    def test_includes_all_serialized_fields(self) -> None:
        rule = _make_rule()
        result = serialize(rule)
        parsed = json.loads(result)
        expected_fields = {
            "rule_id",
            "domain",
            "name",
            "description",
            "rule_condition",
            "rule_action",
            "priority",
            "enabled",
        }
        assert set(parsed.keys()) == expected_fields

    def test_serializes_domain_as_string_value(self) -> None:
        rule = _make_rule(domain=PolicyDomain.LEAVE)
        result = serialize(rule)
        parsed = json.loads(result)
        assert parsed["domain"] == "leave"

    def test_handles_all_operators(self) -> None:
        for op in RuleOperator:
            condition = {"field": "test", "operator": op.value, "value": 10}
            if op == RuleOperator.IS_NULL:
                condition = {"field": "test", "operator": op.value}
            rule = _make_rule(rule_condition=condition)
            result = serialize(rule)
            parsed = json.loads(result)
            assert parsed["rule_condition"]["operator"] == op.value

    def test_handles_all_action_types(self) -> None:
        for action_type in ActionType:
            action = {"type": action_type.value, "parameters": {"key": "val"}}
            rule = _make_rule(rule_action=action)
            result = serialize(rule)
            parsed = json.loads(result)
            assert parsed["rule_action"]["type"] == action_type.value


class TestParse:
    """Tests for the parse function."""

    def test_parses_valid_json(self) -> None:
        rule = _make_rule()
        json_str = serialize(rule)
        result = parse(json_str)
        assert result.rule_id == "attendance_late_threshold"
        assert result.priority == 100
        assert result.enabled is True

    def test_round_trip_preserves_values(self) -> None:
        rule = _make_rule()
        json_str = serialize(rule)
        parsed = parse(json_str)
        json_str2 = serialize(parsed)
        assert json_str == json_str2

    def test_ignores_unknown_fields(self) -> None:
        data = {
            "rule_id": "test_rule",
            "domain": "attendance",
            "name": "Test",
            "description": "A test rule",
            "rule_condition": {"field": "x", "operator": "equals", "value": 1},
            "rule_action": {"type": "flag", "parameters": {}},
            "priority": 50,
            "enabled": True,
            "unknown_field": "should be ignored",
            "another_unknown": 42,
        }
        json_str = json.dumps(data)
        result = parse(json_str)
        assert result.rule_id == "test_rule"

    def test_malformed_json_reports_position(self) -> None:
        with pytest.raises(PolicySerializationError) as exc_info:
            parse('{"rule_id": "test", invalid}')
        assert exc_info.value.position is not None
        assert exc_info.value.position > 0

    def test_missing_required_field_reports_field_errors(self) -> None:
        data = {
            "rule_id": "test_rule",
            "domain": "attendance",
            # missing name, description, rule_condition, rule_action, priority, enabled
        }
        with pytest.raises(PolicySerializationError) as exc_info:
            parse(json.dumps(data))
        assert len(exc_info.value.field_errors) > 0
        missing_fields = [e["field"] for e in exc_info.value.field_errors]
        assert "name" in missing_fields
        assert "description" in missing_fields

    def test_wrong_type_reports_field_errors(self) -> None:
        data = {
            "rule_id": "test_rule",
            "domain": "attendance",
            "name": "Test",
            "description": "Desc",
            "rule_condition": {"field": "x", "operator": "equals", "value": 1},
            "rule_action": {"type": "flag", "parameters": {}},
            "priority": "not_an_int",  # wrong type
            "enabled": True,
        }
        with pytest.raises(PolicySerializationError) as exc_info:
            parse(json.dumps(data))
        field_names = [e["field"] for e in exc_info.value.field_errors]
        assert "priority" in field_names

    def test_unsupported_operator_reports_error(self) -> None:
        data = {
            "rule_id": "test_rule",
            "domain": "attendance",
            "name": "Test",
            "description": "Desc",
            "rule_condition": {"field": "x", "operator": "invalid_op", "value": 1},
            "rule_action": {"type": "flag", "parameters": {}},
            "priority": 50,
            "enabled": True,
        }
        with pytest.raises(PolicySerializationError) as exc_info:
            parse(json.dumps(data))
        field_names = [e["field"] for e in exc_info.value.field_errors]
        assert "rule_condition.operator" in field_names

    def test_unsupported_action_type_reports_error(self) -> None:
        data = {
            "rule_id": "test_rule",
            "domain": "attendance",
            "name": "Test",
            "description": "Desc",
            "rule_condition": {"field": "x", "operator": "equals", "value": 1},
            "rule_action": {"type": "invalid_action", "parameters": {}},
            "priority": 50,
            "enabled": True,
        }
        with pytest.raises(PolicySerializationError) as exc_info:
            parse(json.dumps(data))
        field_names = [e["field"] for e in exc_info.value.field_errors]
        assert "rule_action.type" in field_names

    def test_unsupported_domain_reports_error(self) -> None:
        data = {
            "rule_id": "test_rule",
            "domain": "invalid_domain",
            "name": "Test",
            "description": "Desc",
            "rule_condition": {"field": "x", "operator": "equals", "value": 1},
            "rule_action": {"type": "flag", "parameters": {}},
            "priority": 50,
            "enabled": True,
        }
        with pytest.raises(PolicySerializationError) as exc_info:
            parse(json.dumps(data))
        field_names = [e["field"] for e in exc_info.value.field_errors]
        assert "domain" in field_names

    def test_priority_out_of_range_reports_error(self) -> None:
        data = {
            "rule_id": "test_rule",
            "domain": "attendance",
            "name": "Test",
            "description": "Desc",
            "rule_condition": {"field": "x", "operator": "equals", "value": 1},
            "rule_action": {"type": "flag", "parameters": {}},
            "priority": 1500,
            "enabled": True,
        }
        with pytest.raises(PolicySerializationError) as exc_info:
            parse(json.dumps(data))
        field_names = [e["field"] for e in exc_info.value.field_errors]
        assert "priority" in field_names

    def test_preserves_vietnamese_characters_round_trip(self) -> None:
        data = {
            "rule_id": "vn_rule",
            "domain": "leave",
            "name": "Nghỉ phép năm",
            "description": "Quy định về nghỉ phép năm theo Điều 113 Bộ luật Lao động",
            "rule_condition": {"field": "leave_days", "operator": "greater_than", "value": 12},
            "rule_action": {"type": "restrict", "parameters": {"message": "Vượt quá số ngày"}},
            "priority": 10,
            "enabled": True,
        }
        json_str = json.dumps(data, ensure_ascii=False)
        result = parse(json_str)
        assert result.name == "Nghỉ phép năm"
        assert "Điều 113" in result.description

    def test_non_object_root_reports_error(self) -> None:
        with pytest.raises(PolicySerializationError) as exc_info:
            parse("[1, 2, 3]")
        assert len(exc_info.value.field_errors) > 0
