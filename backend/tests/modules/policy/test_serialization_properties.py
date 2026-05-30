"""Property-based tests for PolicyRule serialization.

Uses Hypothesis to verify correctness properties of the serializer/parser.
"""

# Feature: company-policy-engine, Property 18: Deterministic Serialization
# Feature: company-policy-engine, Property 20: Schema Violation Error Reporting
# Feature: company-policy-engine, Property 21: Unknown Field Tolerance

import json
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.modules.policy.application.serializer_service import parse, serialize
from src.modules.policy.domain.entities import PolicyRule
from src.modules.policy.domain.enums import ActionType, PolicyDomain, RuleOperator
from src.modules.policy.domain.exceptions import PolicySerializationError

# Valid enum values for reference
_VALID_DOMAINS = [d.value for d in PolicyDomain]
_VALID_OPERATORS = [op.value for op in RuleOperator]
_VALID_ACTION_TYPES = [at.value for at in ActionType]

# Required top-level fields with their expected types
_REQUIRED_FIELDS = {
    "rule_id": str,
    "domain": str,
    "name": str,
    "description": str,
    "rule_condition": dict,
    "rule_action": dict,
    "priority": int,
    "enabled": bool,
}


def _valid_policy_rule_dict() -> dict[str, Any]:
    """Return a minimal valid PolicyRule dict."""
    return {
        "rule_id": "test_rule_001",
        "domain": "attendance",
        "name": "Test Rule",
        "description": "A test rule for property testing",
        "rule_condition": {
            "field": "check_in_delay",
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


# Strategy: generate a non-empty subset of required fields to remove
st_fields_to_remove = st.lists(
    st.sampled_from(list(_REQUIRED_FIELDS.keys())),
    min_size=1,
    max_size=len(_REQUIRED_FIELDS),
    unique=True,
)

# Strategy: generate wrong-type values for each field type
_WRONG_TYPE_VALUES: dict[type, st.SearchStrategy] = {
    str: st.one_of(
        st.integers(),
        st.booleans(),
        st.lists(st.integers(), max_size=2),
        st.none(),
    ),
    dict: st.one_of(
        st.text(min_size=1, max_size=10),
        st.integers(),
        st.booleans(),
        st.lists(st.integers(), max_size=2),
    ),
    int: st.one_of(
        st.text(min_size=1, max_size=10),
        st.booleans(),
        st.lists(st.integers(), max_size=2),
    ),
    bool: st.one_of(
        st.text(min_size=1, max_size=10),
        st.integers(min_value=2),
        st.lists(st.integers(), max_size=2),
    ),
}

# Strategy: generate unsupported enum values
st_invalid_domain = st.text(min_size=1, max_size=20).filter(
    lambda s: s not in _VALID_DOMAINS
)
st_invalid_operator = st.text(min_size=1, max_size=30).filter(
    lambda s: s not in _VALID_OPERATORS
)
st_invalid_action_type = st.text(min_size=1, max_size=20).filter(
    lambda s: s not in _VALID_ACTION_TYPES
)


class TestSchemaViolationErrorReporting:
    """Property 20: Schema Violation Error Reporting.

    For any syntactically valid JSON string that does not conform to the
    PolicyRule schema (missing required fields, incorrect field types, or
    unsupported enum values), the parser SHALL return errors identifying
    each non-conforming field and the reason for rejection.

    **Validates: Requirements 6.4**
    """

    @settings(max_examples=100)
    @given(fields_to_remove=st_fields_to_remove)
    def test_missing_required_fields_reported(
        self, fields_to_remove: list[str]
    ) -> None:
        """Removing required fields produces field_errors identifying them."""
        data = _valid_policy_rule_dict()
        for field in fields_to_remove:
            del data[field]

        json_str = json.dumps(data)

        with pytest.raises(PolicySerializationError) as exc_info:
            parse(json_str)

        error = exc_info.value
        assert error.field_errors, "Expected field_errors to be non-empty"

        reported_fields = {e["field"] for e in error.field_errors}
        for field in fields_to_remove:
            assert field in reported_fields, (
                f"Missing field '{field}' not reported in field_errors. "
                f"Reported: {reported_fields}"
            )

        # Each error must have a reason
        for err in error.field_errors:
            assert "reason" in err, f"Error for '{err['field']}' missing 'reason'"
            assert err["reason"], f"Error for '{err['field']}' has empty reason"

    @settings(max_examples=100)
    @given(
        field_name=st.sampled_from(list(_REQUIRED_FIELDS.keys())),
        data=st.data(),
    )
    def test_wrong_type_fields_reported(
        self, field_name: str, data: st.DataObject
    ) -> None:
        """Replacing a field with a wrong type produces field_errors."""
        rule_data = _valid_policy_rule_dict()
        expected_type = _REQUIRED_FIELDS[field_name]
        wrong_value = data.draw(_WRONG_TYPE_VALUES[expected_type])

        # None becomes null in JSON which is a different type for all fields
        rule_data[field_name] = wrong_value

        json_str = json.dumps(rule_data)

        with pytest.raises(PolicySerializationError) as exc_info:
            parse(json_str)

        error = exc_info.value
        assert error.field_errors, (
            f"Expected field_errors when '{field_name}' has wrong type "
            f"(value={wrong_value!r})"
        )

        reported_fields = {e["field"] for e in error.field_errors}
        assert field_name in reported_fields, (
            f"Field '{field_name}' with wrong type not reported. "
            f"Reported: {reported_fields}"
        )

        # Each error must have a reason
        for err in error.field_errors:
            if err["field"] == field_name:
                assert "reason" in err
                assert err["reason"]

    @settings(max_examples=100)
    @given(invalid_domain=st_invalid_domain)
    def test_unsupported_domain_reported(self, invalid_domain: str) -> None:
        """Unsupported domain enum values produce field_errors."""
        data = _valid_policy_rule_dict()
        data["domain"] = invalid_domain

        json_str = json.dumps(data)

        with pytest.raises(PolicySerializationError) as exc_info:
            parse(json_str)

        error = exc_info.value
        assert error.field_errors, (
            f"Expected field_errors for unsupported domain '{invalid_domain}'"
        )

        reported_fields = {e["field"] for e in error.field_errors}
        assert "domain" in reported_fields, (
            f"Unsupported domain '{invalid_domain}' not reported. "
            f"Reported: {reported_fields}"
        )

        # Reason should mention the invalid value or valid options
        domain_errors = [e for e in error.field_errors if e["field"] == "domain"]
        assert domain_errors[0]["reason"]

    @settings(max_examples=100)
    @given(invalid_operator=st_invalid_operator)
    def test_unsupported_operator_reported(self, invalid_operator: str) -> None:
        """Unsupported operator enum values produce field_errors."""
        data = _valid_policy_rule_dict()
        data["rule_condition"]["operator"] = invalid_operator

        json_str = json.dumps(data)

        with pytest.raises(PolicySerializationError) as exc_info:
            parse(json_str)

        error = exc_info.value
        assert error.field_errors, (
            f"Expected field_errors for unsupported operator '{invalid_operator}'"
        )

        reported_fields = {e["field"] for e in error.field_errors}
        assert "rule_condition.operator" in reported_fields, (
            f"Unsupported operator '{invalid_operator}' not reported. "
            f"Reported: {reported_fields}"
        )

    @settings(max_examples=100)
    @given(invalid_action_type=st_invalid_action_type)
    def test_unsupported_action_type_reported(
        self, invalid_action_type: str
    ) -> None:
        """Unsupported action type enum values produce field_errors."""
        data = _valid_policy_rule_dict()
        data["rule_action"]["type"] = invalid_action_type

        json_str = json.dumps(data)

        with pytest.raises(PolicySerializationError) as exc_info:
            parse(json_str)

        error = exc_info.value
        assert error.field_errors, (
            f"Expected field_errors for unsupported action type "
            f"'{invalid_action_type}'"
        )

        reported_fields = {e["field"] for e in error.field_errors}
        assert "rule_action.type" in reported_fields, (
            f"Unsupported action type '{invalid_action_type}' not reported. "
            f"Reported: {reported_fields}"
        )


# ---------------------------------------------------------------------------
# Strategies for generating valid PolicyRule objects
# ---------------------------------------------------------------------------

_domains = st.sampled_from(list(PolicyDomain))
_operators = st.sampled_from(list(RuleOperator))
_action_types = st.sampled_from(list(ActionType))

_rule_ids = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Pd")),
    min_size=1,
    max_size=64,
)

_names = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Z", "P")),
    min_size=1,
    max_size=128,
)

