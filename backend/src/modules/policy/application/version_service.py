"""Version service for the Policy Engine module.

Provides publish, diff, and rollback operations for policy versioning.
Each operation creates an immutable snapshot of the tenant's policy rules,
enabling historical evaluation, auditing, and rollback capabilities.
"""

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from src.modules.policy.domain.entities import (
    PolicyAuditLog,
    PolicyRule,
    PolicyVersion,
)
from src.modules.policy.domain.exceptions import PolicyVersionNotFoundError
from src.modules.policy.infrastructure.cache_client import PolicyCacheClient
from src.modules.policy.infrastructure.policy_repository import PolicyRepository
from src.modules.policy.infrastructure.version_repository import VersionRepository

# ---------------------------------------------------------------------------
# Data structures for diff results
# ---------------------------------------------------------------------------


class VersionDiffResult:
    """Structured result of comparing two policy versions.

    Attributes:
        added: Rules present in version B but not in version A.
        removed: Rules present in version A but not in version B.
        modified: Rules present in both but with different values.
        unchanged: Rules present in both with identical values.
    """

    def __init__(
        self,
        added: list[dict[str, Any]],
        removed: list[dict[str, Any]],
        modified: list[dict[str, Any]],
        unchanged: list[dict[str, Any]],
    ) -> None:
        self.added = added
        self.removed = removed
        self.modified = modified
        self.unchanged = unchanged

    def to_dict(self) -> dict[str, Any]:
        """Serialize the diff result to a dictionary."""
        return {
            "added": self.added,
            "removed": self.removed,
            "modified": self.modified,
            "unchanged": self.unchanged,
            "rules_added": len(self.added),
            "rules_removed": len(self.removed),
            "rules_modified": len(self.modified),
            "rules_unchanged": len(self.unchanged),
        }


# ---------------------------------------------------------------------------
# Version Service
# ---------------------------------------------------------------------------


