"""Serialization and parsing service for PolicyRule objects.

Provides deterministic JSON serialization and validated parsing of
PolicyRule entities, preserving Unicode characters and reporting
structured errors for malformed input.
"""

import json
from typing import Any
from uuid import UUID

from src.modules.policy.domain.entities import PolicyRule
from src.modules.policy.domain.enums import ActionType, PolicyDomain, RuleOperator
from src.modules.policy.domain.exceptions import PolicySerializationError

# Fields included in the serialized JSON representation of a PolicyRule.
_SERIALIZED_FIELDS = (
    "rule_id",
    "domain",
    "name",
    "description",
    "rule_condition",
    "rule_action",
    "priority",
    "enabled",
)

# Required fields that must be present in parsed JSON.
_REQUIRED_FIELDS: dict[str, type | tuple[type, ...]] = {
    "rule_id": str,
    "domain": str,
    "name": str,
    "description": str,
    "rule_condition": dict,
    "rule_action": dict,
    "priority": int,
    "enabled": bool,
}

_REQUIRED_CONDITION_FIELDS: dict[str, type | tuple[type, ...]] = {
    "field": str,
    "operator": str,
}

_REQUIRED_ACTION_FIELDS: dict[str, type | tuple[type, ...]] = {
    "type": str,
    "parameters": dict,
}


def _serialize_condition(condition: dict[str, Any]) -> dict[str, Any]:
    """Serialize a rule_condition dict, converting enums to their values."""
    result: dict[str, Any] = {}
    for key, val in condition.items():
        if isinstance(val, RuleOperator):
            result[key] = val.value
        else:
            result[key] = val
    return result


def _serialize_action(action: dict[str, Any]) -> dict[str, Any]:
    """Serialize a rule_action dict, converting enums to their values."""
    result: dict[str, Any] = {}
    for key, val in action.items():
        if isinstance(val, ActionType):
            result[key] = val.value
        else:
            result[key] = val
    return result


def serialize(rule: PolicyRule) -> str:
    """Serialize a PolicyRule object into a deterministic JSON string.

    Uses sorted keys for deterministic field ordering and preserves
    Unicode characters without escaping non-ASCII code points.

    Args:
        rule: The PolicyRule object to serialize.

    Returns:
        A JSON string representation of the rule with deterministic ordering.

    Raises:
        PolicySerializationError: If the rule cannot be serialized.
    """
    try:
        # Use model_dump to safely extract fields from SQLModel instances,
        # avoiding SQLAlchemy instrumentation issues with direct attribute access.
        all_fields = rule.model_dump()

        data: dict[str, Any] = {}
        for field_name in _SERIALIZED_FIELDS:
            value = all_fields[field_name]
            if field_name == "domain":
                data[field_name] = value.value if isinstance(value, PolicyDomain) else value
            elif field_name == "rule_condition":
                data[field_name] = _serialize_condition(value)
            elif field_name == "rule_action":
                data[field_name] = _serialize_action(value)
            else:
                data[field_name] = value

        return json.dumps(data, sort_keys=True, ensure_ascii=False)
    except (TypeError, ValueError, AttributeError, KeyError) as exc:
        raise PolicySerializationError(
            message=f"Failed to serialize PolicyRule: {exc}",
        ) from exc