_descriptions = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Z", "P")),
    min_size=1,
    max_size=256,
)

_priorities = st.integers(min_value=1, max_value=1000)

_condition_values = st.one_of(
    st.integers(min_value=-10000, max_value=10000),
    st.floats(allow_nan=False, allow_infinity=False, min_value=-1e6, max_value=1e6),
    st.text(min_size=0, max_size=50),
    st.lists(st.integers(min_value=0, max_value=100), min_size=1, max_size=5),
)

_action_params = st.fixed_dictionaries(
    {},
    optional={
        "status": st.text(min_size=1, max_size=20),
        "message": st.text(min_size=1, max_size=50),
        "threshold": st.integers(min_value=0, max_value=1000),
    },
)


@st.composite
def policy_rule_strategy(draw: st.DrawFn) -> PolicyRule:
    """Generate a valid PolicyRule object with random but valid field values."""
    operator = draw(_operators)

    condition: dict[str, Any] = {
        "field": draw(st.text(
            alphabet=st.characters(whitelist_categories=("L", "N")),
            min_size=1,
            max_size=30,
        )),
        "operator": operator.value,
    }
    if operator != RuleOperator.IS_NULL:
        condition["value"] = draw(_condition_values)

    action: dict[str, Any] = {
        "type": draw(_action_types).value,
        "parameters": draw(_action_params),
    }

    rule = PolicyRule.model_validate({
        "rule_id": draw(_rule_ids),
        "domain": draw(_domains),
        "name": draw(_names),
        "description": draw(_descriptions),
        "rule_condition": condition,
        "rule_action": action,
        "priority": draw(_priorities),
        "enabled": draw(st.booleans()),
        "tenant_id": "test_tenant",
        "created_by": "00000000-0000-0000-0000-000000000001",
    })
    return rule