class VersionService:
    """Manages policy version lifecycle: publish, diff, and rollback.

    Coordinates between PolicyRepository, VersionRepository, and
    PolicyCacheClient to create immutable version snapshots, compare
    versions, and restore previous states.

    Args:
        policy_repository: Repository for accessing tenant policy rules.
        version_repository: Repository for policy version persistence.
        cache_client: Redis cache client for invalidation on publish.
    """

    def __init__(
        self,
        policy_repository: PolicyRepository,
        version_repository: VersionRepository,
        cache_client: PolicyCacheClient,
    ) -> None:
        self._policy_repo = policy_repository
        self._version_repo = version_repository
        self._cache = cache_client

    async def publish(
        self,
        tenant_id: str,
        user_id: UUID,
        effective_date: date | None = None,
        change_summary: str = "",
    ) -> PolicyVersion:
        """Publish a new policy version from the tenant's current rules.

        Creates an immutable snapshot of all active (non-deleted) rules,
        assigns a monotonically increasing version number, calculates
        change statistics relative to the previous version, invalidates
        the Redis cache, and records an audit log entry.

        Args:
            tenant_id: The tenant identifier.
            user_id: The UUID of the user performing the publish.
            effective_date: The date from which this version is active.
                Defaults to the current date if not provided.
            change_summary: A human-readable summary of the changes.

        Returns:
            The newly created PolicyVersion entity.
        """
        if effective_date is None:
            effective_date = date.today()

        # 1. Get all current rules for tenant (non-deleted)
        current_rules = await self._policy_repo.get_rules_by_tenant(tenant_id)

        # 2. Serialize rules into a snapshot
        snapshot = self._create_snapshot(current_rules)

        # 3. Get latest version number and increment
        latest_version = await self._version_repo.get_latest_version_number(tenant_id)
        new_version_number = (latest_version or 0) + 1

        # 4. Calculate change statistics by comparing with previous version
        rules_added, rules_removed, rules_modified = await self._calculate_changes(
            tenant_id, snapshot, latest_version
        )

        # 5. Create PolicyVersion entity
        version = PolicyVersion(
            tenant_id=tenant_id,
            version_number=new_version_number,
            snapshot=snapshot,
            change_summary=change_summary,
            rules_added=rules_added,
            rules_removed=rules_removed,
            rules_modified=rules_modified,
            effective_date=effective_date,
            published_by=user_id,
            published_at=datetime.now(UTC),
        )

        # 6. Persist the version
        version = await self._version_repo.create_version(version)

        # 7. Invalidate Redis cache for tenant
        await self._cache.invalidate(tenant_id)

        # 8. Create audit log entry
        audit_log = PolicyAuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action_type="version_published",
            details={
                "version_number": new_version_number,
                "effective_date": effective_date.isoformat(),
                "change_summary": change_summary,
                "rules_added": rules_added,
                "rules_removed": rules_removed,
                "rules_modified": rules_modified,
            },
        )
        self._policy_repo.session.add(audit_log)
        await self._policy_repo.session.flush()

        return version

    async def diff(
        self,
        tenant_id: str,
        version_a: int,
        version_b: int,
    ) -> VersionDiffResult:
        """Compare two policy versions and categorize rule differences.

        Retrieves both versions and compares their snapshots, categorizing
        each rule as added, removed, modified, or unchanged.

        Args:
            tenant_id: The tenant identifier.
            version_a: The first version number (base).
            version_b: The second version number (target).

        Returns:
            A VersionDiffResult with categorized rules.

        Raises:
            PolicyVersionNotFoundError: If either version does not exist.
        """
        ver_a = await self._version_repo.get_version(tenant_id, version_a)
        if ver_a is None:
            raise PolicyVersionNotFoundError(
                f"Policy version {version_a} not found for tenant '{tenant_id}'"
            )

        ver_b = await self._version_repo.get_version(tenant_id, version_b)
        if ver_b is None:
            raise PolicyVersionNotFoundError(
                f"Policy version {version_b} not found for tenant '{tenant_id}'"
            )

        return self._compare_snapshots(ver_a.snapshot, ver_b.snapshot)

    async def rollback(
        self,
        tenant_id: str,
        target_version: int,
        user_id: UUID,
    ) -> PolicyVersion:
        """Rollback to a previous policy version.

        Creates a new version with the target version's snapshot,
        following the same publish flow (new version number, new
        timestamp, cache invalidation, audit log).

        Args:
            tenant_id: The tenant identifier.
            target_version: The version number to rollback to.
            user_id: The UUID of the user performing the rollback.

        Returns:
            The newly created PolicyVersion entity (with the rolled-back snapshot).

        Raises:
            PolicyVersionNotFoundError: If the target version does not exist.
        """
        # 1. Get target version
        target = await self._version_repo.get_version(tenant_id, target_version)
        if target is None:
            raise PolicyVersionNotFoundError(
                f"Policy version {target_version} not found for tenant '{tenant_id}'"
            )

        # 2. Get latest version number and increment
        latest_version = await self._version_repo.get_latest_version_number(tenant_id)
        new_version_number = (latest_version or 0) + 1

        # 3. Calculate change statistics relative to the current latest version
        rules_added, rules_removed, rules_modified = await self._calculate_changes(
            tenant_id, target.snapshot, latest_version
        )

        # 4. Create new version with target's snapshot
        change_summary = f"Rollback to version {target_version}"
        version = PolicyVersion(
            tenant_id=tenant_id,
            version_number=new_version_number,
            snapshot=target.snapshot,
            change_summary=change_summary,
            rules_added=rules_added,
            rules_removed=rules_removed,
            rules_modified=rules_modified,
            effective_date=date.today(),
            published_by=user_id,
            published_at=datetime.now(UTC),
        )

        # 5. Persist the version
        version = await self._version_repo.create_version(version)

        # 6. Invalidate Redis cache
        await self._cache.invalidate(tenant_id)

        # 7. Create audit log entry
        audit_log = PolicyAuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action_type="version_rollback",
            details={
                "version_number": new_version_number,
                "target_version": target_version,
                "change_summary": change_summary,
                "rules_added": rules_added,
                "rules_removed": rules_removed,
                "rules_modified": rules_modified,
            },
        )
        self._policy_repo.session.add(audit_log)
        await self._policy_repo.session.flush()

        return version

    # ---------------------------------------------------------------------------
    # Private helpers
    # ---------------------------------------------------------------------------

    def _create_snapshot(self, rules: list[PolicyRule]) -> dict[str, Any]:
        """Serialize a list of PolicyRule entities into a snapshot dict.

        The snapshot stores rules as a list of dicts keyed by rule_id
        for efficient comparison during diff operations.

        Args:
            rules: The list of active PolicyRule entities.

        Returns:
            A dict with a "rules" key containing a list of rule dicts.
        """
        rule_dicts: list[dict[str, Any]] = []
        for rule in rules:
            rule_dicts.append(
                {
                    "id": str(rule.id),
                    "rule_id": rule.rule_id,
                    "domain": rule.domain if isinstance(rule.domain, str) else rule.domain.value,
                    "name": rule.name,
                    "description": rule.description,
                    "rule_condition": rule.rule_condition,
                    "rule_action": rule.rule_action,
                    "priority": rule.priority,
                    "enabled": rule.enabled,
                    "is_custom": rule.is_custom,
                    "template_rule_id": (
                        str(rule.template_rule_id) if rule.template_rule_id else None
                    ),
                }
            )
        return {"rules": rule_dicts}

    async def _calculate_changes(
        self,
        tenant_id: str,
        new_snapshot: dict[str, Any],
        previous_version_number: int | None,
    ) -> tuple[int, int, int]:
        """Calculate added, removed, and modified rule counts.

        Compares the new snapshot against the previous version's snapshot.
        If no previous version exists, all rules are considered added.

        Args:
            tenant_id: The tenant identifier.
            new_snapshot: The new snapshot to compare.
            previous_version_number: The previous version number, or None.

        Returns:
            A tuple of (rules_added, rules_removed, rules_modified).
        """
        if previous_version_number is None:
            # First version: all rules are "added"
            return len(new_snapshot.get("rules", [])), 0, 0

        previous_version = await self._version_repo.get_version(tenant_id, previous_version_number)
        if previous_version is None:
            return len(new_snapshot.get("rules", [])), 0, 0

        diff_result = self._compare_snapshots(previous_version.snapshot, new_snapshot)
        return len(diff_result.added), len(diff_result.removed), len(diff_result.modified)

    def _compare_snapshots(
        self,
        snapshot_a: dict[str, Any],
        snapshot_b: dict[str, Any],
    ) -> VersionDiffResult:
        """Compare two snapshots and categorize rules.

        Uses rule_id as the key for matching rules between snapshots.
        A rule is considered modified if any of its fields differ
        (excluding the UUID primary key).

        Args:
            snapshot_a: The base snapshot (version A).
            snapshot_b: The target snapshot (version B).

        Returns:
            A VersionDiffResult with categorized rules.
        """
        rules_a = {r["rule_id"]: r for r in snapshot_a.get("rules", [])}
        rules_b = {r["rule_id"]: r for r in snapshot_b.get("rules", [])}

        added: list[dict[str, Any]] = []
        removed: list[dict[str, Any]] = []
        modified: list[dict[str, Any]] = []
        unchanged: list[dict[str, Any]] = []

        # Rules in B but not in A → added
        for rule_id, rule in rules_b.items():
            if rule_id not in rules_a:
                added.append(rule)

        # Rules in A but not in B → removed
        for rule_id, rule in rules_a.items():
            if rule_id not in rules_b:
                removed.append(rule)

        # Rules in both → check if modified or unchanged
        for rule_id in rules_a:
            if rule_id in rules_b:
                if self._rules_differ(rules_a[rule_id], rules_b[rule_id]):
                    modified.append(
                        {
                            "rule_id": rule_id,
                            "before": rules_a[rule_id],
                            "after": rules_b[rule_id],
                        }
                    )
                else:
                    unchanged.append(rules_a[rule_id])

        return VersionDiffResult(
            added=added,
            removed=removed,
            modified=modified,
            unchanged=unchanged,
        )

    def _rules_differ(
        self,
        rule_a: dict[str, Any],
        rule_b: dict[str, Any],
    ) -> bool:
        """Check if two rule dicts differ in any meaningful field.

        Compares all fields except the UUID primary key ('id'), since
        the same logical rule may have different UUIDs across versions.

        Args:
            rule_a: The rule dict from version A.
            rule_b: The rule dict from version B.

        Returns:
            True if the rules differ, False if they are identical.
        """
        compare_fields = [
            "rule_id",
            "domain",
            "name",
            "description",
            "rule_condition",
            "rule_action",
            "priority",
            "enabled",
            "is_custom",
            "template_rule_id",
        ]
        for field in compare_fields:
            if rule_a.get(field) != rule_b.get(field):
                return True
        return False
