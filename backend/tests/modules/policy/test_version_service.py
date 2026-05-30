"""Unit tests for VersionService.

Tests publish, diff, and rollback operations including snapshot creation,
version number monotonicity, cache invalidation, and audit logging.
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.modules.policy.application.version_service import VersionDiffResult, VersionService
from src.modules.policy.domain.entities import PolicyRule, PolicyVersion
from src.modules.policy.domain.enums import PolicyDomain
from src.modules.policy.domain.exceptions import PolicyVersionNotFoundError


def _make_rule(
    rule_id: str = "ATT-001",
    domain: PolicyDomain = PolicyDomain.ATTENDANCE,
    name: str = "Late Threshold",
    priority: int = 100,
    enabled: bool = True,
    is_custom: bool = False,
    template_rule_id=None,
) -> PolicyRule:
    """Create a PolicyRule entity for testing."""
    return PolicyRule(
        id=uuid4(),
        tenant_id="tenant-001",
        domain=domain,
        rule_id=rule_id,
        name=name,
        description=f"Test rule {name}",
        rule_condition={"field": "check_in_time", "operator": "greater_than", "value": 15},
        rule_action={"type": "flag", "parameters": {"status": "late"}},
        priority=priority,
        enabled=enabled,
        is_custom=is_custom,
        template_rule_id=template_rule_id,
        is_deleted=False,
        created_by=uuid4(),
    )


def _make_version(
    tenant_id: str = "tenant-001",
    version_number: int = 1,
    rules: list[dict] | None = None,
) -> PolicyVersion:
    """Create a PolicyVersion entity for testing."""
    snapshot = {"rules": rules or []}
    return PolicyVersion(
        id=uuid4(),
        tenant_id=tenant_id,
        version_number=version_number,
        snapshot=snapshot,
        change_summary="Test version",
        rules_added=len(rules) if rules else 0,
        rules_removed=0,
        rules_modified=0,
        effective_date=date(2024, 1, 1),
        published_by=uuid4(),
    )


def _make_service() -> tuple[VersionService, AsyncMock, AsyncMock, AsyncMock]:
    """Create a VersionService with mocked dependencies.

    Returns:
        Tuple of (service, policy_repo_mock, version_repo_mock, cache_mock).
    """
    policy_repo = AsyncMock()
    # session.add is synchronous in SQLAlchemy; use MagicMock to avoid warnings
    session_mock = MagicMock()
    session_mock.flush = AsyncMock()
    policy_repo.session = session_mock

    version_repo = AsyncMock()
    version_repo.create_version.side_effect = lambda v: v

    cache_client = AsyncMock()

    service = VersionService(
        policy_repository=policy_repo,
        version_repository=version_repo,
        cache_client=cache_client,
    )
    return service, policy_repo, version_repo, cache_client


class TestPublish:
    """Tests for VersionService.publish."""

    async def test_creates_first_version_with_number_1(self) -> None:
        """First publish for a tenant creates version number 1."""
        service, policy_repo, version_repo, _ = _make_service()
        policy_repo.get_rules_by_tenant.return_value = [_make_rule()]
        version_repo.get_latest_version_number.return_value = None

        result = await service.publish("tenant-001", uuid4(), date(2024, 6, 1), "Initial")

        assert result.version_number == 1

    async def test_increments_version_number(self) -> None:
        """Subsequent publishes increment the version number."""
        service, policy_repo, version_repo, _ = _make_service()
        policy_repo.get_rules_by_tenant.return_value = [_make_rule()]
        version_repo.get_latest_version_number.return_value = 3
        version_repo.get_version.return_value = _make_version(version_number=3)

        result = await service.publish("tenant-001", uuid4(), date(2024, 6, 1), "Update")

        assert result.version_number == 4

    async def test_snapshot_contains_all_rules(self) -> None:
        """Snapshot includes all active rules for the tenant."""
        service, policy_repo, version_repo, _ = _make_service()
        rules = [_make_rule(rule_id="ATT-001"), _make_rule(rule_id="LV-001")]
        policy_repo.get_rules_by_tenant.return_value = rules
        version_repo.get_latest_version_number.return_value = None

        result = await service.publish("tenant-001", uuid4(), date(2024, 6, 1), "Initial")

        assert len(result.snapshot["rules"]) == 2
        rule_ids = {r["rule_id"] for r in result.snapshot["rules"]}
        assert rule_ids == {"ATT-001", "LV-001"}

    async def test_invalidates_cache(self) -> None:
        """Publish invalidates the Redis cache for the tenant."""
        service, policy_repo, version_repo, cache = _make_service()
        policy_repo.get_rules_by_tenant.return_value = []
        version_repo.get_latest_version_number.return_value = None

        await service.publish("tenant-001", uuid4(), date(2024, 6, 1), "Initial")

        cache.invalidate.assert_called_once_with("tenant-001")

    async def test_creates_audit_log(self) -> None:
        """Publish creates an audit log entry."""
        service, policy_repo, version_repo, _ = _make_service()
        policy_repo.get_rules_by_tenant.return_value = []
        version_repo.get_latest_version_number.return_value = None
        user_id = uuid4()

        await service.publish("tenant-001", user_id, date(2024, 6, 1), "Initial publish")

        # Verify session.add was called (for the audit log)
        policy_repo.session.add.assert_called_once()
        audit_log = policy_repo.session.add.call_args[0][0]
        assert audit_log.tenant_id == "tenant-001"
        assert audit_log.user_id == user_id
        assert audit_log.action_type == "version_published"
        assert audit_log.details["version_number"] == 1
        assert audit_log.details["change_summary"] == "Initial publish"

    async def test_uses_today_when_no_effective_date(self) -> None:
        """Defaults to today's date when effective_date is None."""
        service, policy_repo, version_repo, _ = _make_service()
        policy_repo.get_rules_by_tenant.return_value = []
        version_repo.get_latest_version_number.return_value = None

        result = await service.publish("tenant-001", uuid4(), None, "No date")

        assert result.effective_date == date.today()

    async def test_first_version_all_rules_counted_as_added(self) -> None:
        """First version counts all rules as added."""
        service, policy_repo, version_repo, _ = _make_service()
        rules = [_make_rule(rule_id="R1"), _make_rule(rule_id="R2"), _make_rule(rule_id="R3")]
        policy_repo.get_rules_by_tenant.return_value = rules
        version_repo.get_latest_version_number.return_value = None

        result = await service.publish("tenant-001", uuid4(), date(2024, 6, 1), "Initial")

        assert result.rules_added == 3
        assert result.rules_removed == 0
        assert result.rules_modified == 0


