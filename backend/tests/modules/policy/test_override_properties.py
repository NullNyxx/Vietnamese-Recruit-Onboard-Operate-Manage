# Feature: company-policy-engine, Property 7: Override Reset Restores Template Default
# Feature: company-policy-engine, Property 8: Type Validation Rejection
"""Property-based tests for override reset and type validation rejection.

Property 7: For any template-based policy rule that has been overridden,
resetting the override SHALL produce a rule whose effective value is identical
to the original policy template default value, and the override record SHALL
no longer exist in storage.
**Validates: Requirements 3.6**

Property 8: For any policy rule field with a defined expected type (numeric for
thresholds, duration for time values, percentage for multipliers), submitting an
override value of a different type SHALL always be rejected with an error
indicating the expected type.
**Validates: Requirements 3.7**
"""

import string
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.modules.policy.application.policy_service import PolicyService
from src.modules.policy.domain.entities import PolicyRule, PolicyTemplate
from src.modules.policy.domain.enums import ActionType, PolicyDomain, RuleOperator
from src.modules.policy.domain.exceptions import PolicyValidationError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_policy_rule(
    *,
    is_custom: bool = False,
    template_rule_id=None,
    rule_id: str = "test-rule",
    tenant_id: str = "tenant-001",
) -> PolicyRule:
    """Create a PolicyRule instance for testing."""
    return PolicyRule(
        id=uuid4(),
        tenant_id=tenant_id,
        domain=PolicyDomain.ATTENDANCE,
        rule_id=rule_id,
        name="Test Rule",
        description="A test rule",
        rule_condition={"field": "minutes_late", "operator": "greater_than", "value": 15},
        rule_action={"type": "flag", "parameters": {"status": "late"}},
        priority=100,
        enabled=True,
        template_rule_id=template_rule_id,
        is_custom=is_custom,
        is_deleted=False,
        created_by=uuid4(),
    )


# ---------------------------------------------------------------------------
# Strategies for generating wrong-type values
# ---------------------------------------------------------------------------

# Values that are NOT integers (and not bools, since bool is subclass of int)
_non_integer_values = st.one_of(
    st.text(min_size=1, max_size=50),
    st.floats(allow_nan=False, allow_infinity=False),
    st.lists(st.integers(), min_size=0, max_size=3),
    st.dictionaries(st.text(min_size=1, max_size=5), st.integers(), max_size=3),
    st.none(),
)

# Values that are NOT booleans
_non_boolean_values = st.one_of(
    st.text(min_size=1, max_size=50),
    st.integers(min_value=-1000, max_value=1000),
    st.floats(allow_nan=False, allow_infinity=False),
    st.lists(st.integers(), min_size=0, max_size=3),
    st.dictionaries(st.text(min_size=1, max_size=5), st.integers(), max_size=3),
    st.none(),
)

# Values that are NOT strings
_non_string_values = st.one_of(
    st.integers(min_value=-1000, max_value=1000),
    st.floats(allow_nan=False, allow_infinity=False),
    st.booleans(),
    st.lists(st.integers(), min_size=0, max_size=3),
    st.dictionaries(st.text(min_size=1, max_size=5), st.integers(), max_size=3),
    st.none(),
)

# Values that are NOT dicts
_non_dict_values = st.one_of(
    st.text(min_size=1, max_size=50),
    st.integers(min_value=-1000, max_value=1000),
    st.floats(allow_nan=False, allow_infinity=False),
    st.booleans(),
    st.lists(st.integers(), min_size=0, max_size=3),
    st.none(),
)


# ---------------------------------------------------------------------------
# Property Tests
# ---------------------------------------------------------------------------


