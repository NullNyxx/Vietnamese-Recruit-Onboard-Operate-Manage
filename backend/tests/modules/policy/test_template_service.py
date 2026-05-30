"""Unit tests for TemplateService.

Tests template provisioning logic including atomic operations,
error handling, and domain coverage validation.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.modules.policy.application.template_service import TemplateService
from src.modules.policy.domain.entities import PolicyTemplate
from src.modules.policy.domain.enums import PolicyDomain
from src.modules.policy.domain.exceptions import TemplateInitializationError


def _make_template(
    domain: PolicyDomain = PolicyDomain.ATTENDANCE,
    rule_id: str = "ATT-001",
    name: str = "Late Threshold",
    priority: int = 100,
) -> PolicyTemplate:
    """Create a PolicyTemplate entity for testing."""
    return PolicyTemplate(
        id=uuid4(),
        domain=domain,
        rule_id=rule_id,
        name=name,
        description=f"Default {name} rule",
        rule_condition={"field": "check_in_time", "operator": "greater_than", "value": 15},
        rule_action={"type": "flag", "parameters": {"status": "late"}},
        priority=priority,
        enabled=True,
        legal_constraints=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _make_templates_all_domains() -> list[PolicyTemplate]:
    """Create templates covering all four required domains."""
    return [
        _make_template(domain=PolicyDomain.ATTENDANCE, rule_id="ATT-001"),
        _make_template(domain=PolicyDomain.LEAVE, rule_id="LV-001", name="Annual Leave"),
        _make_template(domain=PolicyDomain.OVERTIME, rule_id="OT-001", name="Max Monthly OT"),
        _make_template(domain=PolicyDomain.DISCIPLINARY, rule_id="DISC-001", name="Reprimand"),
    ]


class _AsyncContextManager:
    """A simple async context manager for mocking session.begin_nested()."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False


def _make_service(
    templates: list[PolicyTemplate] | None = None,
    create_rule_side_effect=None,
) -> tuple[TemplateService, AsyncMock, AsyncMock, AsyncMock]:
    """Create a TemplateService with mocked dependencies.

    Returns:
        Tuple of (service, session_mock, template_repo_mock, policy_repo_mock).
    """
    session = MagicMock()
    # In SQLAlchemy 2.0, session.begin_nested() returns an object that
    # supports both `await` and `async with`. We mock it as a plain
    # function returning an async context manager.
    session.begin_nested = MagicMock(return_value=_AsyncContextManager())

    template_repo = AsyncMock()
    template_repo.get_all_templates.return_value = templates or []

    policy_repo = AsyncMock()
    if create_rule_side_effect:
        policy_repo.create_rule.side_effect = create_rule_side_effect
    else:
        # Return the rule passed in (simulating persistence)
        policy_repo.create_rule.side_effect = lambda rule: rule

    service = TemplateService(
        session=session,
        template_repo=template_repo,
        policy_repo=policy_repo,
    )
    return service, session, template_repo, policy_repo