class TestDiff:
    """Tests for VersionService.diff."""

    async def test_identifies_added_rules(self) -> None:
        """Rules in version B but not A are categorized as added."""
        service, _, version_repo, _ = _make_service()
        ver_a = _make_version(version_number=1, rules=[])
        ver_b = _make_version(
            version_number=2,
            rules=[{"rule_id": "NEW-001", "name": "New Rule", "domain": "attendance",
                    "description": "desc", "rule_condition": {}, "rule_action": {},
                    "priority": 100, "enabled": True, "is_custom": False,
                    "template_rule_id": None, "id": str(uuid4())}],
        )
        version_repo.get_version.side_effect = [ver_a, ver_b]

        result = await service.diff("tenant-001", 1, 2)

        assert len(result.added) == 1
        assert result.added[0]["rule_id"] == "NEW-001"
        assert len(result.removed) == 0
        assert len(result.modified) == 0

    async def test_identifies_removed_rules(self) -> None:
        """Rules in version A but not B are categorized as removed."""
        service, _, version_repo, _ = _make_service()
        rule_dict = {"rule_id": "OLD-001", "name": "Old Rule", "domain": "attendance",
                     "description": "desc", "rule_condition": {}, "rule_action": {},
                     "priority": 100, "enabled": True, "is_custom": False,
                     "template_rule_id": None, "id": str(uuid4())}
        ver_a = _make_version(version_number=1, rules=[rule_dict])
        ver_b = _make_version(version_number=2, rules=[])
        version_repo.get_version.side_effect = [ver_a, ver_b]

        result = await service.diff("tenant-001", 1, 2)

        assert len(result.removed) == 1
        assert result.removed[0]["rule_id"] == "OLD-001"
        assert len(result.added) == 0

    async def test_identifies_modified_rules(self) -> None:
        """Rules present in both but with different values are modified."""
        service, _, version_repo, _ = _make_service()
        rule_a = {"rule_id": "ATT-001", "name": "Late Threshold", "domain": "attendance",
                  "description": "desc", "rule_condition": {"field": "x", "operator": "gt",
                  "value": 15}, "rule_action": {}, "priority": 100, "enabled": True,
                  "is_custom": False, "template_rule_id": None, "id": str(uuid4())}
        rule_b = {**rule_a, "priority": 200}  # Changed priority
        ver_a = _make_version(version_number=1, rules=[rule_a])
        ver_b = _make_version(version_number=2, rules=[rule_b])
        version_repo.get_version.side_effect = [ver_a, ver_b]

        result = await service.diff("tenant-001", 1, 2)

        assert len(result.modified) == 1
        assert result.modified[0]["rule_id"] == "ATT-001"
        assert result.modified[0]["before"]["priority"] == 100
        assert result.modified[0]["after"]["priority"] == 200

    async def test_identifies_unchanged_rules(self) -> None:
        """Rules identical in both versions are categorized as unchanged."""
        service, _, version_repo, _ = _make_service()
        rule = {"rule_id": "ATT-001", "name": "Late Threshold", "domain": "attendance",
                "description": "desc", "rule_condition": {}, "rule_action": {},
                "priority": 100, "enabled": True, "is_custom": False,
                "template_rule_id": None, "id": str(uuid4())}
        ver_a = _make_version(version_number=1, rules=[rule])
        ver_b = _make_version(version_number=2, rules=[rule])
        version_repo.get_version.side_effect = [ver_a, ver_b]

        result = await service.diff("tenant-001", 1, 2)

        assert len(result.unchanged) == 1
        assert len(result.added) == 0
        assert len(result.removed) == 0
        assert len(result.modified) == 0

    async def test_raises_error_for_nonexistent_version_a(self) -> None:
        """Raises PolicyVersionNotFoundError if version A doesn't exist."""
        service, _, version_repo, _ = _make_service()
        version_repo.get_version.return_value = None

        with pytest.raises(PolicyVersionNotFoundError):
            await service.diff("tenant-001", 99, 1)

    async def test_raises_error_for_nonexistent_version_b(self) -> None:
        """Raises PolicyVersionNotFoundError if version B doesn't exist."""
        service, _, version_repo, _ = _make_service()
        ver_a = _make_version(version_number=1, rules=[])
        version_repo.get_version.side_effect = [ver_a, None]

        with pytest.raises(PolicyVersionNotFoundError):
            await service.diff("tenant-001", 1, 99)