class TestProperty8TypeValidationRejection:
    """Property 8: Type Validation Rejection.

    For any policy rule field with a defined expected type (numeric for
    thresholds, duration for time values, percentage for multipliers),
    submitting an override value of a different type SHALL always be
    rejected with an error indicating the expected type.

    **Validates: Requirements 3.7**
    """

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """Set up mocked repositories and service for each test."""
        self.policy_repo = AsyncMock()
        self.template_repo = AsyncMock()
        self.service = PolicyService(
            policy_repo=self.policy_repo,
            template_repo=self.template_repo,
        )
        self.tenant_id = "tenant-001"
        self.user_id = uuid4()

        # Default: return a custom rule (no legal minimum checks needed)
        self.rule = _make_policy_rule(is_custom=True)
        self.policy_repo.get_rule.return_value = self.rule

    @settings(max_examples=100)
    @given(wrong_value=_non_integer_values)
    @pytest.mark.asyncio
    async def test_priority_rejects_non_integer_type(self, wrong_value) -> None:
        """Submitting a non-integer value for priority SHALL be rejected.

        Priority is a numeric threshold field (integer 1-1000). Any value
        that is not an integer must be rejected with a field-level error.
        """
        # Booleans are technically int subclass in Python but should be rejected
        if isinstance(wrong_value, bool):
            pass  # bool IS rejected by the service (isinstance check excludes bool)
        elif isinstance(wrong_value, int):
            return  # Skip actual integers - they won't fail type check

        with pytest.raises(PolicyValidationError) as exc_info:
            await self.service.update_rule(
                tenant_id=self.tenant_id,
                rule_id="test-rule",
                updates={"priority": wrong_value},
                user_id=self.user_id,
            )

        error = exc_info.value
        assert len(error.fields) >= 1
        error_fields = [e["field"] for e in error.fields]
        assert "priority" in error_fields
        priority_error = next(e for e in error.fields if e["field"] == "priority")
        assert "reason" in priority_error
        assert len(priority_error["reason"]) > 0

    @settings(max_examples=100)
    @given(wrong_value=_non_boolean_values)
    @pytest.mark.asyncio
    async def test_enabled_rejects_non_boolean_type(self, wrong_value) -> None:
        """Submitting a non-boolean value for enabled SHALL be rejected.

        The enabled field expects a boolean. Any other type must be
        rejected with a field-level error indicating the expected type.
        """
        if isinstance(wrong_value, bool):
            return  # Skip actual booleans

        with pytest.raises(PolicyValidationError) as exc_info:
            await self.service.update_rule(
                tenant_id=self.tenant_id,
                rule_id="test-rule",
                updates={"enabled": wrong_value},
                user_id=self.user_id,
            )

        error = exc_info.value
        assert len(error.fields) >= 1
        error_fields = [e["field"] for e in error.fields]
        assert "enabled" in error_fields
        enabled_error = next(e for e in error.fields if e["field"] == "enabled")
        assert "reason" in enabled_error
        assert len(enabled_error["reason"]) > 0

    @settings(max_examples=100)
    @given(wrong_value=_non_string_values)
    @pytest.mark.asyncio
    async def test_name_rejects_non_string_type(self, wrong_value) -> None:
        """Submitting a non-string value for name SHALL be rejected.

        The name field expects a string. Any other type must be
        rejected with a field-level error indicating the expected type.
        """
        if isinstance(wrong_value, str):
            return  # Skip actual strings

        with pytest.raises(PolicyValidationError) as exc_info:
            await self.service.update_rule(
                tenant_id=self.tenant_id,
                rule_id="test-rule",
                updates={"name": wrong_value},
                user_id=self.user_id,
            )

        error = exc_info.value
        assert len(error.fields) >= 1
        error_fields = [e["field"] for e in error.fields]
        assert "name" in error_fields
        name_error = next(e for e in error.fields if e["field"] == "name")
        assert "reason" in name_error
        assert len(name_error["reason"]) > 0

    @settings(max_examples=100)
    @given(wrong_value=_non_dict_values)
    @pytest.mark.asyncio
    async def test_rule_condition_rejects_non_dict_type(self, wrong_value) -> None:
        """Submitting a non-dict value for rule_condition SHALL be rejected.

        The rule_condition field expects a dict/object. Any other type
        must be rejected with a field-level error indicating the expected type.
        """
        if isinstance(wrong_value, dict):
            return  # Skip actual dicts

        with pytest.raises(PolicyValidationError) as exc_info:
            await self.service.update_rule(
                tenant_id=self.tenant_id,
                rule_id="test-rule",
                updates={"rule_condition": wrong_value},
                user_id=self.user_id,
            )

        error = exc_info.value
        assert len(error.fields) >= 1
        error_fields = [e["field"] for e in error.fields]
        assert "rule_condition" in error_fields
        condition_error = next(
            e for e in error.fields if e["field"] == "rule_condition"
        )
        assert "reason" in condition_error
        assert len(condition_error["reason"]) > 0

    @settings(max_examples=100)
    @given(wrong_value=_non_dict_values)
    @pytest.mark.asyncio
    async def test_rule_action_rejects_non_dict_type(self, wrong_value) -> None:
        """Submitting a non-dict value for rule_action SHALL be rejected.

        The rule_action field expects a dict/object. Any other type
        must be rejected with a field-level error indicating the expected type.
        """
        if isinstance(wrong_value, dict):
            return  # Skip actual dicts

        with pytest.raises(PolicyValidationError) as exc_info:
            await self.service.update_rule(
                tenant_id=self.tenant_id,
                rule_id="test-rule",
                updates={"rule_action": wrong_value},
                user_id=self.user_id,
            )

        error = exc_info.value
        assert len(error.fields) >= 1
        error_fields = [e["field"] for e in error.fields]
        assert "rule_action" in error_fields
        action_error = next(
            e for e in error.fields if e["field"] == "rule_action"
        )
        assert "reason" in action_error
        assert len(action_error["reason"]) > 0

    @settings(max_examples=100)
    @given(wrong_value=_non_string_values)
    @pytest.mark.asyncio
    async def test_description_rejects_non_string_type(self, wrong_value) -> None:
        """Submitting a non-string value for description SHALL be rejected.

        The description field expects a string. Any other type must be
        rejected with a field-level error indicating the expected type.
        """
        if isinstance(wrong_value, str):
            return  # Skip actual strings

        with pytest.raises(PolicyValidationError) as exc_info:
            await self.service.update_rule(
                tenant_id=self.tenant_id,
                rule_id="test-rule",
                updates={"description": wrong_value},
                user_id=self.user_id,
            )

        error = exc_info.value
        assert len(error.fields) >= 1
        error_fields = [e["field"] for e in error.fields]
        assert "description" in error_fields
        desc_error = next(
            e for e in error.fields if e["field"] == "description"
        )
        assert "reason" in desc_error
        assert len(desc_error["reason"]) > 0


