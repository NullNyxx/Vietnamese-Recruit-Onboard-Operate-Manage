"""Tests for PolicyService CRUD operations.

Tests create_custom_rule, update_rule, disable_rule, and reset_override
methods with enforcement of legal minimums, type validation, and
custom rule limits.
"""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.modules.policy.application.policy_service import PolicyService
from src.modules.policy.domain.entities import PolicyRule, PolicyTemplate
from src.modules.policy.domain.enums import PolicyDomain
from src.modules.policy.domain.exceptions import (
    CustomRuleLimitError,
    CustomRuleResetError,
    LegalMinimumViolationError,
    PolicyRuleNotFoundError,
    PolicyValidationError,
)


def _valid_rule_data() -> dict:
    """Return a minimal valid PolicyRule dict for creation."""
    return {
        "rule_id": "custom-late-threshold",
        "domain": "attendance",
        "name": "Custom Late Threshold",
        "description": "Custom rule for late threshold.",
        "rule_condition": {
            "field": "minutes_late",
            "operator": "greater_than",
            "value": 20,
        },
        "rule_action": {
            "type": "flag",
            "parameters": {"status": "late"},
        },
        "priority": 100,
        "enabled": True,
    }


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


def _make_template(*, legal_constraints=None) -> PolicyTemplate:
    """Create a PolicyTemplate instance for testing."""
    return PolicyTemplate(
        id=uuid4(),
        domain=PolicyDomain.ATTENDANCE,
        rule_id="attendance-late-threshold",
        name="Late Threshold",
        description="Default late threshold rule",
        rule_condition={"field": "minutes_late", "operator": "greater_than", "value": 15},
        rule_action={"type": "flag", "parameters": {"status": "late"}},
        priority=100,
        enabled=True,
        legal_constraints=legal_constraints,
    )


@pytest.fixture
def policy_repo() -> AsyncMock:
    """Create a mock PolicyRepository."""
    return AsyncMock()


@pytest.fixture
def template_repo() -> AsyncMock:
    """Create a mock TemplateRepository."""
    return AsyncMock()


@pytest.fixture
def service(policy_repo: AsyncMock, template_repo: AsyncMock) -> PolicyService:
    """Create a PolicyService with mocked repositories."""
    return PolicyService(policy_repo=policy_repo, template_repo=template_repo)


class TestCreateCustomRule:
    """Tests for PolicyService.create_custom_rule."""

    @pytest.mark.asyncio
    async def test_creates_custom_rule_successfully(
        self, service: PolicyService, policy_repo: AsyncMock
    ) -> None:
        policy_repo.count_custom_rules.return_value = 0
        policy_repo.create_rule.return_value = _make_policy_rule(is_custom=True)

        result = await service.create_custom_rule(
            tenant_id="tenant-001",
            rule_data=_valid_rule_data(),
            user_id=uuid4(),
        )

        assert result.is_custom is True
        policy_repo.create_rule.assert_called_once()

    @pytest.mark.asyncio
    async def test_enforces_500_custom_rule_limit(
        self, service: PolicyService, policy_repo: AsyncMock
    ) -> None:
        policy_repo.count_custom_rules.return_value = 500

        with pytest.raises(CustomRuleLimitError):
            await service.create_custom_rule(
                tenant_id="tenant-001",
                rule_data=_valid_rule_data(),
                user_id=uuid4(),
            )

    @pytest.mark.asyncio
    async def test_validates_rule_structure(
        self, service: PolicyService, policy_repo: AsyncMock
    ) -> None:
        invalid_data = {"rule_id": "test"}  # Missing required fields

        with pytest.raises(PolicyValidationError):
            await service.create_custom_rule(
                tenant_id="tenant-001",
                rule_data=invalid_data,
                user_id=uuid4(),
            )

    @pytest.mark.asyncio
    async def test_allows_creation_at_499_rules(
        self, service: PolicyService, policy_repo: AsyncMock
    ) -> None:
        policy_repo.count_custom_rules.return_value = 499
        policy_repo.create_rule.return_value = _make_policy_rule(is_custom=True)

        result = await service.create_custom_rule(
            tenant_id="tenant-001",
            rule_data=_valid_rule_data(),
            user_id=uuid4(),
        )

        assert result is not None