# ---------------------------------------------------------------------------
# Property 18: Deterministic Serialization
# ---------------------------------------------------------------------------


class TestDeterministicSerialization:
    """Property 18: Deterministic Serialization.

    For any valid PolicyRule object, serializing it multiple times SHALL
    always produce the same byte-identical JSON output (deterministic
    field ordering).

    **Validates: Requirements 6.1**
    """

    @given(rule=policy_rule_strategy())
    @settings(max_examples=100)
    def test_multiple_serializations_produce_identical_output(
        self, rule: PolicyRule
    ) -> None:
        """Serializing the same PolicyRule multiple times always produces
        byte-identical JSON output."""
        first = serialize(rule)
        second = serialize(rule)
        third = serialize(rule)

        assert first == second, (
            "Second serialization differs from first"
        )
        assert first == third, (
            "Third serialization differs from first"
        )



# ---------------------------------------------------------------------------
# Property 21: Unknown Field Tolerance
# Feature: company-policy-engine, Property 21: Unknown Field Tolerance
# ---------------------------------------------------------------------------

# Vietnamese alphabet characters for generating Unicode text in Property 21
_VIET_CHARS = (
    "abcdeghiklmnopqrstuvxy "
    "0123456789"
)

# Strategy for generating random extra field keys (prefixed to avoid collision)
_extra_field_key_st = st.from_regex(r"x_[a-z][a-z0-9_]{0,20}", fullmatch=True)

_extra_field_value_st = st.one_of(
    st.integers(min_value=-1_000_000, max_value=1_000_000),
    st.text(alphabet=_VIET_CHARS, min_size=0, max_size=50),
    st.booleans(),
    st.none(),
    st.lists(st.integers(min_value=-100, max_value=100), min_size=0, max_size=5),
    st.dictionaries(
        keys=st.from_regex(r"[a-z]{1,10}", fullmatch=True),
        values=st.one_of(
            st.integers(), st.text(min_size=0, max_size=10), st.booleans()
        ),
        min_size=0,
        max_size=3,
    ),
)

_extra_fields_st = st.dictionaries(
    keys=_extra_field_key_st,
    values=_extra_field_value_st,
    min_size=1,
    max_size=5,
)