def parse(json_string: str) -> PolicyRule:
    """Parse a JSON string into a PolicyRule object.

    Validates that all required fields are present and correctly typed.
    Unknown fields are silently ignored. Reports structured errors for
    malformed JSON (with character position) and schema violations
    (with field-level reasons).

    Args:
        json_string: The JSON string to parse.

    Returns:
        A PolicyRule object populated from the JSON data.

    Raises:
        PolicySerializationError: If the JSON is malformed (with position)
            or violates the schema (with field_errors).
    """
    # Step 1: Parse raw JSON
    try:
        data = json.loads(json_string)
    except json.JSONDecodeError as exc:
        raise PolicySerializationError(
            message=f"Malformed JSON: {exc.msg}",
            position=exc.pos,
        ) from exc

    if not isinstance(data, dict):
        raise PolicySerializationError(
            message="JSON root must be an object",
            field_errors=[{"field": "$", "reason": "Expected a JSON object at root level"}],
        )

    # Step 2: Validate schema
    field_errors: list[dict[str, str]] = []

    # Check required top-level fields
    for field_name, expected_type in _REQUIRED_FIELDS.items():
        if field_name not in data:
            field_errors.append(
                {
                    "field": field_name,
                    "reason": f"Required field '{field_name}' is missing",
                }
            )
        elif not isinstance(data[field_name], expected_type):
            field_errors.append(
                {
                    "field": field_name,
                    "reason": (
                        f"Expected type '{expected_type.__name__}', "
                        f"got '{type(data[field_name]).__name__}'"
                    ),
                }
            )

    # Validate domain enum value
    if "domain" in data and isinstance(data["domain"], str):
        try:
            PolicyDomain(data["domain"])
        except ValueError:
            valid_values = [d.value for d in PolicyDomain]
            field_errors.append(
                {
                    "field": "domain",
                    "reason": (
                        f"Unsupported domain value '{data['domain']}'. "
                        f"Must be one of: {valid_values}"
                    ),
                }
            )

    # Validate priority range
    if "priority" in data and isinstance(data["priority"], int):
        if not (1 <= data["priority"] <= 1000):
            field_errors.append(
                {
                    "field": "priority",
                    "reason": "Priority must be between 1 and 1000 inclusive",
                }
            )

    # Validate rule_condition structure
    if "rule_condition" in data and isinstance(data["rule_condition"], dict):
        condition = data["rule_condition"]
        for cond_field, cond_type in _REQUIRED_CONDITION_FIELDS.items():
            if cond_field not in condition:
                field_errors.append(
                    {
                        "field": f"rule_condition.{cond_field}",
                        "reason": f"Required field 'rule_condition.{cond_field}' is missing",
                    }
                )
            elif not isinstance(condition[cond_field], cond_type):
                field_errors.append(
                    {
                        "field": f"rule_condition.{cond_field}",
                        "reason": (
                            f"Expected type '{cond_type.__name__}', "
                            f"got '{type(condition[cond_field]).__name__}'"
                        ),
                    }
                )

        # Validate operator enum
        if "operator" in condition and isinstance(condition["operator"], str):
            try:
                RuleOperator(condition["operator"])
            except ValueError:
                valid_ops = [op.value for op in RuleOperator]
                field_errors.append(
                    {
                        "field": "rule_condition.operator",
                        "reason": (
                            f"Unsupported operator '{condition['operator']}'. "
                            f"Must be one of: {valid_ops}"
                        ),
                    }
                )

        # value field is optional for is_null operator but required otherwise
        if "operator" in condition and isinstance(condition.get("operator"), str):
            try:
                op = RuleOperator(condition["operator"])
                if op != RuleOperator.IS_NULL and "value" not in condition:
                    field_errors.append(
                        {
                            "field": "rule_condition.value",
                            "reason": (
                                "Required field 'rule_condition.value' is missing "
                                f"for operator '{op.value}'"
                            ),
                        }
                    )
            except ValueError:
                pass  # Already reported above

    # Validate rule_action structure
    if "rule_action" in data and isinstance(data["rule_action"], dict):
        action = data["rule_action"]
        for act_field, act_type in _REQUIRED_ACTION_FIELDS.items():
            if act_field not in action:
                field_errors.append(
                    {
                        "field": f"rule_action.{act_field}",
                        "reason": f"Required field 'rule_action.{act_field}' is missing",
                    }
                )
            elif not isinstance(action[act_field], act_type):
                field_errors.append(
                    {
                        "field": f"rule_action.{act_field}",
                        "reason": (
                            f"Expected type '{act_type.__name__}', "
                            f"got '{type(action[act_field]).__name__}'"
                        ),
                    }
                )

        # Validate action type enum
        if "type" in action and isinstance(action["type"], str):
            try:
                ActionType(action["type"])
            except ValueError:
                valid_types = [at.value for at in ActionType]
                field_errors.append(
                    {
                        "field": "rule_action.type",
                        "reason": (
                            f"Unsupported action type '{action['type']}'. "
                            f"Must be one of: {valid_types}"
                        ),
                    }
                )

    # If there are field errors, raise with all of them
    if field_errors:
        raise PolicySerializationError(
            message="Schema validation failed",
            field_errors=field_errors,
        )

    # Step 3: Construct PolicyRule object from validated data
    try:
        condition_data = data["rule_condition"]
        action_data = data["rule_action"]

        # Build the rule_condition dict with enum conversion
        rule_condition: dict[str, Any] = {
            "field": condition_data["field"],
            "operator": RuleOperator(condition_data["operator"]).value,
        }
        if "value" in condition_data:
            rule_condition["value"] = condition_data["value"]

        # Build the rule_action dict with enum conversion
        rule_action: dict[str, Any] = {
            "type": ActionType(action_data["type"]).value,
            "parameters": action_data["parameters"],
        }

        # Use model_validate to properly initialize the SQLModel instance
        # with SQLAlchemy instrumentation. Provide minimal required fields
        # that aren't part of the serialized format with placeholder values.
        rule = PolicyRule.model_validate(
            {
                "rule_id": data["rule_id"],
                "domain": PolicyDomain(data["domain"]),
                "name": data["name"],
                "description": data["description"],
                "rule_condition": rule_condition,
                "rule_action": rule_action,
                "priority": data["priority"],
                "enabled": data["enabled"],
                # Non-serialized fields get placeholder values
                "tenant_id": "",
                "created_by": UUID("00000000-0000-0000-0000-000000000000"),
            }
        )

        return rule
    except (KeyError, ValueError, TypeError) as exc:
        raise PolicySerializationError(
            message=f"Failed to construct PolicyRule: {exc}",
            field_errors=[{"field": "$", "reason": str(exc)}],
        ) from exc