class TestUpdateRule:
    """Tests for PolicyService.update_rule."""

    @pytest.mark.asyncio
    async def test_updates_custom_rule_directly(
        self, service: PolicyService, policy_repo: AsyncMock
    ) -> None:
        rule = _make_policy_rule(is_custom=True)
        policy_repo.get_rule.return_value = rule
        policy_repo.update_rule.return_value = rule

        result = await service.update_rule(
            tenant_id="tenant-001",
            rule_id="test-rule",
            updates={"name": "Updated Name"},
            user_id=uuid4(),
        )

        assert result is not None
        policy_repo.update_rule.assert_called_once()

    @pytest.mark.asyncio
    async def test_updates_template_rule_with_legal_check(
        self, service: PolicyService, policy_repo: AsyncMock, template_repo: AsyncMock
    ) -> None:
        template_id = uuid4()
        rule = _make_policy_rule(is_custom=False, template_rule_id=template_id)
        template = _make_template(legal_constraints=None)

        policy_repo.get_rule.return_value = rule
        policy_repo.update_rule.return_value = rule
        template_repo.get_template_by_uuid.return_value = template

        result = await service.update_rule(
            tenant_id="tenant-001",
            rule_id="test-rule",
            updates={"priority": 200},
            user_id=uuid4(),
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_raises_not_found_for_missing_rule(
        self, service: PolicyService, policy_repo: AsyncMock
    ) -> None:
        policy_repo.get_rule.return_value = None

        with pytest.raises(PolicyRuleNotFoundError):
            await service.update_rule(
                tenant_id="tenant-001",
                rule_id="nonexistent",
                updates={"name": "New Name"},
                user_id=uuid4(),
            )

    @pytest.mark.asyncio
    async def test_rejects_invalid_type_for_priority(
        self, service: PolicyService, policy_repo: AsyncMock
    ) -> None:
        rule = _make_policy_rule(is_custom=True)
        policy_repo.get_rule.return_value = rule

        with pytest.raises(PolicyValidationError):
            await service.update_rule(
                tenant_id="tenant-001",
                rule_id="test-rule",
                updates={"priority": "not_an_int"},
                user_id=uuid4(),
            )

    @pytest.mark.asyncio
    async def test_rejects_invalid_type_for_enabled(
        self, service: PolicyService, policy_repo: AsyncMock
    ) -> None:
        rule = _make_policy_rule(is_custom=True)
        policy_repo.get_rule.return_value = rule

        with pytest.raises(PolicyValidationError):
            await service.update_rule(
                tenant_id="tenant-001",
                rule_id="test-rule",
                updates={"enabled": "yes"},
                user_id=uuid4(),
            )

    @pytest.mark.asyncio
    async def test_enforces_legal_minimum_on_condition_value(
        self, service: PolicyService, policy_repo: AsyncMock, template_repo: AsyncMock
    ) -> None:
        template_id = uuid4()
        rule = _make_policy_rule(is_custom=False, template_rule_id=template_id)
        template = _make_template(legal_constraints={"min_value": 150})

        policy_repo.get_rule.return_value = rule
        template_repo.get_template_by_uuid.return_value = template

        with pytest.raises(LegalMinimumViolationError):
            await service.update_rule(
                tenant_id="tenant-001",
                rule_id="test-rule",
                updates={
                    "rule_condition": {
                        "field": "multiplier",
                        "operator": "greater_than_or_equal",
                        "value": 100,  # Below legal minimum of 150
                    }
                },
                user_id=uuid4(),
            )

    @pytest.mark.asyncio
    async def test_enforces_legal_minimum_on_action_params(
        self, service: PolicyService, policy_repo: AsyncMock, template_repo: AsyncMock
    ) -> None:
        template_id = uuid4()
        rule = _make_policy_rule(is_custom=False, template_rule_id=template_id)
        template = _make_template(
            legal_constraints={"min_values": {"multiplier": 150}}
        )

        policy_repo.get_rule.return_value = rule
        template_repo.get_template_by_uuid.return_value = template

        with pytest.raises(LegalMinimumViolationError):
            await service.update_rule(
                tenant_id="tenant-001",
                rule_id="test-rule",
                updates={
                    "rule_action": {
                        "type": "calculate",
                        "parameters": {"multiplier": 100},  # Below min 150
                    }
                },
                user_id=uuid4(),
            )

    @pytest.mark.asyncio
    async def test_allows_value_at_legal_minimum(
        self, service: PolicyService, policy_repo: AsyncMock, template_repo: AsyncMock
    ) -> None:
        template_id = uuid4()
        rule = _make_policy_rule(is_custom=False, template_rule_id=template_id)
        template = _make_template(legal_constraints={"min_value": 150})

        policy_repo.get_rule.return_value = rule
        policy_repo.update_rule.return_value = rule
        template_repo.get_template_by_uuid.return_value = template

        result = await service.update_rule(
            tenant_id="tenant-001",
            rule_id="test-rule",
            updates={
                "rule_condition": {
                    "field": "multiplier",
                    "operator": "greater_than_or_equal",
                    "value": 150,  # Exactly at legal minimum
                }
            },
            user_id=uuid4(),
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_ignores_non_updatable_fields(
        self, service: PolicyService, policy_repo: AsyncMock
    ) -> None:
        rule = _make_policy_rule(is_custom=True)
        policy_repo.get_rule.return_value = rule

        # Passing only non-updatable fields should return rule unchanged
        result = await service.update_rule(
            tenant_id="tenant-001",
            rule_id="test-rule",
            updates={"rule_id": "new-id", "tenant_id": "other"},
            user_id=uuid4(),
        )

        assert result == rule
        policy_repo.update_rule.assert_not_called()


class TestDisableRule:
    """Tests for PolicyService.disable_rule."""

    @pytest.mark.asyncio
    async def test_soft_deletes_custom_rule(
        self, service: PolicyService, policy_repo: AsyncMock
    ) -> None:
        rule = _make_policy_rule(is_custom=True)
        policy_repo.get_rule.return_value = rule
        deleted_rule = _make_policy_rule(is_custom=True)
        deleted_rule.is_deleted = True
        policy_repo.soft_delete_rule.return_value = deleted_rule

        result = await service.disable_rule(
            tenant_id="tenant-001",
            rule_id="test-rule",
        )

        assert result.is_deleted is True
        policy_repo.soft_delete_rule.assert_called_once_with("tenant-001", "test-rule")

    @pytest.mark.asyncio
    async def test_disables_template_rule(
        self, service: PolicyService, policy_repo: AsyncMock
    ) -> None:
        template_id = uuid4()
        rule = _make_policy_rule(is_custom=False, template_rule_id=template_id)
        disabled_rule = _make_policy_rule(is_custom=False, template_rule_id=template_id)
        disabled_rule.enabled = False

        policy_repo.get_rule.return_value = rule
        policy_repo.update_rule.return_value = disabled_rule

        result = await service.disable_rule(
            tenant_id="tenant-001",
            rule_id="test-rule",
        )

        assert result.enabled is False
        policy_repo.update_rule.assert_called_once_with(
            "tenant-001", "test-rule", {"enabled": False}
        )

    @pytest.mark.asyncio
    async def test_raises_not_found_for_missing_rule(
        self, service: PolicyService, policy_repo: AsyncMock
    ) -> None:
        policy_repo.get_rule.return_value = None

        with pytest.raises(PolicyRuleNotFoundError):
            await service.disable_rule(
                tenant_id="tenant-001",
                rule_id="nonexistent",
            )


class TestResetOverride:
    """Tests for PolicyService.reset_override."""

    @pytest.mark.asyncio
    async def test_resets_template_rule_to_defaults(
        self, service: PolicyService, policy_repo: AsyncMock, template_repo: AsyncMock
    ) -> None:
        template_id = uuid4()
        rule = _make_policy_rule(is_custom=False, template_rule_id=template_id)
        rule.name = "Overridden Name"
        rule.priority = 500

        template = _make_template()
        template.id = template_id

        policy_repo.get_rule.return_value = rule
        template_repo.get_template_by_uuid.return_value = template

        reset_rule = _make_policy_rule(is_custom=False, template_rule_id=template_id)
        reset_rule.name = template.name
        reset_rule.priority = template.priority
        policy_repo.update_rule.return_value = reset_rule

        result = await service.reset_override(
            tenant_id="tenant-001",
            rule_id="test-rule",
        )

        assert result.name == template.name
        policy_repo.update_rule.assert_called_once()
        call_args = policy_repo.update_rule.call_args
        reset_data = call_args[0][2]
        assert reset_data["name"] == template.name
        assert reset_data["description"] == template.description
        assert reset_data["priority"] == template.priority
        assert reset_data["enabled"] == template.enabled

    @pytest.mark.asyncio
    async def test_rejects_reset_for_custom_rule(
        self, service: PolicyService, policy_repo: AsyncMock
    ) -> None:
        rule = _make_policy_rule(is_custom=True)
        policy_repo.get_rule.return_value = rule

        with pytest.raises(CustomRuleResetError):
            await service.reset_override(
                tenant_id="tenant-001",
                rule_id="test-rule",
            )

    @pytest.mark.asyncio
    async def test_raises_not_found_for_missing_rule(
        self, service: PolicyService, policy_repo: AsyncMock
    ) -> None:
        policy_repo.get_rule.return_value = None

        with pytest.raises(PolicyRuleNotFoundError):
            await service.reset_override(
                tenant_id="tenant-001",
                rule_id="nonexistent",
            )

    @pytest.mark.asyncio
    async def test_raises_error_when_template_not_found(
        self, service: PolicyService, policy_repo: AsyncMock, template_repo: AsyncMock
    ) -> None:
        template_id = uuid4()
        rule = _make_policy_rule(is_custom=False, template_rule_id=template_id)

        policy_repo.get_rule.return_value = rule
        template_repo.get_template_by_uuid.return_value = None

        with pytest.raises(PolicyRuleNotFoundError):
            await service.reset_override(
                tenant_id="tenant-001",
                rule_id="test-rule",
            )