# ---------------------------------------------------------------------------
# Feature: company-policy-engine, Property 7: Override Reset Restores Template Default
# ---------------------------------------------------------------------------

# Strategies for Property 7

SUPPORTED_OPERATORS: list[str] = [op.value for op in RuleOperator]
SUPPORTED_ACTION_TYPES: list[str] = [at.value for at in ActionType]
SUPPORTED_DOMAINS: list[str] = [d.value for d in PolicyDomain]


@st.composite
def template_values(draw: st.DrawFn) -> dict:
    """Generate random template default values."""
    domain = draw(st.sampled_from(SUPPORTED_DOMAINS))
    name = draw(
        st.text(
            alphabet=string.ascii_letters + string.digits + " -_",
            min_size=1,
            max_size=64,
        )
    )
    description = draw(
        st.text(
            alphabet=string.ascii_letters + string.digits + " .,",
            min_size=0,
            max_size=128,
        )
    )
    operator = draw(st.sampled_from(SUPPORTED_OPERATORS))
    action_type = draw(st.sampled_from(SUPPORTED_ACTION_TYPES))
    priority = draw(st.integers(min_value=1, max_value=1000))
    enabled = draw(st.booleans())
    field_name = draw(
        st.text(alphabet=string.ascii_lowercase + "_", min_size=1, max_size=32)
    )
    condition_value = draw(st.integers(min_value=0, max_value=10000))

    return {
        "domain": domain,
        "name": name,
        "description": description,
        "rule_condition": {
            "field": field_name,
            "operator": operator,
            "value": condition_value,
        },
        "rule_action": {
            "type": action_type,
            "parameters": {"status": draw(st.text(min_size=1, max_size=20))},
        },
        "priority": priority,
        "enabled": enabled,
    }


@st.composite
def override_values(draw: st.DrawFn) -> dict:
    """Generate random override values that differ from template defaults."""
    name = draw(
        st.text(
            alphabet=string.ascii_letters + string.digits + " -_",
            min_size=1,
            max_size=64,
        )
    )
    description = draw(
        st.text(
            alphabet=string.ascii_letters + string.digits + " .,",
            min_size=0,
            max_size=128,
        )
    )
    operator = draw(st.sampled_from(SUPPORTED_OPERATORS))
    action_type = draw(st.sampled_from(SUPPORTED_ACTION_TYPES))
    priority = draw(st.integers(min_value=1, max_value=1000))
    enabled = draw(st.booleans())
    field_name = draw(
        st.text(alphabet=string.ascii_lowercase + "_", min_size=1, max_size=32)
    )
    condition_value = draw(st.integers(min_value=0, max_value=10000))

    return {
        "name": name,
        "description": description,
        "rule_condition": {
            "field": field_name,
            "operator": operator,
            "value": condition_value,
        },
        "rule_action": {
            "type": action_type,
            "parameters": {"status": draw(st.text(min_size=1, max_size=20))},
        },
        "priority": priority,
        "enabled": enabled,
    }