@st.composite
def _p21_policy_rule_strategy(draw: st.DrawFn) -> PolicyRule:
    """Generate a valid PolicyRule object for Property 21 testing."""
    operator = draw(st.sampled_from(list(RuleOperator)))
    condition: dict[str, Any] = {
        "field": draw(st.from_regex(r"[a-z][a-z0-9_]{0,20}", fullmatch=True)),
        "operator": operator.value,
    }
    if operator != RuleOperator.IS_NULL:
        condition["value"] = draw(
            st.one_of(
                st.integers(min_value=-1000, max_value=1000),
                st.text(alphabet=_VIET_CHARS, min_size=1, max_size=30),
                st.booleans(),
            )
        )

    action: dict[str, Any] = {
        "type": draw(st.sampled_from(list(ActionType))).value,
        "parameters": draw(
            st.dictionaries(
                keys=st.from_regex(r"[a-z_]{1,15}", fullmatch=True),
                values=st.one_of(
                    st.integers(min_value=-100, max_value=100),
                    st.text(min_size=0, max_size=20),
                    st.booleans(),
                ),
                min_size=0,
                max_size=3,
            )
        ),
    }

    return PolicyRule.model_validate(
        {
            "rule_id": draw(
                st.from_regex(r"[a-z][a-z0-9_]{0,63}", fullmatch=True)
            ),
            "domain": draw(st.sampled_from(list(PolicyDomain))),
            "name": draw(
                st.text(alphabet=_VIET_CHARS, min_size=1, max_size=64)
            ),
            "description": draw(
                st.text(alphabet=_VIET_CHARS, min_size=1, max_size=128)
            ),
            "rule_condition": condition,
            "rule_action": action,
            "priority": draw(st.integers(min_value=1, max_value=1000)),
            "enabled": draw(st.booleans()),
            "tenant_id": "test_tenant",
            "created_by": "00000000-0000-0000-0000-000000000000",
        }
    )


@st.composite
def valid_policy_rule_json_with_extra_fields(
    draw: st.DrawFn,
) -> tuple[str, str]:
    """Generate valid PolicyRule JSON and a version with extra unknown fields.

    Returns a tuple of (original_json, augmented_json) where augmented_json
    has additional fields not defined in the PolicyRule schema.
    """
    rule = draw(_p21_policy_rule_strategy())
    original_json = serialize(rule)

    # Parse the JSON to a dict, add extra fields, then re-serialize
    data = json.loads(original_json)
    extra_fields = draw(_extra_fields_st)
    augmented_data = {**data, **extra_fields}

    augmented_json = json.dumps(augmented_data, ensure_ascii=False)
    return (original_json, augmented_json)


class TestUnknownFieldTolerance:
    """Property 21: Unknown Field Tolerance.

    **Validates: Requirements 6.5**

    For any valid PolicyRule JSON with additional fields not defined in the
    schema, parsing SHALL succeed and produce the same PolicyRule object as
    parsing the JSON without the extra fields.
    """

    @given(json_pair=valid_policy_rule_json_with_extra_fields())
    @settings(max_examples=100)
    def test_unknown_fields_are_ignored(
        self, json_pair: tuple[str, str]
    ) -> None:
        """Parsing JSON with extra unknown fields produces the same PolicyRule.

        **Validates: Requirements 6.5**
        """
        original_json, augmented_json = json_pair

        # Parse both versions
        rule_from_original = parse(original_json)
        rule_from_augmented = parse(augmented_json)

        # Both must produce PolicyRule objects with identical field values
        assert rule_from_original.rule_id == rule_from_augmented.rule_id
        assert rule_from_original.domain == rule_from_augmented.domain
        assert rule_from_original.name == rule_from_augmented.name
        assert rule_from_original.description == rule_from_augmented.description
        assert rule_from_original.rule_condition == rule_from_augmented.rule_condition
        assert rule_from_original.rule_action == rule_from_augmented.rule_action
        assert rule_from_original.priority == rule_from_augmented.priority
        assert rule_from_original.enabled == rule_from_augmented.enabled


# ---------------------------------------------------------------------------
# Strategies for Property 20: Schema Violation Error Reporting
# ---------------------------------------------------------------------------

# Strategy: generate a non-empty subset of required fields to remove
st_fields_to_remove = st.lists(
    st.sampled_from(list(_REQUIRED_FIELDS.keys())),
    min_size=1,
    max_size=len(_REQUIRED_FIELDS),
    unique=True,
)

# Strategy: generate wrong-type values for each field type
_WRONG_TYPE_VALUES: dict[type, st.SearchStrategy] = {
    str: st.one_of(
        st.integers(),
        st.booleans(),
        st.lists(st.integers(), max_size=2),
    ),
    dict: st.one_of(
        st.text(min_size=1, max_size=10),
        st.integers(),
        st.booleans(),
        st.lists(st.integers(), max_size=2),
    ),
    int: st.one_of(
        st.text(min_size=1, max_size=10),
        st.lists(st.integers(), max_size=2),
    ),
    bool: st.one_of(
        st.text(min_size=1, max_size=10),
        st.integers(min_value=2),
        st.lists(st.integers(), max_size=2),
    ),
}

