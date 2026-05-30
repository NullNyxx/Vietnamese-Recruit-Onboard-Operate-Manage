"""Unit tests for TemplateRepository using mocked AsyncSession.

Tests read-only query methods for PolicyTemplate retrieval
by domain and rule_id.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.modules.policy.domain.entities import PolicyTemplate
from src.modules.policy.domain.enums import PolicyDomain
from src.modules.policy.infrastructure.template_repository import TemplateRepository


def _make_mock_session(query_result=None):
    """Create a mock AsyncSession that returns the given query result."""
    session = AsyncMock()
    scalars_mock = MagicMock()

    if isinstance(query_result, list):
        scalars_mock.all.return_value = query_result
    else:
        scalars_mock.first.return_value = query_result

    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    session.execute.return_value = result_mock
    return session


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


class TestGetAllTemplates:
    """Tests for TemplateRepository.get_all_templates."""

    async def test_returns_empty_list_when_no_templates(self) -> None:
        session = _make_mock_session(query_result=[])
        repo = TemplateRepository(session)

        result = await repo.get_all_templates()

        assert result == []
        session.execute.assert_called_once()

    async def test_returns_all_templates(self) -> None:
        templates = [
            _make_template(domain=PolicyDomain.ATTENDANCE, rule_id="ATT-001"),
            _make_template(domain=PolicyDomain.LEAVE, rule_id="LV-001"),
            _make_template(domain=PolicyDomain.OVERTIME, rule_id="OT-001"),
        ]
        session = _make_mock_session(query_result=templates)
        repo = TemplateRepository(session)

        result = await repo.get_all_templates()

        assert len(result) == 3
        assert result[0].rule_id == "ATT-001"
        assert result[1].rule_id == "LV-001"
        assert result[2].rule_id == "OT-001"


class TestGetTemplatesByDomain:
    """Tests for TemplateRepository.get_templates_by_domain."""

    async def test_returns_empty_list_when_no_templates_in_domain(self) -> None:
        session = _make_mock_session(query_result=[])
        repo = TemplateRepository(session)

        result = await repo.get_templates_by_domain(PolicyDomain.DISCIPLINARY)

        assert result == []
        session.execute.assert_called_once()

    async def test_returns_templates_for_given_domain(self) -> None:
        templates = [
            _make_template(domain=PolicyDomain.ATTENDANCE, rule_id="ATT-001", priority=100),
            _make_template(domain=PolicyDomain.ATTENDANCE, rule_id="ATT-002", priority=200),
        ]
        session = _make_mock_session(query_result=templates)
        repo = TemplateRepository(session)

        result = await repo.get_templates_by_domain(PolicyDomain.ATTENDANCE)

        assert len(result) == 2
        assert all(t.domain == PolicyDomain.ATTENDANCE for t in result)


class TestGetTemplate:
    """Tests for TemplateRepository.get_template."""

    async def test_returns_none_when_template_not_found(self) -> None:
        session = _make_mock_session(query_result=None)
        repo = TemplateRepository(session)

        result = await repo.get_template("NONEXISTENT-001")

        assert result is None
        session.execute.assert_called_once()

    async def test_returns_template_when_found(self) -> None:
        template = _make_template(rule_id="ATT-001")
        session = _make_mock_session(query_result=template)
        repo = TemplateRepository(session)

        result = await repo.get_template("ATT-001")

        assert result is not None
        assert result.rule_id == "ATT-001"
        assert result.name == "Late Threshold"
        assert result.domain == PolicyDomain.ATTENDANCE