class TestProvisionTemplates:
    """Tests for TemplateService.provision_templates."""

    async def test_provisions_all_templates_successfully(self) -> None:
        """All templates are copied as PolicyRules for the tenant."""
        templates = _make_templates_all_domains()
        service, session, template_repo, policy_repo = _make_service(templates=templates)
        tenant_id = "tenant-001"
        system_user_id = uuid4()

        result = await service.provision_templates(tenant_id, system_user_id)

        assert len(result) == 4
        assert policy_repo.create_rule.call_count == 4
        template_repo.get_all_templates.assert_called_once()

    async def test_created_rules_have_correct_tenant_id(self) -> None:
        """Each created rule is scoped to the correct tenant."""
        templates = _make_templates_all_domains()
        service, _, _, policy_repo = _make_service(templates=templates)
        tenant_id = "tenant-xyz"
        system_user_id = uuid4()

        result = await service.provision_templates(tenant_id, system_user_id)

        for rule in result:
            assert rule.tenant_id == tenant_id

    async def test_created_rules_have_template_rule_id_set(self) -> None:
        """Each created rule links back to its source template."""
        templates = _make_templates_all_domains()
        service, _, _, policy_repo = _make_service(templates=templates)
        tenant_id = "tenant-001"
        system_user_id = uuid4()

        result = await service.provision_templates(tenant_id, system_user_id)

        template_ids = {t.id for t in templates}
        for rule in result:
            assert rule.template_rule_id in template_ids

    async def test_created_rules_are_not_custom(self) -> None:
        """Template-derived rules have is_custom=False."""
        templates = _make_templates_all_domains()
        service, _, _, _ = _make_service(templates=templates)
        tenant_id = "tenant-001"
        system_user_id = uuid4()

        result = await service.provision_templates(tenant_id, system_user_id)

        for rule in result:
            assert rule.is_custom is False

    async def test_created_rules_have_correct_created_by(self) -> None:
        """Each created rule records the system user as creator."""
        templates = _make_templates_all_domains()
        service, _, _, _ = _make_service(templates=templates)
        tenant_id = "tenant-001"
        system_user_id = uuid4()

        result = await service.provision_templates(tenant_id, system_user_id)

        for rule in result:
            assert rule.created_by == system_user_id

    async def test_created_rules_are_not_deleted(self) -> None:
        """Template-derived rules start as not deleted."""
        templates = _make_templates_all_domains()
        service, _, _, _ = _make_service(templates=templates)
        tenant_id = "tenant-001"
        system_user_id = uuid4()

        result = await service.provision_templates(tenant_id, system_user_id)

        for rule in result:
            assert rule.is_deleted is False

    async def test_raises_error_when_no_templates_exist(self) -> None:
        """Raises TemplateInitializationError if no templates in system."""
        service, _, _, _ = _make_service(templates=[])
        tenant_id = "tenant-001"
        system_user_id = uuid4()

        with pytest.raises(TemplateInitializationError, match="No policy templates found"):
            await service.provision_templates(tenant_id, system_user_id)

    async def test_raises_error_when_domain_missing(self) -> None:
        """Raises TemplateInitializationError if not all domains covered."""
        # Only attendance and leave — missing overtime and disciplinary
        templates = [
            _make_template(domain=PolicyDomain.ATTENDANCE, rule_id="ATT-001"),
            _make_template(domain=PolicyDomain.LEAVE, rule_id="LV-001"),
        ]
        service, _, _, _ = _make_service(templates=templates)
        tenant_id = "tenant-001"
        system_user_id = uuid4()

        with pytest.raises(TemplateInitializationError, match="Missing templates for domains"):
            await service.provision_templates(tenant_id, system_user_id)

    async def test_raises_error_on_database_failure(self) -> None:
        """Raises TemplateInitializationError on unexpected DB error."""
        templates = _make_templates_all_domains()
        service, _, _, policy_repo = _make_service(
            templates=templates,
            create_rule_side_effect=RuntimeError("DB connection lost"),
        )
        tenant_id = "tenant-001"
        system_user_id = uuid4()

        with pytest.raises(TemplateInitializationError, match="Failed to initialize"):
            await service.provision_templates(tenant_id, system_user_id)

    async def test_uses_begin_nested_for_atomicity(self) -> None:
        """The operation uses a savepoint (begin_nested) for atomicity."""
        templates = _make_templates_all_domains()
        service, session, _, _ = _make_service(templates=templates)
        tenant_id = "tenant-001"
        system_user_id = uuid4()

        await service.provision_templates(tenant_id, system_user_id)

        session.begin_nested.assert_called_once()

    async def test_copies_rule_condition_from_template(self) -> None:
        """Rule condition is copied verbatim from the template."""
        templates = _make_templates_all_domains()
        service, _, _, _ = _make_service(templates=templates)
        tenant_id = "tenant-001"
        system_user_id = uuid4()

        result = await service.provision_templates(tenant_id, system_user_id)

        for rule, template in zip(result, templates):
            assert rule.rule_condition == template.rule_condition

    async def test_copies_rule_action_from_template(self) -> None:
        """Rule action is copied verbatim from the template."""
        templates = _make_templates_all_domains()
        service, _, _, _ = _make_service(templates=templates)
        tenant_id = "tenant-001"
        system_user_id = uuid4()

        result = await service.provision_templates(tenant_id, system_user_id)

        for rule, template in zip(result, templates):
            assert rule.rule_action == template.rule_action

    async def test_preserves_priority_from_template(self) -> None:
        """Priority values are preserved from the template."""
        templates = _make_templates_all_domains()
        service, _, _, _ = _make_service(templates=templates)
        tenant_id = "tenant-001"
        system_user_id = uuid4()

        result = await service.provision_templates(tenant_id, system_user_id)

        for rule, template in zip(result, templates):
            assert rule.priority == template.priority

    async def test_preserves_enabled_status_from_template(self) -> None:
        """Enabled status is preserved from the template."""
        templates = _make_templates_all_domains()
        service, _, _, _ = _make_service(templates=templates)
        tenant_id = "tenant-001"
        system_user_id = uuid4()

        result = await service.provision_templates(tenant_id, system_user_id)

        for rule, template in zip(result, templates):
            assert rule.enabled == template.enabled