# Strategy: generate unsupported enum values
st_invalid_domain = st.text(min_size=1, max_size=20).filter(
    lambda s: s not in _VALID_DOMAINS
)
st_invalid_operator = st.text(min_size=1, max_size=30).filter(
    lambda s: s not in _VALID_OPERATORS
)
st_invalid_action_type = st.text(min_size=1, max_size=20).filter(
    lambda s: s not in _VALID_ACTION_TYPES
)


# ---------------------------------------------------------------------------
# Property 20: Schema Violation Error Reporting
# ---------------------------------------------------------------------------


class TestSchemaViolationErrorReporting:
    """Property 20: Schema Violation Error Reporting.

    For any syntactically valid JSON string that does not conform to the
    PolicyRule schema (missing required fields, incorrect field types, or
    unsupported enum values), the parser SHALL return errors identifying
    each non-conforming field and the reason for rejection.

    **Validates: Requirements 6.4**
    """

    @settings(max_examples=100)
    @given(fields_to_remove=st_fields_to_remove)
    def test_missing_required_fields_reported(
        self, fields_to_remove: list[str]
    ) -> None:
        """Removing required fields produces field_errors identifying them."""
        data = _valid_policy_rule_dict()
        for field in fields_to_remove:
            del data[field]

        json_str = json.dumps(data)

        with pytest.raises(PolicySerializationError) as exc_info:
            parse(json_str)

        error = exc_info.value
        assert error.field_errors, "Expected field_errors to be non-empty"

        reported_fields = {e["field"] for e in error.field_errors}
        for field in fields_to_remove:
            assert field in reported_fields, (
                f"Missing field '{field}' not reported in field_errors. "
                f"Reported: {reported_fields}"
            )

        # Each error must have a reason
        for err in error.field_errors:
            assert "reason" in err, f"Error for '{err['field']}' missing 'reason'"
            assert err["reason"], f"Error for '{err['field']}' has empty reason"

    @settings(max_examples=100)
    @given(
        field_name=st.sampled_from(list(_REQUIRED_FIELDS.keys())),
        data=st.data(),
    )
    def test_wrong_type_fields_reported(
        self, field_name: str, data: st.DataObject
    ) -> None:
        """Replacing a field with a wrong type produces field_errors."""
        rule_data = _valid_policy_rule_dict()
        expected_type = _REQUIRED_FIELDS[field_name]
        wrong_value = data.draw(_WRONG_TYPE_VALUES[expected_type])

        rule_data[field_name] = wrong_value

        json_str = json.dumps(rule_data)

        with pytest.raises(PolicySerializationError) as exc_info:
            parse(json_str)

        error = exc_info.value
        assert error.field_errors, (
            f"Expected field_errors when '{field_name}' has wrong type "
            f"(value={wrong_value!r})"
        )

        reported_fields = {e["field"] for e in error.field_errors}
        assert field_name in reported_fields, (
            f"Field '{field_name}' with wrong type not reported. "
            f"Reported: {reported_fields}"
        )

        # Each error must have a reason
        for err in error.field_errors:
            if err["field"] == field_name:
                assert "reason" in err
                assert err["reason"]

    @settings(max_examples=100)
    @given(invalid_domain=st_invalid_domain)
    def test_unsupported_domain_reported(self, invalid_domain: str) -> None:
        """Unsupported domain enum values produce field_errors."""
        data = _valid_policy_rule_dict()
        data["domain"] = invalid_domain

        json_str = json.dumps(data)

        with pytest.raises(PolicySerializationError) as exc_info:
            parse(json_str)

        error = exc_info.value
        assert error.field_errors, (
            f"Expected field_errors for unsupported domain '{invalid_domain}'"
        )

        reported_fields = {e["field"] for e in error.field_errors}
        assert "domain" in reported_fields, (
            f"Unsupported domain '{invalid_domain}' not reported. "
            f"Reported: {reported_fields}"
        )

        # Reason should mention the invalid value or valid options
        domain_errors = [
            e for e in error.field_errors if e["field"] == "domain"
        ]
        assert domain_errors[0]["reason"]

    @settings(max_examples=100)
    @given(invalid_operator=st_invalid_operator)
    def test_unsupported_operator_reported(
        self, invalid_operator: str
    ) -> None:
        """Unsupported operator enum values produce field_errors."""
        data = _valid_policy_rule_dict()
        data["rule_condition"]["operator"] = invalid_operator

        json_str = json.dumps(data)

        with pytest.raises(PolicySerializationError) as exc_info:
            parse(json_str)

        error = exc_info.value
        assert error.field_errors, (
            f"Expected field_errors for unsupported operator "
            f"'{invalid_operator}'"
        )

        reported_fields = {e["field"] for e in error.field_errors}
        assert "rule_condition.operator" in reported_fields, (
            f"Unsupported operator '{invalid_operator}' not reported. "
            f"Reported: {reported_fields}"
        )

    @settings(max_examples=100)
    @given(invalid_action_type=st_invalid_action_type)
    def test_unsupported_action_type_reported(
        self, invalid_action_type: str
    ) -> None:
        """Unsupported action type enum values produce field_errors."""
        data = _valid_policy_rule_dict()
        data["rule_action"]["type"] = invalid_action_type

        json_str = json.dumps(data)

        with pytest.raises(PolicySerializationError) as exc_info:
            parse(json_str)

        error = exc_info.value
        assert error.field_errors, (
            f"Expected field_errors for unsupported action type "
            f"'{invalid_action_type}'"
        )

        reported_fields = {e["field"] for e in error.field_errors}
        assert "rule_action.type" in reported_fields, (
            f"Unsupported action type '{invalid_action_type}' not reported. "
            f"Reported: {reported_fields}"
        )