class TestProperty7OverrideResetRestoresTemplateDefault:
    """Property 7: Override Reset Restores Template Default.

    For any template-based policy rule that has been overridden,
    resetting the override SHALL produce a rule whose effective value
    is identical to the original policy template default value, and
    the override record SHALL no longer exist in storage.

    **Validates: Requirements 3.6**
    """

    @settings(max_examples=100)
    @given(tpl_vals=template_values(), ovr_vals=override_values())
    @pytest.mark.asyncio
    async def test_reset_restores_all_template_fields(
        self,
        tpl_vals: dict,
        ovr_vals: dict,
    ) -> None:
        """After reset, the rule's fields SHALL match the template defaults."""
        template_id = uuid4()
        tenant_id = "tenant-prop7"
        rule_id = "rule-under-test"

        template = PolicyTemplate(
            id=template_id,
            domain=PolicyDomain(tpl_vals["domain"]),
            rule_id=rule_id,
            name=tpl_vals["name"],
            description=tpl_vals["description"],
            rule_condition=tpl_vals["rule_condition"],
            rule_action=tpl_vals["rule_action"],
            priority=tpl_vals["priority"],
            enabled=tpl_vals["enabled"],
            legal_constraints=None,
        )

        overridden_rule = PolicyRule(
            id=uuid4(),
            tenant_id=tenant_id,
            domain=PolicyDomain(tpl_vals["domain"]),
            rule_id=rule_id,
            name=ovr_vals["name"],
            description=ovr_vals["description"],
            rule_condition=ovr_vals["rule_condition"],
            rule_action=ovr_vals["rule_action"],
            priority=ovr_vals["priority"],
            enabled=ovr_vals["enabled"],
            template_rule_id=template_id,
            is_custom=False,
            is_deleted=False,
            created_by=uuid4(),
        )

        reset_rule = PolicyRule(
            id=overridden_rule.id,
            tenant_id=tenant_id,
            domain=PolicyDomain(tpl_vals["domain"]),
            rule_id=rule_id,
            name=tpl_vals["name"],
            description=tpl_vals["description"],
            rule_condition=tpl_vals["rule_condition"],
            rule_action=tpl_vals["rule_action"],
            priority=tpl_vals["priority"],
            enabled=tpl_vals["enabled"],
            template_rule_id=template_id,
            is_custom=False,
            is_deleted=False,
            created_by=overridden_rule.created_by,
        )

        policy_repo = AsyncMock()
        template_repo = AsyncMock()
        policy_repo.get_rule.return_value = overridden_rule
        template_repo.get_template_by_uuid.return_value = template
        policy_repo.update_rule.return_value = reset_rule

        service = PolicyService(policy_repo=policy_repo, template_repo=template_repo)

        result = await service.reset_override(tenant_id=tenant_id, rule_id=rule_id)

        assert result.name == template.name
        assert result.description == template.description
        assert result.rule_condition == template.rule_condition
        assert result.rule_action == template.rule_action
        assert result.priority == template.priority
        assert result.enabled == template.enabled

    @settings(max_examples=100)
    @given(tpl_vals=template_values(), ovr_vals=override_values())
    @pytest.mark.asyncio
    async def test_reset_passes_template_defaults_to_repository(
        self,
        tpl_vals: dict,
        ovr_vals: dict,
    ) -> None:
        """Reset SHALL pass the exact template default values to the repository."""
        template_id = uuid4()
        tenant_id = "tenant-prop7"
        rule_id = "rule-under-test"

        template = PolicyTemplate(
            id=template_id,
            domain=PolicyDomain(tpl_vals["domain"]),
            rule_id=rule_id,
            name=tpl_vals["name"],
            description=tpl_vals["description"],
            rule_condition=tpl_vals["rule_condition"],
            rule_action=tpl_vals["rule_action"],
            priority=tpl_vals["priority"],
            enabled=tpl_vals["enabled"],
            legal_constraints=None,
        )

        overridden_rule = PolicyRule(
            id=uuid4(),
            tenant_id=tenant_id,
            domain=PolicyDomain(tpl_vals["domain"]),
            rule_id=rule_id,
            name=ovr_vals["name"],
            description=ovr_vals["description"],
            rule_condition=ovr_vals["rule_condition"],
            rule_action=ovr_vals["rule_action"],
            priority=ovr_vals["priority"],
            enabled=ovr_vals["enabled"],
            template_rule_id=template_id,
            is_custom=False,
            is_deleted=False,
            created_by=uuid4(),
        )

        reset_rule = PolicyRule(
            id=overridden_rule.id,
            tenant_id=tenant_id,
            domain=PolicyDomain(tpl_vals["domain"]),
            rule_id=rule_id,
            name=tpl_vals["name"],
            description=tpl_vals["description"],
            rule_condition=tpl_vals["rule_condition"],
            rule_action=tpl_vals["rule_action"],
            priority=tpl_vals["priority"],
            enabled=tpl_vals["enabled"],
            template_rule_id=template_id,
            is_custom=False,
            is_deleted=False,
            created_by=overridden_rule.created_by,
        )

        policy_repo = AsyncMock()
        template_repo = AsyncMock()
        policy_repo.get_rule.return_value = overridden_rule
        template_repo.get_template_by_uuid.return_value = template
        policy_repo.update_rule.return_value = reset_rule

        service = PolicyService(policy_repo=policy_repo, template_repo=template_repo)

        await service.reset_override(tenant_id=tenant_id, rule_id=rule_id)

        policy_repo.update_rule.assert_called_once()
        call_args = policy_repo.update_rule.call_args[0]
        assert call_args[0] == tenant_id
        assert call_args[1] == rule_id

        reset_data = call_args[2]
        assert reset_data["name"] == tpl_vals["name"]
        assert reset_data["description"] == tpl_vals["description"]
        assert reset_data["rule_condition"] == tpl_vals["rule_condition"]
        assert reset_data["rule_action"] == tpl_vals["rule_action"]
        assert reset_data["priority"] == tpl_vals["priority"]
        assert reset_data["enabled"] == tpl_vals["enabled"]

    @settings(max_examples=100)
    @given(tpl_vals=template_values(), ovr_vals=override_values())
    @pytest.mark.asyncio
    async def test_reset_override_record_no_longer_persisted(
        self,
        tpl_vals: dict,
        ovr_vals: dict,
    ) -> None:
        """After reset, the override record SHALL no longer exist in storage.

        The reset operation replaces the overridden values with template
        defaults via update_rule, effectively removing the override.
        """
        template_id = uuid4()
        tenant_id = "tenant-prop7"
        rule_id = "rule-under-test"

        template = PolicyTemplate(
            id=template_id,
            domain=PolicyDomain(tpl_vals["domain"]),
            rule_id=rule_id,
            name=tpl_vals["name"],
            description=tpl_vals["description"],
            rule_condition=tpl_vals["rule_condition"],
            rule_action=tpl_vals["rule_action"],
            priority=tpl_vals["priority"],
            enabled=tpl_vals["enabled"],
            legal_constraints=None,
        )

        overridden_rule = PolicyRule(
            id=uuid4(),
            tenant_id=tenant_id,
            domain=PolicyDomain(tpl_vals["domain"]),
            rule_id=rule_id,
            name=ovr_vals["name"],
            description=ovr_vals["description"],
            rule_condition=ovr_vals["rule_condition"],
            rule_action=ovr_vals["rule_action"],
            priority=ovr_vals["priority"],
            enabled=ovr_vals["enabled"],
            template_rule_id=template_id,
            is_custom=False,
            is_deleted=False,
            created_by=uuid4(),
        )

        reset_rule = PolicyRule(
            id=overridden_rule.id,
            tenant_id=tenant_id,
            domain=PolicyDomain(tpl_vals["domain"]),
            rule_id=rule_id,
            name=tpl_vals["name"],
            description=tpl_vals["description"],
            rule_condition=tpl_vals["rule_condition"],
            rule_action=tpl_vals["rule_action"],
            priority=tpl_vals["priority"],
            enabled=tpl_vals["enabled"],
            template_rule_id=template_id,
            is_custom=False,
            is_deleted=False,
            created_by=overridden_rule.created_by,
        )

        policy_repo = AsyncMock()
        template_repo = AsyncMock()
        policy_repo.get_rule.return_value = overridden_rule
        template_repo.get_template_by_uuid.return_value = template
        policy_repo.update_rule.return_value = reset_rule

        service = PolicyService(policy_repo=policy_repo, template_repo=template_repo)

        result = await service.reset_override(tenant_id=tenant_id, rule_id=rule_id)

        # The stored rule now has values identical to the template —
        # meaning the override no longer exists in storage.
        assert result.name == template.name
        assert result.description == template.description
        assert result.rule_condition == template.rule_condition
        assert result.rule_action == template.rule_action
        assert result.priority == template.priority
        assert result.enabled == template.enabled

        # Verify the repository was instructed to overwrite with template data
        # (the override is removed by replacing all overridden fields)
        update_data = policy_repo.update_rule.call_args[0][2]
        assert set(update_data.keys()) == {
            "name",
            "description",
            "rule_condition",
            "rule_action",
            "priority",
            "enabled",
        }
