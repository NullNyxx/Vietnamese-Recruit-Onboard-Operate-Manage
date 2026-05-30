"""Property-based tests for policy versioning.

Uses Hypothesis to verify correctness properties of the VersionService.
"""

# Feature: company-policy-engine, Property 9: Version Number Monotonicity
# Feature: company-policy-engine, Property 12: Version Diff Correctness
# Feature: company-policy-engine, Property 13: Rollback Produces Identical Rules

from datetime import date
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.modules.policy.application.version_service import VersionService
from src.modules.policy.domain.entities import PolicyVersion
from src.modules.policy.domain.enums import ActionType, PolicyDomain, RuleOperator

# ---------------------------------------------------------------------------
# Strategies for generating rule dicts used in version snapshots
# ---------------------------------------------------------------------------

_VALID_DOMAINS = [d.value for d in PolicyDomain]
_VALID_OPERATORS = [op.value for op in RuleOperator]
_VALID_ACTION_TYPES = [at.value for at in ActionType]

# Strategy for generating unique rule_id strings
_rule_id_st = st.from_regex(r"[A-Z]{2,4}-[0-9]{3}", fullmatch=True)

# Strategy for generating a single rule dict as stored in a version snapshot
_priority_st = st.integers(min_value=1, max_value=1000)
_name_st = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Z")),
    min_size=1,
    max_size=64,
)
_description_st = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Z")),
    min_size=1,
    max_size=128,
)


@st.composite
def rule_dict_strategy(draw: st.DrawFn, rule_id: str | None = None) -> dict[str, Any]:
    """Generate a rule dict as it appears in a version snapshot."""
    return {
        "id": draw(st.uuids()).hex,
        "rule_id": rule_id or draw(_rule_id_st),
        "domain": draw(st.sampled_from(_VALID_DOMAINS)),
        "name": draw(_name_st),
        "description": draw(_description_st),
        "rule_condition": {
            "field": draw(st.from_regex(r"[a-z_]{3,20}", fullmatch=True)),
            "operator": draw(st.sampled_from(_VALID_OPERATORS)),
            "value": draw(st.integers(min_value=0, max_value=1000)),
        },
        "rule_action": {
            "type": draw(st.sampled_from(_VALID_ACTION_TYPES)),
            "parameters": {"status": draw(st.from_regex(r"[a-z_]{3,15}", fullmatch=True))},
        },
        "priority": draw(_priority_st),
        "enabled": draw(st.booleans()),
        "is_custom": draw(st.booleans()),
        "template_rule_id": None,
    }