# ---------------------------------------------------------------------------
# Property 21: Unknown Field Tolerance
# ---------------------------------------------------------------------------

# Vietnamese characters for generating realistic text
_VIETNAMESE_CHARS = (
    "aăâbcdđeêghiklmnoôơpqrstuưvxy"
    "AĂÂBCDĐEÊGHIKLMNOÔƠPQRSTUƯVXY"
    "àảãáạằẳẵắặầẩẫấậèẻẽéẹềểễếệ"
    "ìỉĩíịòỏõóọồổỗốộờởỡớợùủũúụ"
    "ừửữứựỳỷỹýỵ 0123456789"
)

st_extra_field_names = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Pd")),
    min_size=1,
    max_size=30,
).filter(lambda s: s not in _REQUIRED_FIELDS)

st_extra_field_values = st.one_of(
    st.text(alphabet=_VIETNAMESE_CHARS, min_size=0, max_size=50),
    st.integers(min_value=-1000, max_value=1000),
    st.floats(allow_nan=False, allow_infinity=False),
    st.booleans(),
    st.none(),
    st.lists(st.integers(), max_size=3),
    st.dictionaries(
        st.text(min_size=1, max_size=10),
        st.integers(),
        max_size=3,
    ),
)

st_extra_fields = st.dictionaries(
    st_extra_field_names,
    st_extra_field_values,
    min_size=1,
    max_size=5,
)


class TestUnknownFieldTolerance:
    """Property 21: Unknown Field Tolerance.

    For any valid PolicyRule JSON with additional fields not defined in
    the schema, parsing SHALL succeed and produce the same PolicyRule
    object as parsing the JSON without the extra fields.

    **Validates: Requirements 6.5**
    """

    @settings(max_examples=100)
    @given(extra_fields=st_extra_fields)
    def test_extra_fields_ignored_during_parsing(
        self, extra_fields: dict[str, Any]
    ) -> None:
        """Parsing JSON with unknown fields produces the same result as
        parsing without them."""
        base_data = _valid_policy_rule_dict()

        # Parse without extra fields
        json_without = json.dumps(base_data, ensure_ascii=False)
        rule_without = parse(json_without)

        # Parse with extra fields
        data_with_extra = {**base_data, **extra_fields}
        json_with = json.dumps(data_with_extra, ensure_ascii=False)
        rule_with = parse(json_with)

        # Both should produce identical PolicyRule objects
        assert rule_with.rule_id == rule_without.rule_id
        assert rule_with.domain == rule_without.domain
        assert rule_with.name == rule_without.name
        assert rule_with.description == rule_without.description
        assert rule_with.rule_condition == rule_without.rule_condition
        assert rule_with.rule_action == rule_without.rule_action
        assert rule_with.priority == rule_without.priority
        assert rule_with.enabled == rule_without.enabled