class TestRollback:
    """Tests for VersionService.rollback."""

    async def test_creates_new_version_with_target_snapshot(self) -> None:
        """Rollback creates a new version with the target's snapshot."""
        service, policy_repo, version_repo, _ = _make_service()
        target_rules = [{"rule_id": "ATT-001", "name": "Late", "domain": "attendance",
                         "description": "d", "rule_condition": {}, "rule_action": {},
                         "priority": 100, "enabled": True, "is_custom": False,
                         "template_rule_id": None, "id": str(uuid4())}]
        target = _make_version(version_number=2, rules=target_rules)
        version_repo.get_version.return_value = target
        version_repo.get_latest_version_number.return_value = 5

        result = await service.rollback("tenant-001", 2, uuid4())

        assert result.snapshot == target.snapshot
        assert result.version_number == 6

    async def test_rollback_invalidates_cache(self) -> None:
        """Rollback invalidates the Redis cache."""
        service, _, version_repo, cache = _make_service()
        target = _make_version(version_number=1, rules=[])
        version_repo.get_version.return_value = target
        version_repo.get_latest_version_number.return_value = 3

        await service.rollback("tenant-001", 1, uuid4())

        cache.invalidate.assert_called_once_with("tenant-001")

    async def test_rollback_creates_audit_log(self) -> None:
        """Rollback creates an audit log entry with rollback action type."""
        service, policy_repo, version_repo, _ = _make_service()
        target = _make_version(version_number=2, rules=[])
        version_repo.get_version.return_value = target
        version_repo.get_latest_version_number.return_value = 4
        user_id = uuid4()

        await service.rollback("tenant-001", 2, user_id)

        policy_repo.session.add.assert_called_once()
        audit_log = policy_repo.session.add.call_args[0][0]
        assert audit_log.action_type == "version_rollback"
        assert audit_log.details["target_version"] == 2
        assert audit_log.user_id == user_id

    async def test_raises_error_for_nonexistent_target(self) -> None:
        """Raises PolicyVersionNotFoundError if target version doesn't exist."""
        service, _, version_repo, _ = _make_service()
        version_repo.get_version.return_value = None

        with pytest.raises(PolicyVersionNotFoundError):
            await service.rollback("tenant-001", 99, uuid4())


class TestVersionDiffResult:
    """Tests for VersionDiffResult.to_dict."""

    def test_to_dict_includes_counts(self) -> None:
        """to_dict includes count fields for each category."""
        result = VersionDiffResult(
            added=[{"rule_id": "A"}],
            removed=[{"rule_id": "B"}, {"rule_id": "C"}],
            modified=[],
            unchanged=[{"rule_id": "D"}],
        )

        d = result.to_dict()

        assert d["rules_added"] == 1
        assert d["rules_removed"] == 2
        assert d["rules_modified"] == 0
        assert d["rules_unchanged"] == 1