@st.composite
def snapshot_pair_strategy(
    draw: st.DrawFn,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Generate two snapshots with overlapping, unique, and modified rules.

    Returns (snapshot_a, snapshot_b) where:
    - Some rules are only in A (will be "removed")
    - Some rules are only in B (will be "added")
    - Some rules are in both with identical values (will be "unchanged")
    - Some rules are in both with different values (will be "modified")
    """
    # Generate distinct rule_ids for each category
    num_only_a = draw(st.integers(min_value=0, max_value=5))
    num_only_b = draw(st.integers(min_value=0, max_value=5))
    num_unchanged = draw(st.integers(min_value=0, max_value=5))
    num_modified = draw(st.integers(min_value=0, max_value=5))

    total = num_only_a + num_only_b + num_unchanged + num_modified
    # Ensure at least one rule exists across both snapshots
    if total == 0:
        num_unchanged = 1

    # Generate unique rule_ids for all categories
    all_rule_ids = draw(
        st.lists(
            _rule_id_st,
            min_size=num_only_a + num_only_b + num_unchanged + num_modified,
            max_size=num_only_a + num_only_b + num_unchanged + num_modified,
            unique=True,
        )
    )

    idx = 0
    only_a_ids = all_rule_ids[idx : idx + num_only_a]
    idx += num_only_a
    only_b_ids = all_rule_ids[idx : idx + num_only_b]
    idx += num_only_b
    unchanged_ids = all_rule_ids[idx : idx + num_unchanged]
    idx += num_unchanged
    modified_ids = all_rule_ids[idx : idx + num_modified]

    rules_a: list[dict[str, Any]] = []
    rules_b: list[dict[str, Any]] = []

    # Rules only in A
    for rid in only_a_ids:
        rules_a.append(draw(rule_dict_strategy(rule_id=rid)))

    # Rules only in B
    for rid in only_b_ids:
        rules_b.append(draw(rule_dict_strategy(rule_id=rid)))

    # Unchanged rules (identical in both)
    for rid in unchanged_ids:
        rule = draw(rule_dict_strategy(rule_id=rid))
        rules_a.append(rule.copy())
        rules_b.append(rule.copy())

    # Modified rules (same rule_id, different values)
    for rid in modified_ids:
        rule_a = draw(rule_dict_strategy(rule_id=rid))
        rule_b = rule_a.copy()
        # Modify at least one field to ensure they differ
        rule_b["priority"] = (rule_a["priority"] % 1000) + 1
        if rule_b["priority"] == rule_a["priority"]:
            rule_b["enabled"] = not rule_a["enabled"]
        rules_a.append(rule_a)
        rules_b.append(rule_b)

    snapshot_a = {"rules": rules_a}
    snapshot_b = {"rules": rules_b}

    return snapshot_a, snapshot_b


# ---------------------------------------------------------------------------
# Property 12: Version Diff Correctness
# ---------------------------------------------------------------------------


class TestVersionDiffCorrectness:
    """Property 12: Version Diff Correctness.

    For any two policy versions V1 and V2 of the same tenant, the diff SHALL
    correctly categorize every rule as: added (present in V2 but not V1),
    removed (present in V1 but not V2), modified (present in both but with
    different values), or unchanged (present in both with identical values),
    and the union of these categories SHALL equal the union of all rules in
    V1 and V2.

    **Validates: Requirements 4.5**
    """

    @settings(max_examples=100)
    @given(snapshots=snapshot_pair_strategy())
    def test_union_of_categories_equals_union_of_all_rules(
        self, snapshots: tuple[dict[str, Any], dict[str, Any]]
    ) -> None:
        """The union of added, removed, modified, unchanged rule_ids equals
        the union of all rule_ids in V1 and V2.

        **Validates: Requirements 4.5**
        """
        snapshot_a, snapshot_b = snapshots

        # Create a VersionService instance (we only need _compare_snapshots)
        service = VersionService.__new__(VersionService)
        result = service._compare_snapshots(snapshot_a, snapshot_b)

        # Collect rule_ids from each category
        added_ids = {r["rule_id"] for r in result.added}
        removed_ids = {r["rule_id"] for r in result.removed}
        modified_ids = {r["rule_id"] for r in result.modified}
        unchanged_ids = {r["rule_id"] for r in result.unchanged}

        # Union of all categories
        all_categorized = added_ids | removed_ids | modified_ids | unchanged_ids

        # Union of all rules in both snapshots
        all_v1_ids = {r["rule_id"] for r in snapshot_a.get("rules", [])}
        all_v2_ids = {r["rule_id"] for r in snapshot_b.get("rules", [])}
        all_rule_ids = all_v1_ids | all_v2_ids

        assert all_categorized == all_rule_ids, (
            f"Categorized rule_ids {all_categorized} != "
            f"union of V1+V2 rule_ids {all_rule_ids}"
        )

    @settings(max_examples=100)
    @given(snapshots=snapshot_pair_strategy())
    def test_categories_are_mutually_exclusive(
        self, snapshots: tuple[dict[str, Any], dict[str, Any]]
    ) -> None:
        """No rule_id appears in more than one category.

        **Validates: Requirements 4.5**
        """
        snapshot_a, snapshot_b = snapshots

        service = VersionService.__new__(VersionService)
        result = service._compare_snapshots(snapshot_a, snapshot_b)

        added_ids = {r["rule_id"] for r in result.added}
        removed_ids = {r["rule_id"] for r in result.removed}
        modified_ids = {r["rule_id"] for r in result.modified}
        unchanged_ids = {r["rule_id"] for r in result.unchanged}

        # No overlaps between any two categories
        assert added_ids.isdisjoint(removed_ids), "added ∩ removed is non-empty"
        assert added_ids.isdisjoint(modified_ids), "added ∩ modified is non-empty"
        assert added_ids.isdisjoint(unchanged_ids), "added ∩ unchanged is non-empty"
        assert removed_ids.isdisjoint(modified_ids), "removed ∩ modified is non-empty"
        assert removed_ids.isdisjoint(unchanged_ids), "removed ∩ unchanged is non-empty"
        assert modified_ids.isdisjoint(unchanged_ids), "modified ∩ unchanged is non-empty"

    @settings(max_examples=100)
    @given(snapshots=snapshot_pair_strategy())
    def test_added_rules_only_in_v2(
        self, snapshots: tuple[dict[str, Any], dict[str, Any]]
    ) -> None:
        """Added rules are present in V2 but not in V1.

        **Validates: Requirements 4.5**
        """
        snapshot_a, snapshot_b = snapshots

        service = VersionService.__new__(VersionService)
        result = service._compare_snapshots(snapshot_a, snapshot_b)

        v1_ids = {r["rule_id"] for r in snapshot_a.get("rules", [])}
        v2_ids = {r["rule_id"] for r in snapshot_b.get("rules", [])}

        for rule in result.added:
            rid = rule["rule_id"]
            assert rid in v2_ids, f"Added rule '{rid}' not found in V2"
            assert rid not in v1_ids, f"Added rule '{rid}' unexpectedly found in V1"

    @settings(max_examples=100)
    @given(snapshots=snapshot_pair_strategy())
    def test_removed_rules_only_in_v1(
        self, snapshots: tuple[dict[str, Any], dict[str, Any]]
    ) -> None:
        """Removed rules are present in V1 but not in V2.

        **Validates: Requirements 4.5**
        """
        snapshot_a, snapshot_b = snapshots

        service = VersionService.__new__(VersionService)
        result = service._compare_snapshots(snapshot_a, snapshot_b)

        v1_ids = {r["rule_id"] for r in snapshot_a.get("rules", [])}
        v2_ids = {r["rule_id"] for r in snapshot_b.get("rules", [])}

        for rule in result.removed:
            rid = rule["rule_id"]
            assert rid in v1_ids, f"Removed rule '{rid}' not found in V1"
            assert rid not in v2_ids, f"Removed rule '{rid}' unexpectedly found in V2"

    @settings(max_examples=100)
    @given(snapshots=snapshot_pair_strategy())
    def test_modified_rules_in_both_with_differences(
        self, snapshots: tuple[dict[str, Any], dict[str, Any]]
    ) -> None:
        """Modified rules are present in both V1 and V2 with different values.

        **Validates: Requirements 4.5**
        """
        snapshot_a, snapshot_b = snapshots

        service = VersionService.__new__(VersionService)
        result = service._compare_snapshots(snapshot_a, snapshot_b)

        v1_map = {r["rule_id"]: r for r in snapshot_a.get("rules", [])}
        v2_map = {r["rule_id"]: r for r in snapshot_b.get("rules", [])}

        for entry in result.modified:
            rid = entry["rule_id"]
            assert rid in v1_map, f"Modified rule '{rid}' not found in V1"
            assert rid in v2_map, f"Modified rule '{rid}' not found in V2"
            # The before/after values must actually differ
            assert entry["before"] != entry["after"], (
                f"Modified rule '{rid}' has identical before/after values"
            )

    @settings(max_examples=100)
    @given(snapshots=snapshot_pair_strategy())
    def test_unchanged_rules_identical_in_both(
        self, snapshots: tuple[dict[str, Any], dict[str, Any]]
    ) -> None:
        """Unchanged rules are present in both V1 and V2 with identical values.

        **Validates: Requirements 4.5**
        """
        snapshot_a, snapshot_b = snapshots

        service = VersionService.__new__(VersionService)
        result = service._compare_snapshots(snapshot_a, snapshot_b)

        v1_map = {r["rule_id"]: r for r in snapshot_a.get("rules", [])}
        v2_map = {r["rule_id"]: r for r in snapshot_b.get("rules", [])}

        for rule in result.unchanged:
            rid = rule["rule_id"]
            assert rid in v1_map, f"Unchanged rule '{rid}' not found in V1"
            assert rid in v2_map, f"Unchanged rule '{rid}' not found in V2"
            # The rule values must be identical in both versions
            # (comparing the fields that _rules_differ checks)
            compare_fields = [
                "rule_id", "domain", "name", "description",
                "rule_condition", "rule_action", "priority",
                "enabled", "is_custom", "template_rule_id",
            ]
            for field in compare_fields:
                assert v1_map[rid].get(field) == v2_map[rid].get(field), (
                    f"Unchanged rule '{rid}' has different '{field}' values: "
                    f"V1={v1_map[rid].get(field)!r}, V2={v2_map[rid].get(field)!r}"
                )


# ---------------------------------------------------------------------------
# Property 13: Rollback Produces Identical Rules
# ---------------------------------------------------------------------------


@st.composite
def version_snapshot_strategy(draw: st.DrawFn) -> dict[str, Any]:
    """Generate a complete version snapshot with unique rule_ids."""
    rules = draw(
        st.lists(
            rule_dict_strategy(),
            min_size=0,
            max_size=10,
            unique_by=lambda r: r["rule_id"],
        )
    )
    return {"rules": rules}


def _make_rollback_service() -> tuple[VersionService, AsyncMock, AsyncMock, AsyncMock]:
    """Create a VersionService with mocked dependencies for rollback tests.

    Returns:
        Tuple of (service, policy_repo_mock, version_repo_mock, cache_mock).
    """
    policy_repo = AsyncMock()
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


class TestRollbackProducesIdenticalRules:
    """Property 13: Rollback Produces Identical Rules.

    For any previous policy version V_target, rolling back to V_target
    SHALL create a new policy version V_new whose rule snapshot is
    value-identical to V_target's snapshot (same rules, same values,
    same enabled states).

    **Validates: Requirements 4.6**
    """

    @settings(max_examples=100)
    @given(
        target_snapshot=version_snapshot_strategy(),
        target_version_number=st.integers(min_value=1, max_value=100),
        latest_version_number=st.integers(min_value=1, max_value=200),
    )
    @pytest.mark.asyncio
    async def test_rollback_snapshot_is_value_identical_to_target(
        self,
        target_snapshot: dict[str, Any],
        target_version_number: int,
        latest_version_number: int,
    ) -> None:
        """Rolling back to a target version produces a new version whose
        snapshot is value-identical to the target's snapshot.

        **Validates: Requirements 4.6**
        """
        # Ensure latest >= target so the scenario is realistic
        latest = max(latest_version_number, target_version_number)

        service, _, version_repo, _ = _make_rollback_service()

        # Create the target version with the generated snapshot
        target = PolicyVersion(
            id=uuid4(),
            tenant_id="tenant-prop13",
            version_number=target_version_number,
            snapshot=target_snapshot,
            change_summary="Original publish",
            rules_added=len(target_snapshot.get("rules", [])),
            rules_removed=0,
            rules_modified=0,
            effective_date=date(2024, 1, 1),
            published_by=uuid4(),
        )

        # Mock: get_version returns the target for both the rollback lookup
        # and the _calculate_changes call (which fetches the latest version)
        version_repo.get_version.return_value = target
        version_repo.get_latest_version_number.return_value = latest

        user_id = uuid4()
        result = await service.rollback("tenant-prop13", target_version_number, user_id)

        # The new version's snapshot must be value-identical to the target's
        assert result.snapshot == target_snapshot, (
            f"Rollback snapshot differs from target.\n"
            f"Target snapshot: {target_snapshot}\n"
            f"Result snapshot: {result.snapshot}"
        )

        # Verify individual rules match in count
        target_rules = target_snapshot.get("rules", [])
        result_rules = result.snapshot.get("rules", [])
        assert len(result_rules) == len(target_rules), (
            f"Rule count mismatch: target has {len(target_rules)}, "
            f"result has {len(result_rules)}"
        )

        # Verify each rule's values and enabled states are identical
        for target_rule, result_rule in zip(target_rules, result_rules):
            assert target_rule["rule_id"] == result_rule["rule_id"], (
                f"rule_id mismatch: {target_rule['rule_id']} != "
                f"{result_rule['rule_id']}"
            )
            assert target_rule["enabled"] == result_rule["enabled"], (
                f"enabled state mismatch for rule {target_rule['rule_id']}: "
                f"{target_rule['enabled']} != {result_rule['enabled']}"
            )
            assert target_rule["rule_condition"] == result_rule["rule_condition"]
            assert target_rule["rule_action"] == result_rule["rule_action"]
            assert target_rule["priority"] == result_rule["priority"]
            assert target_rule["name"] == result_rule["name"]
            assert target_rule["domain"] == result_rule["domain"]
            assert target_rule["is_custom"] == result_rule["is_custom"]

        # The new version number must be latest + 1
        assert result.version_number == latest + 1


# ---------------------------------------------------------------------------
# Property 9: Version Number Monotonicity
# ---------------------------------------------------------------------------


def _make_monotonicity_service() -> tuple[VersionService, AsyncMock, AsyncMock, AsyncMock]:
    """Create a VersionService with mocked dependencies for monotonicity tests.

    Returns:
        Tuple of (service, policy_repo_mock, version_repo_mock, cache_mock).
    """
    policy_repo = AsyncMock()
    session_mock = MagicMock()
    session_mock.flush = AsyncMock()
    policy_repo.session = session_mock
    policy_repo.get_rules_by_tenant.return_value = []

    version_repo = AsyncMock()
    version_repo.create_version.side_effect = lambda v: v

    cache_client = AsyncMock()

    service = VersionService(
        policy_repository=policy_repo,
        version_repository=version_repo,
        cache_client=cache_client,
    )
    return service, policy_repo, version_repo, cache_client


class TestVersionNumberMonotonicity:
    """Property 9: Version Number Monotonicity.

    For any tenant, the sequence of policy version numbers SHALL be strictly
    monotonically increasing — each new version number SHALL be exactly one
    greater than the previous maximum version number for that tenant.

    **Validates: Requirements 4.1**
    """

    @settings(max_examples=100)
    @given(num_publishes=st.integers(min_value=1, max_value=20))
    async def test_version_numbers_are_strictly_monotonic(
        self, num_publishes: int
    ) -> None:
        """Publishing N times produces version numbers 1, 2, ..., N.

        Each version number is exactly one greater than the previous.

        **Validates: Requirements 4.1**
        """
        service, policy_repo, version_repo, _ = _make_monotonicity_service()
        tenant_id = "tenant-mono"
        user_id = uuid4()

        # Track the current latest version number (starts at None = no versions)
        current_latest: int | None = None
        published_versions: list[int] = []

        for _ in range(num_publishes):
            # Mock get_latest_version_number to return the current latest
            version_repo.get_latest_version_number.return_value = current_latest
            # Mock get_version for _calculate_changes (previous version lookup)
            if current_latest is not None:
                version_repo.get_version.return_value = PolicyVersion(
                    tenant_id=tenant_id,
                    version_number=current_latest,
                    snapshot={"rules": []},
                    change_summary="prev",
                    rules_added=0,
                    rules_removed=0,
                    rules_modified=0,
                    effective_date=date(2024, 1, 1),
                    published_by=user_id,
                )
            else:
                version_repo.get_version.return_value = None

            result = await service.publish(
                tenant_id=tenant_id,
                user_id=user_id,
                effective_date=date(2024, 6, 1),
                change_summary=f"Publish #{len(published_versions) + 1}",
            )

            published_versions.append(result.version_number)
            current_latest = result.version_number

        # Verify strict monotonicity: each version == previous + 1
        for i in range(1, len(published_versions)):
            assert published_versions[i] == published_versions[i - 1] + 1, (
                f"Version {published_versions[i]} is not exactly one greater "
                f"than previous {published_versions[i - 1]}. "
                f"Full sequence: {published_versions}"
            )

        # Verify first version is 1
        assert published_versions[0] == 1, (
            f"First version should be 1, got {published_versions[0]}"
        )

        # Verify last version equals num_publishes
        assert published_versions[-1] == num_publishes, (
            f"After {num_publishes} publishes, last version should be "
            f"{num_publishes}, got {published_versions[-1]}"
        )
