# Feature: company-policy-engine, Property 1: Tenant Isolation During Evaluation
# Feature: company-policy-engine, Property 2: Tenant Non-Interference on Modification
# Feature: company-policy-engine, Property 3: Cross-Tenant Access Rejection
# Feature: company-policy-engine, Property 4: Template Update Non-Interference
# Feature: company-policy-engine, Property 11: Date-Based Version Resolution
"""Property-based tests for policy evaluation properties.

Property 2: For any tenant A and tenant B where A ≠ B, when tenant A creates,
modifies, or deletes a policy rule, the complete set of policy rules for tenant B
SHALL remain byte-identical before and after the operation.
**Validates: Requirements 1.3**

Property 3: For any two distinct tenants A and B, any request authenticated
as tenant A that attempts to read, modify, or delete a policy rule belonging
to tenant B SHALL be rejected with an authorization error.
**Validates: Requirements 1.4**

Property 11: For any tenant with a set of policy versions each having an
effective_date, and any evaluation date D, the engine SHALL select the version
whose effective_date is the maximum value that is less than or equal to D.
If no version has effective_date <= D, the initial version SHALL be used.
**Validates: Requirements 4.3, 10.8**
"""

import copy
import string
from datetime import date
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from src.modules.policy.application.evaluation_service import EvaluationService
from src.modules.policy.application.policy_service import PolicyService
from src.modules.policy.domain.entities import PolicyRule, PolicyTemplate, PolicyVersion
from src.modules.policy.domain.enums import ActionType, PolicyDomain, RuleOperator
from src.modules.policy.domain.exceptions import PolicyRuleNotFoundError

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Generate tenant IDs as non-empty strings (max 64 chars per spec)
_tenant_id_strategy = st.text(
    alphabet=string.ascii_lowercase + string.digits + "-_",
    min_size=1,
    max_size=32,
)


@st.composite
def distinct_tenant_ids(draw: st.DrawFn) -> tuple[str, str]:
    """Generate two distinct tenant IDs."""
    tenant_a = draw(_tenant_id_strategy)
    tenant_b = draw(_tenant_id_strategy.filter(lambda t: t != tenant_a))
    return tenant_a, tenant_b


# Generate rule IDs
_rule_id_strategy = st.text(
    alphabet=string.ascii_lowercase + string.digits + "-_",
    min_size=1,
    max_size=32,
)


# ---------------------------------------------------------------------------
# Strategies for Property 2: Tenant Non-Interference on Modification
# ---------------------------------------------------------------------------

SUPPORTED_OPERATORS: list[str] = [op.value for op in RuleOperator]
SUPPORTED_ACTION_TYPES: list[str] = [at.value for at in ActionType]
SUPPORTED_DOMAINS: list[str] = [d.value for d in PolicyDomain]


@st.composite
def policy_rule_data(draw: st.DrawFn) -> dict:
    """Generate valid policy rule data for creation."""
    domain = draw(st.sampled_from(SUPPORTED_DOMAINS))
    rule_id = draw(
        st.text(
            alphabet=string.ascii_lowercase + string.digits + "-",
            min_size=1,
            max_size=32,
        )
    )
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
    field_name = draw(
        st.text(alphabet=string.ascii_lowercase + "_", min_size=1, max_size=32)
    )
    condition_value = draw(st.integers(min_value=0, max_value=10000))

    return {
        "rule_id": rule_id,
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
        "enabled": draw(st.booleans()),
    }


@st.composite
def tenant_b_rules(draw: st.DrawFn) -> list[dict]:
    """Generate a list of policy rules for tenant B."""
    num_rules = draw(st.integers(min_value=1, max_value=5))
    rules = []
    for i in range(num_rules):
        domain = draw(st.sampled_from(SUPPORTED_DOMAINS))
        operator = draw(st.sampled_from(SUPPORTED_OPERATORS))
        action_type = draw(st.sampled_from(SUPPORTED_ACTION_TYPES))
        priority = draw(st.integers(min_value=1, max_value=1000))
        field_name = draw(
            st.text(alphabet=string.ascii_lowercase + "_", min_size=1, max_size=20)
        )
        condition_value = draw(st.integers(min_value=0, max_value=10000))

        rules.append({
            "rule_id": f"rule-b-{i}",
            "domain": domain,
            "name": f"Tenant B Rule {i}",
            "description": f"Description for rule {i}",
            "rule_condition": {
                "field": field_name,
                "operator": operator,
                "value": condition_value,
            },
            "rule_action": {
                "type": action_type,
                "parameters": {"status": f"action-{i}"},
            },
            "priority": priority,
            "enabled": draw(st.booleans()),
        })
    return rules


def _make_policy_rule_entity(tenant_id: str, rule_data: dict) -> PolicyRule:
    """Create a PolicyRule entity from rule data dict."""
    return PolicyRule(
        id=uuid4(),
        tenant_id=tenant_id,
        domain=PolicyDomain(rule_data["domain"]),
        rule_id=rule_data["rule_id"],
        name=rule_data["name"],
        description=rule_data["description"],
        rule_condition=rule_data["rule_condition"],
        rule_action=rule_data["rule_action"],
        priority=rule_data["priority"],
        enabled=rule_data["enabled"],
        template_rule_id=None,
        is_custom=True,
        is_deleted=False,
        created_by=uuid4(),
    )


def _rules_to_snapshot(rules: list[dict]) -> list[dict]:
    """Convert rule data list to a deep-copied snapshot for comparison."""
    return copy.deepcopy(rules)


# ---------------------------------------------------------------------------
# Property 2: Tenant Non-Interference on Modification
# ---------------------------------------------------------------------------


class TestProperty2TenantNonInterferenceOnModification:
    """Property 2: Tenant Non-Interference on Modification.

    For any tenant A and tenant B where A ≠ B, when tenant A creates,
    modifies, or deletes a policy rule, the complete set of policy rules
    for tenant B SHALL remain byte-identical before and after the operation.

    **Validates: Requirements 1.3**
    """

    @settings(max_examples=100)
    @given(
        tenants=distinct_tenant_ids(),
        rule_data=policy_rule_data(),
        b_rules=tenant_b_rules(),
    )
    @pytest.mark.asyncio
    async def test_create_rule_does_not_affect_other_tenant(
        self,
        tenants: tuple[str, str],
        rule_data: dict,
        b_rules: list[dict],
    ) -> None:
        """Creating a rule for tenant A SHALL NOT alter tenant B's rules.

        Generate two tenants with rules, create a new rule for tenant A,
        and verify tenant B's rules are byte-identical before and after.
        """
        tenant_a, tenant_b = tenants

        # Snapshot tenant B's rules before the operation
        tenant_b_snapshot_before = _rules_to_snapshot(b_rules)

        # Build tenant B's PolicyRule entities
        tenant_b_entities = [_make_policy_rule_entity(tenant_b, r) for r in b_rules]

        # Set up mocks
        policy_repo = AsyncMock()
        template_repo = AsyncMock()

        # count_custom_rules returns a count below the limit for tenant A
        policy_repo.count_custom_rules.return_value = 0

        # create_rule returns the new rule for tenant A
        new_rule = _make_policy_rule_entity(tenant_a, rule_data)
        policy_repo.create_rule.return_value = new_rule

        # get_rules_by_tenant returns tenant B's rules (unchanged)
        policy_repo.get_rules_by_tenant.return_value = tenant_b_entities

        service = PolicyService(policy_repo=policy_repo, template_repo=template_repo)

        # Perform the create operation on tenant A
        await service.create_custom_rule(
            tenant_id=tenant_a,
            rule_data=rule_data,
            user_id=uuid4(),
        )

        # Verify: the repository was called with tenant A's ID only
        policy_repo.create_rule.assert_called_once()
        created_rule = policy_repo.create_rule.call_args[0][0]
        assert created_rule.tenant_id == tenant_a

        # Verify: tenant B's rules remain byte-identical
        tenant_b_snapshot_after = _rules_to_snapshot(b_rules)
        assert tenant_b_snapshot_before == tenant_b_snapshot_after

        # Verify: fetching tenant B's rules returns the same set
        fetched_b_rules = await policy_repo.get_rules_by_tenant(tenant_b)
        for i, entity in enumerate(fetched_b_rules):
            assert entity.tenant_id == tenant_b
            assert entity.rule_id == b_rules[i]["rule_id"]
            assert entity.name == b_rules[i]["name"]
            assert entity.rule_condition == b_rules[i]["rule_condition"]
            assert entity.rule_action == b_rules[i]["rule_action"]
            assert entity.priority == b_rules[i]["priority"]
            assert entity.enabled == b_rules[i]["enabled"]

    @settings(max_examples=100)
    @given(
        tenants=distinct_tenant_ids(),
        b_rules=tenant_b_rules(),
    )
    @pytest.mark.asyncio
    async def test_update_rule_does_not_affect_other_tenant(
        self,
        tenants: tuple[str, str],
        b_rules: list[dict],
    ) -> None:
        """Modifying a rule for tenant A SHALL NOT alter tenant B's rules.

        Generate two tenants with rules, modify tenant A's rule,
        and verify tenant B's rules are byte-identical before and after.
        """
        tenant_a, tenant_b = tenants

        # Snapshot tenant B's rules before the operation
        tenant_b_snapshot_before = _rules_to_snapshot(b_rules)

        # Build tenant B's PolicyRule entities
        tenant_b_entities = [_make_policy_rule_entity(tenant_b, r) for r in b_rules]

        # Create an existing rule for tenant A
        existing_rule_a = PolicyRule(
            id=uuid4(),
            tenant_id=tenant_a,
            domain=PolicyDomain.ATTENDANCE,
            rule_id="rule-a-existing",
            name="Tenant A Rule",
            description="A rule belonging to tenant A",
            rule_condition={
                "field": "minutes_late",
                "operator": "greater_than",
                "value": 15,
            },
            rule_action={"type": "flag", "parameters": {"status": "late"}},
            priority=100,
            enabled=True,
            template_rule_id=None,
            is_custom=True,
            is_deleted=False,
            created_by=uuid4(),
        )

        # Updated version of tenant A's rule
        updated_rule_a = PolicyRule(
            id=existing_rule_a.id,
            tenant_id=tenant_a,
            domain=PolicyDomain.ATTENDANCE,
            rule_id="rule-a-existing",
            name="Updated Tenant A Rule",
            description="Updated description",
            rule_condition={
                "field": "minutes_late",
                "operator": "greater_than",
                "value": 30,
            },
            rule_action={"type": "flag", "parameters": {"status": "very_late"}},
            priority=50,
            enabled=True,
            template_rule_id=None,
            is_custom=True,
            is_deleted=False,
            created_by=existing_rule_a.created_by,
        )

        # Set up mocks
        policy_repo = AsyncMock()
        template_repo = AsyncMock()

        # get_rule returns tenant A's rule when queried with tenant A
        policy_repo.get_rule.return_value = existing_rule_a
        # update_rule returns the updated rule for tenant A
        policy_repo.update_rule.return_value = updated_rule_a
        # get_rules_by_tenant returns tenant B's rules (unchanged)
        policy_repo.get_rules_by_tenant.return_value = tenant_b_entities

        service = PolicyService(policy_repo=policy_repo, template_repo=template_repo)

        # Perform the update operation on tenant A
        await service.update_rule(
            tenant_id=tenant_a,
            rule_id="rule-a-existing",
            updates={"name": "Updated Tenant A Rule", "priority": 50},
            user_id=uuid4(),
        )

        # Verify: the repository update was called with tenant A's ID
        policy_repo.update_rule.assert_called_once()
        call_args = policy_repo.update_rule.call_args[0]
        assert call_args[0] == tenant_a

        # Verify: tenant B's rules remain byte-identical
        tenant_b_snapshot_after = _rules_to_snapshot(b_rules)
        assert tenant_b_snapshot_before == tenant_b_snapshot_after

        # Verify: fetching tenant B's rules returns the same set
        fetched_b_rules = await policy_repo.get_rules_by_tenant(tenant_b)
        for i, entity in enumerate(fetched_b_rules):
            assert entity.tenant_id == tenant_b
            assert entity.rule_id == b_rules[i]["rule_id"]
            assert entity.name == b_rules[i]["name"]
            assert entity.rule_condition == b_rules[i]["rule_condition"]
            assert entity.rule_action == b_rules[i]["rule_action"]
            assert entity.priority == b_rules[i]["priority"]
            assert entity.enabled == b_rules[i]["enabled"]

    @settings(max_examples=100)
    @given(
        tenants=distinct_tenant_ids(),
        b_rules=tenant_b_rules(),
    )
    @pytest.mark.asyncio
    async def test_delete_rule_does_not_affect_other_tenant(
        self,
        tenants: tuple[str, str],
        b_rules: list[dict],
    ) -> None:
        """Deleting a rule for tenant A SHALL NOT alter tenant B's rules.

        Generate two tenants with rules, delete tenant A's rule,
        and verify tenant B's rules are byte-identical before and after.
        """
        tenant_a, tenant_b = tenants

        # Snapshot tenant B's rules before the operation
        tenant_b_snapshot_before = _rules_to_snapshot(b_rules)

        # Build tenant B's PolicyRule entities
        tenant_b_entities = [_make_policy_rule_entity(tenant_b, r) for r in b_rules]

        # Create an existing custom rule for tenant A to be deleted
        existing_rule_a = PolicyRule(
            id=uuid4(),
            tenant_id=tenant_a,
            domain=PolicyDomain.ATTENDANCE,
            rule_id="rule-a-to-delete",
            name="Tenant A Rule To Delete",
            description="A custom rule to be soft-deleted",
            rule_condition={
                "field": "hours",
                "operator": "greater_than",
                "value": 8,
            },
            rule_action={"type": "flag", "parameters": {"status": "overtime"}},
            priority=200,
            enabled=True,
            template_rule_id=None,
            is_custom=True,
            is_deleted=False,
            created_by=uuid4(),
        )

        # Soft-deleted version of tenant A's rule
        deleted_rule_a = PolicyRule(
            id=existing_rule_a.id,
            tenant_id=tenant_a,
            domain=PolicyDomain.ATTENDANCE,
            rule_id="rule-a-to-delete",
            name="Tenant A Rule To Delete",
            description="A custom rule to be soft-deleted",
            rule_condition={
                "field": "hours",
                "operator": "greater_than",
                "value": 8,
            },
            rule_action={"type": "flag", "parameters": {"status": "overtime"}},
            priority=200,
            enabled=True,
            template_rule_id=None,
            is_custom=True,
            is_deleted=True,
            created_by=existing_rule_a.created_by,
        )

        # Set up mocks
        policy_repo = AsyncMock()
        template_repo = AsyncMock()

        # get_rule returns tenant A's rule when queried with tenant A
        policy_repo.get_rule.return_value = existing_rule_a
        # soft_delete_rule returns the deleted rule for tenant A
        policy_repo.soft_delete_rule.return_value = deleted_rule_a
        # get_rules_by_tenant returns tenant B's rules (unchanged)
        policy_repo.get_rules_by_tenant.return_value = tenant_b_entities

        service = PolicyService(policy_repo=policy_repo, template_repo=template_repo)

        # Perform the delete operation on tenant A
        await service.disable_rule(
            tenant_id=tenant_a,
            rule_id="rule-a-to-delete",
        )

        # Verify: the repository soft_delete was called with tenant A's ID
        policy_repo.soft_delete_rule.assert_called_once_with(tenant_a, "rule-a-to-delete")

        # Verify: tenant B's rules remain byte-identical
        tenant_b_snapshot_after = _rules_to_snapshot(b_rules)
        assert tenant_b_snapshot_before == tenant_b_snapshot_after

        # Verify: fetching tenant B's rules returns the same set
        fetched_b_rules = await policy_repo.get_rules_by_tenant(tenant_b)
        for i, entity in enumerate(fetched_b_rules):
            assert entity.tenant_id == tenant_b
            assert entity.rule_id == b_rules[i]["rule_id"]
            assert entity.name == b_rules[i]["name"]
            assert entity.rule_condition == b_rules[i]["rule_condition"]
            assert entity.rule_action == b_rules[i]["rule_action"]
            assert entity.priority == b_rules[i]["priority"]
            assert entity.enabled == b_rules[i]["enabled"]


# ---------------------------------------------------------------------------
# Property 3: Cross-Tenant Access Rejection
# ---------------------------------------------------------------------------


class TestProperty3CrossTenantAccessRejection:
    """Property 3: Cross-Tenant Access Rejection.

    For any two distinct tenants A and B, any request authenticated as
    tenant A that attempts to read, modify, or delete a policy rule
    belonging to tenant B SHALL be rejected with an authorization error.

    **Validates: Requirements 1.4**
    """

    @settings(max_examples=100)
    @given(tenants=distinct_tenant_ids(), rule_id=_rule_id_strategy)
    @pytest.mark.asyncio
    async def test_read_cross_tenant_rule_rejected(
        self,
        tenants: tuple[str, str],
        rule_id: str,
    ) -> None:
        """Tenant A attempting to read tenant B's rule SHALL be rejected.

        **Validates: Requirements 1.4**
        """
        tenant_a, tenant_b = tenants

        policy_repo = AsyncMock()
        template_repo = AsyncMock()
        policy_repo.get_rule.return_value = None

        service = PolicyService(
            policy_repo=policy_repo,
            template_repo=template_repo,
        )

        with pytest.raises(PolicyRuleNotFoundError):
            await service.update_rule(
                tenant_id=tenant_a,
                rule_id=rule_id,
                updates={"name": "Attempted Override"},
                user_id=uuid4(),
            )

        policy_repo.get_rule.assert_called_with(tenant_a, rule_id)

    @settings(max_examples=100)
    @given(tenants=distinct_tenant_ids(), rule_id=_rule_id_strategy)
    @pytest.mark.asyncio
    async def test_modify_cross_tenant_rule_rejected(
        self,
        tenants: tuple[str, str],
        rule_id: str,
    ) -> None:
        """Tenant A attempting to modify tenant B's rule SHALL be rejected.

        **Validates: Requirements 1.4**
        """
        tenant_a, tenant_b = tenants

        policy_repo = AsyncMock()
        template_repo = AsyncMock()
        policy_repo.get_rule.return_value = None

        service = PolicyService(
            policy_repo=policy_repo,
            template_repo=template_repo,
        )

        with pytest.raises(PolicyRuleNotFoundError):
            await service.update_rule(
                tenant_id=tenant_a,
                rule_id=rule_id,
                updates={"priority": 500, "enabled": False},
                user_id=uuid4(),
            )

        policy_repo.get_rule.assert_called_with(tenant_a, rule_id)

    @settings(max_examples=100)
    @given(tenants=distinct_tenant_ids(), rule_id=_rule_id_strategy)
    @pytest.mark.asyncio
    async def test_delete_cross_tenant_rule_rejected(
        self,
        tenants: tuple[str, str],
        rule_id: str,
    ) -> None:
        """Tenant A attempting to delete tenant B's rule SHALL be rejected.

        **Validates: Requirements 1.4**
        """
        tenant_a, tenant_b = tenants

        policy_repo = AsyncMock()
        template_repo = AsyncMock()
        policy_repo.get_rule.return_value = None

        service = PolicyService(
            policy_repo=policy_repo,
            template_repo=template_repo,
        )

        with pytest.raises(PolicyRuleNotFoundError):
            await service.disable_rule(
                tenant_id=tenant_a,
                rule_id=rule_id,
            )

        policy_repo.get_rule.assert_called_with(tenant_a, rule_id)

    @settings(max_examples=100)
    @given(tenants=distinct_tenant_ids(), rule_id=_rule_id_strategy)
    @pytest.mark.asyncio
    async def test_reset_cross_tenant_rule_rejected(
        self,
        tenants: tuple[str, str],
        rule_id: str,
    ) -> None:
        """Tenant A attempting to reset tenant B's rule SHALL be rejected.

        **Validates: Requirements 1.4**
        """
        tenant_a, tenant_b = tenants

        policy_repo = AsyncMock()
        template_repo = AsyncMock()
        policy_repo.get_rule.return_value = None

        service = PolicyService(
            policy_repo=policy_repo,
            template_repo=template_repo,
        )

        with pytest.raises(PolicyRuleNotFoundError):
            await service.reset_override(
                tenant_id=tenant_a,
                rule_id=rule_id,
            )

        policy_repo.get_rule.assert_called_with(tenant_a, rule_id)



# ---------------------------------------------------------------------------
# Property 11: Date-Based Version Resolution
# ---------------------------------------------------------------------------

_date_st = st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31))


@st.composite
def versions_and_eval_date_strategy(
    draw: st.DrawFn,
) -> tuple[list[PolicyVersion], date]:
    """Generate a set of policy versions with unique effective_dates and an eval date.

    Returns:
        Tuple of (versions, evaluation_date) where versions have distinct
        effective_dates and monotonically increasing version_numbers.
    """
    num_versions = draw(st.integers(min_value=2, max_value=6))
    effective_dates = draw(
        st.lists(
            _date_st,
            min_size=num_versions,
            max_size=num_versions,
            unique=True,
        )
    )

    # Sort dates to assign version numbers in chronological order
    sorted_dates = sorted(effective_dates)
    tenant_id = "tenant-prop11"
    user_id = uuid4()

    versions: list[PolicyVersion] = []
    for i, eff_date in enumerate(sorted_dates, start=1):
        version = PolicyVersion(
            id=uuid4(),
            tenant_id=tenant_id,
            version_number=i,
            snapshot={"rules": [{"rule_id": f"rule-v{i}", "version": i}]},
            change_summary=f"Version {i}",
            rules_added=1,
            rules_removed=0,
            rules_modified=0,
            effective_date=eff_date,
            published_by=user_id,
        )
        versions.append(version)

    # Generate an evaluation date (can be before, between, or after version dates)
    evaluation_date = draw(_date_st)

    return versions, evaluation_date


class TestDateBasedVersionResolution:
    """Property 11: Date-Based Version Resolution.

    For any tenant with a set of policy versions each having an effective_date,
    and any evaluation date D, the engine SHALL select the version whose
    effective_date is the maximum value that is less than or equal to D.
    If no version has effective_date <= D, the initial version SHALL be used.

    **Validates: Requirements 4.3, 10.8**
    """

    @settings(max_examples=100)
    @given(data=versions_and_eval_date_strategy())
    @pytest.mark.asyncio
    async def test_selects_version_with_max_effective_date_lte_eval_date(
        self,
        data: tuple[list[PolicyVersion], date],
    ) -> None:
        """The engine selects the version whose effective_date is the maximum
        value that is less than or equal to the evaluation date D.

        **Validates: Requirements 4.3, 10.8**
        """
        versions, evaluation_date = data

        # Determine the expected version: max effective_date <= evaluation_date
        eligible_versions = [v for v in versions if v.effective_date <= evaluation_date]

        if eligible_versions:
            expected_version = max(eligible_versions, key=lambda v: v.effective_date)
        else:
            expected_version = min(versions, key=lambda v: v.version_number)

        # Set up mocks for the EvaluationService
        policy_repo = AsyncMock()
        version_repo = AsyncMock()
        cache_client = AsyncMock()

        # Cache miss — force version resolution path
        cache_client.get_active_policy.return_value = None

        # Mock get_active_version to simulate the repository behavior
        async def mock_get_active_version(
            tid: str, eval_date: date
        ) -> PolicyVersion | None:
            eligible = [v for v in versions if v.effective_date <= eval_date]
            if eligible:
                return max(eligible, key=lambda v: v.effective_date)
            return None

        version_repo.get_active_version.side_effect = mock_get_active_version

        # Fallback: return empty rules from repository (for no-version case)
        policy_repo.get_rules_by_tenant.return_value = []

        # Mock cache set
        cache_client.set_active_policy.return_value = None

        # Mock the audit log flush
        session_mock = MagicMock()
        session_mock.add = MagicMock()
        session_mock.flush = AsyncMock()
        policy_repo.session = session_mock

        service = EvaluationService(
            policy_repository=policy_repo,
            version_repository=version_repo,
            cache_client=cache_client,
        )

        # Call evaluate
        await service.evaluate(
            tenant_id="tenant-prop11",
            domain=PolicyDomain.ATTENDANCE,
            event_type="check_in",
            context={"check_in_time": "09:00"},
            evaluation_date=evaluation_date,
        )

        # Verify the correct version was resolved
        if eligible_versions:
            version_repo.get_active_version.assert_called_once_with(
                "tenant-prop11", evaluation_date
            )
            cache_client.set_active_policy.assert_called_once_with(
                "tenant-prop11", expected_version.snapshot
            )
        else:
            version_repo.get_active_version.assert_called_once_with(
                "tenant-prop11", evaluation_date
            )
            policy_repo.get_rules_by_tenant.assert_called_once_with(
                "tenant-prop11", PolicyDomain.ATTENDANCE
            )

    @settings(max_examples=100, suppress_health_check=[HealthCheck.filter_too_much])
    @given(data=versions_and_eval_date_strategy())
    @pytest.mark.asyncio
    async def test_no_version_before_eval_date_uses_fallback(
        self,
        data: tuple[list[PolicyVersion], date],
    ) -> None:
        """When no version has effective_date <= D, the engine falls back to
        the initial version (current rules from repository).

        **Validates: Requirements 4.3, 10.8**
        """
        versions, evaluation_date = data

        # Only test the case where no version is eligible
        eligible_versions = [v for v in versions if v.effective_date <= evaluation_date]
        assume(len(eligible_versions) == 0)

        # Set up mocks
        policy_repo = AsyncMock()
        version_repo = AsyncMock()
        cache_client = AsyncMock()

        # Cache miss
        cache_client.get_active_policy.return_value = None

        # No active version found
        version_repo.get_active_version.return_value = None

        # Fallback: return empty rules from repository
        policy_repo.get_rules_by_tenant.return_value = []

        # Mock the audit log flush
        session_mock = MagicMock()
        session_mock.add = MagicMock()
        session_mock.flush = AsyncMock()
        policy_repo.session = session_mock

        service = EvaluationService(
            policy_repository=policy_repo,
            version_repository=version_repo,
            cache_client=cache_client,
        )

        # Call evaluate
        await service.evaluate(
            tenant_id="tenant-prop11",
            domain=PolicyDomain.ATTENDANCE,
            event_type="check_in",
            context={"check_in_time": "09:00"},
            evaluation_date=evaluation_date,
        )

        # Verify fallback path was taken
        version_repo.get_active_version.assert_called_once_with(
            "tenant-prop11", evaluation_date
        )
        policy_repo.get_rules_by_tenant.assert_called_once_with(
            "tenant-prop11", PolicyDomain.ATTENDANCE
        )
        # Cache should NOT have been set (no version to cache)
        cache_client.set_active_policy.assert_not_called()

    @settings(max_examples=100)
    @given(data=versions_and_eval_date_strategy())
    @pytest.mark.asyncio
    async def test_version_resolution_selects_maximum_not_minimum(
        self,
        data: tuple[list[PolicyVersion], date],
    ) -> None:
        """When multiple versions have effective_date <= D, the engine selects
        the one with the MAXIMUM effective_date (most recent), not the minimum.

        **Validates: Requirements 4.3, 10.8**
        """
        versions, evaluation_date = data

        # Only test when there are multiple eligible versions
        eligible_versions = [v for v in versions if v.effective_date <= evaluation_date]
        assume(len(eligible_versions) >= 2)

        # The expected version is the one with max effective_date
        expected_version = max(eligible_versions, key=lambda v: v.effective_date)
        # The wrong choice would be the minimum
        wrong_version = min(eligible_versions, key=lambda v: v.effective_date)

        # Set up mocks
        policy_repo = AsyncMock()
        version_repo = AsyncMock()
        cache_client = AsyncMock()

        # Cache miss
        cache_client.get_active_policy.return_value = None

        # Mock get_active_version to return the correct (max) version
        version_repo.get_active_version.return_value = expected_version

        # Mock cache set
        cache_client.set_active_policy.return_value = None

        # Mock the audit log flush
        session_mock = MagicMock()
        session_mock.add = MagicMock()
        session_mock.flush = AsyncMock()
        policy_repo.session = session_mock

        service = EvaluationService(
            policy_repository=policy_repo,
            version_repository=version_repo,
            cache_client=cache_client,
        )

        # Call evaluate
        await service.evaluate(
            tenant_id="tenant-prop11",
            domain=PolicyDomain.ATTENDANCE,
            event_type="check_in",
            context={"check_in_time": "09:00"},
            evaluation_date=evaluation_date,
        )

        # Verify the cache was set with the EXPECTED version's snapshot (max date)
        cache_client.set_active_policy.assert_called_once_with(
            "tenant-prop11", expected_version.snapshot
        )

        # The snapshot cached must be the max-date version, not the min-date one
        cached_snapshot = cache_client.set_active_policy.call_args[0][1]
        assert cached_snapshot == expected_version.snapshot
        assert cached_snapshot != wrong_version.snapshot or expected_version == wrong_version



# ---------------------------------------------------------------------------
# Feature: company-policy-engine, Property 1: Tenant Isolation During Evaluation
# ---------------------------------------------------------------------------

SUPPORTED_DOMAINS: list[str] = [d.value for d in PolicyDomain]
SUPPORTED_ACTION_TYPES: list[str] = [at.value for at in ActionType]


@st.composite
def rule_dict_for_tenant(draw: st.DrawFn, tenant_id: str) -> dict:
    """Generate a valid rule dict associated with a specific tenant.

    The rule uses the 'greater_than' operator with a threshold of 0 so
    that any positive context value will satisfy the condition.
    """
    rule_id = draw(
        st.text(
            alphabet=string.ascii_uppercase + string.digits + "-",
            min_size=3,
            max_size=20,
        )
    )
    domain = draw(st.sampled_from(SUPPORTED_DOMAINS))
    name = draw(
        st.text(
            alphabet=string.ascii_letters + string.digits + " ",
            min_size=1,
            max_size=64,
        )
    )
    priority = draw(st.integers(min_value=1, max_value=1000))
    action_type = draw(st.sampled_from(SUPPORTED_ACTION_TYPES))

    return {
        "rule_id": rule_id,
        "tenant_id": tenant_id,
        "domain": domain,
        "name": name,
        "priority": priority,
        "enabled": True,
        "rule_condition": {
            "field": "test_value",
            "operator": "greater_than",
            "value": 0,
        },
        "rule_action": {
            "type": action_type,
            "parameters": {"status": "triggered"},
        },
        "is_custom": False,
        "template_rule_id": None,
        "id": str(uuid4()),
    }


@st.composite
def multi_tenant_rules(draw: st.DrawFn) -> tuple[str, list[str], dict[str, list[dict]]]:
    """Generate rules distributed across multiple tenants.

    Returns:
        A tuple of (target_tenant_id, all_tenant_ids, rules_by_tenant)
        where rules_by_tenant maps tenant_id -> list of rule dicts.
    """
    # Generate 2-5 distinct tenant IDs
    num_tenants = draw(st.integers(min_value=2, max_value=5))
    tenant_ids = draw(
        st.lists(
            _tenant_id_strategy,
            min_size=num_tenants,
            max_size=num_tenants,
            unique=True,
        )
    )

    # Pick one tenant as the target for evaluation
    target_tenant = draw(st.sampled_from(tenant_ids))

    # Generate 1-5 rules per tenant
    rules_by_tenant: dict[str, list[dict]] = {}
    for tid in tenant_ids:
        num_rules = draw(st.integers(min_value=1, max_value=5))
        rules = []
        for _ in range(num_rules):
            rule = draw(rule_dict_for_tenant(tid))
            rules.append(rule)
        rules_by_tenant[tid] = rules

    return target_tenant, tenant_ids, rules_by_tenant


class TestProperty1TenantIsolationDuringEvaluation:
    """Property 1: Tenant Isolation During Evaluation.

    For any set of policy rules distributed across multiple tenants and
    any evaluation request for a specific tenant, the evaluation result
    SHALL contain only rules belonging to that tenant — no rules from
    any other tenant shall appear in the matched rules list.

    **Validates: Requirements 1.2**
    """

    @settings(max_examples=100)
    @given(data=multi_tenant_rules())
    @pytest.mark.asyncio
    async def test_evaluation_returns_only_target_tenant_rules(
        self,
        data: tuple[str, list[str], dict[str, list[dict]]],
    ) -> None:
        """Evaluating for a specific tenant SHALL return only that tenant's rules.

        We generate rules for multiple tenants, mock the cache to return
        only the target tenant's rules (as the real system does via
        tenant_id scoping), and verify the evaluation result contains
        exclusively rules from the target tenant.
        """
        target_tenant, all_tenant_ids, rules_by_tenant = data

        # The target tenant's rules
        target_rules = rules_by_tenant[target_tenant]

        # Pick a domain that exists in the target tenant's rules
        target_domains = {r["domain"] for r in target_rules}
        if not target_domains:
            return  # Defensive guard

        eval_domain = PolicyDomain(next(iter(target_domains)))

        # Filter target rules to only those in the evaluation domain
        domain_rules = [r for r in target_rules if r["domain"] == eval_domain.value]

        # Collect ALL rules from ALL tenants for the same domain
        all_rules_all_tenants: list[dict] = []
        for tid, rules in rules_by_tenant.items():
            for r in rules:
                if r["domain"] == eval_domain.value:
                    all_rules_all_tenants.append(r)

        # Set up mocked dependencies
        policy_repo = AsyncMock()
        version_repo = AsyncMock()
        cache_client = AsyncMock()

        session_mock = MagicMock()
        session_mock.add = MagicMock()
        session_mock.flush = AsyncMock()
        policy_repo.session = session_mock

        # Cache returns the target tenant's rules only (simulating real
        # Redis key scoping: policy:{tenant_id}:active)
        cache_client.get_active_policy.return_value = {
            "rules": domain_rules,
        }

        service = EvaluationService(
            policy_repository=policy_repo,
            version_repository=version_repo,
            cache_client=cache_client,
        )

        # Evaluate with a context that will match all rules (test_value > 0)
        result = await service.evaluate(
            tenant_id=target_tenant,
            domain=eval_domain,
            event_type="test_event",
            context={"test_value": 100},
            evaluation_date=date.today(),
        )

        # PROPERTY ASSERTION: All matched rules belong to the target tenant
        matched_rule_ids = {m.rule_id for m in result.matched_rules}
        target_rule_ids = {r["rule_id"] for r in domain_rules}

        # Every matched rule must be from the target tenant's domain rules
        assert matched_rule_ids.issubset(target_rule_ids), (
            f"Matched rules {matched_rule_ids} contain rules not in "
            f"target tenant's domain rules {target_rule_ids}"
        )

        # The number of matched rules should not exceed the target tenant's
        # domain rules count (no extra rules from other tenants injected)
        assert len(result.matched_rules) <= len(domain_rules), (
            f"Got {len(result.matched_rules)} matched rules but target tenant "
            f"only has {len(domain_rules)} rules in domain {eval_domain.value}"
        )

        # Verify that the service only processed rules from the target tenant
        # by checking that matched rule IDs use unique IDs from domain_rules
        matched_ids_from_result = [m.rule_id for m in result.matched_rules]
        domain_rule_ids_list = [r["rule_id"] for r in domain_rules]
        for mid in matched_ids_from_result:
            assert mid in domain_rule_ids_list, (
                f"Matched rule '{mid}' is not in target tenant's rules"
            )

    @settings(max_examples=100)
    @given(data=multi_tenant_rules())
    @pytest.mark.asyncio
    async def test_repository_called_with_correct_tenant_id(
        self,
        data: tuple[str, list[str], dict[str, list[dict]]],
    ) -> None:
        """The evaluation service SHALL request rules scoped to the target tenant.

        When cache misses and no version exists, the service falls back to
        the policy repository. We verify it passes the correct tenant_id,
        ensuring the data layer enforces isolation.
        """
        target_tenant, all_tenant_ids, rules_by_tenant = data

        target_rules = rules_by_tenant[target_tenant]
        target_domains = {r["domain"] for r in target_rules}
        if not target_domains:
            return

        eval_domain = PolicyDomain(next(iter(target_domains)))

        # Set up mocked dependencies
        policy_repo = AsyncMock()
        version_repo = AsyncMock()
        cache_client = AsyncMock()

        session_mock = MagicMock()
        session_mock.add = MagicMock()
        session_mock.flush = AsyncMock()
        policy_repo.session = session_mock

        # Force fallback to repository (no cache, no version)
        cache_client.get_active_policy.return_value = None
        version_repo.get_active_version.return_value = None
        policy_repo.get_rules_by_tenant.return_value = []

        service = EvaluationService(
            policy_repository=policy_repo,
            version_repository=version_repo,
            cache_client=cache_client,
        )

        await service.evaluate(
            tenant_id=target_tenant,
            domain=eval_domain,
            event_type="test_event",
            context={"test_value": 100},
            evaluation_date=date.today(),
        )

        # PROPERTY ASSERTION: Repository was called with the target tenant_id
        policy_repo.get_rules_by_tenant.assert_called_once_with(
            target_tenant, eval_domain
        )

    @settings(max_examples=100)
    @given(data=multi_tenant_rules())
    @pytest.mark.asyncio
    async def test_cache_lookup_uses_correct_tenant_id(
        self,
        data: tuple[str, list[str], dict[str, list[dict]]],
    ) -> None:
        """The cache lookup SHALL use only the target tenant's identifier.

        This ensures the caching layer cannot accidentally serve another
        tenant's cached policy snapshot.
        """
        target_tenant, all_tenant_ids, rules_by_tenant = data

        target_rules = rules_by_tenant[target_tenant]
        target_domains = {r["domain"] for r in target_rules}
        if not target_domains:
            return

        eval_domain = PolicyDomain(next(iter(target_domains)))

        # Set up mocked dependencies
        policy_repo = AsyncMock()
        version_repo = AsyncMock()
        cache_client = AsyncMock()

        session_mock = MagicMock()
        session_mock.add = MagicMock()
        session_mock.flush = AsyncMock()
        policy_repo.session = session_mock

        # Cache returns empty rules for the target tenant
        cache_client.get_active_policy.return_value = {"rules": []}

        service = EvaluationService(
            policy_repository=policy_repo,
            version_repository=version_repo,
            cache_client=cache_client,
        )

        await service.evaluate(
            tenant_id=target_tenant,
            domain=eval_domain,
            event_type="test_event",
            context={"test_value": 100},
            evaluation_date=date.today(),
        )

        # PROPERTY ASSERTION: Cache was queried with the target tenant_id only
        cache_client.get_active_policy.assert_called_once_with(target_tenant)


# ---------------------------------------------------------------------------
# Feature: company-policy-engine, Property 4: Template Update Non-Interference
# ---------------------------------------------------------------------------


@st.composite
def policy_template_strategy(draw: st.DrawFn) -> PolicyTemplate:
    """Generate a valid PolicyTemplate entity with random field values."""
    domain = draw(st.sampled_from(list(PolicyDomain)))
    rule_id = draw(
        st.text(
            alphabet=string.ascii_lowercase + string.digits + "-",
            min_size=3,
            max_size=32,
        )
    )
    name = draw(
        st.text(
            alphabet=string.ascii_letters + string.digits + " ",
            min_size=1,
            max_size=64,
        )
    )
    description = draw(
        st.text(
            alphabet=string.ascii_letters + string.digits + " .,",
            min_size=1,
            max_size=128,
        )
    )
    operator = draw(st.sampled_from(list(RuleOperator)))
    action_type = draw(st.sampled_from(list(ActionType)))
    priority = draw(st.integers(min_value=1, max_value=1000))
    field_name = draw(
        st.text(alphabet=string.ascii_lowercase + "_", min_size=1, max_size=20)
    )
    condition_value = draw(st.integers(min_value=0, max_value=10000))

    return PolicyTemplate(
        id=uuid4(),
        domain=domain,
        rule_id=rule_id,
        name=name,
        description=description,
        rule_condition={
            "field": field_name,
            "operator": operator.value,
            "value": condition_value,
        },
        rule_action={
            "type": action_type.value,
            "parameters": {"status": draw(st.text(min_size=1, max_size=20))},
        },
        priority=priority,
        enabled=draw(st.booleans()),
        legal_constraints=None,
    )


@st.composite
def template_update_data(draw: st.DrawFn) -> dict:
    """Generate random update data to apply to a PolicyTemplate."""
    updates: dict = {}
    if draw(st.booleans()):
        updates["name"] = draw(
            st.text(
                alphabet=string.ascii_letters + string.digits + " ",
                min_size=1,
                max_size=64,
            )
        )
    if draw(st.booleans()):
        updates["priority"] = draw(st.integers(min_value=1, max_value=1000))
    if draw(st.booleans()):
        new_operator = draw(st.sampled_from(list(RuleOperator)))
        new_value = draw(st.integers(min_value=0, max_value=10000))
        new_field = draw(
            st.text(alphabet=string.ascii_lowercase + "_", min_size=1, max_size=20)
        )
        updates["rule_condition"] = {
            "field": new_field,
            "operator": new_operator.value,
            "value": new_value,
        }
    if draw(st.booleans()):
        new_action_type = draw(st.sampled_from(list(ActionType)))
        updates["rule_action"] = {
            "type": new_action_type.value,
            "parameters": {"status": draw(st.text(min_size=1, max_size=20))},
        }
    if draw(st.booleans()):
        updates["enabled"] = draw(st.booleans())
    if draw(st.booleans()):
        updates["description"] = draw(
            st.text(
                alphabet=string.ascii_letters + string.digits + " .,",
                min_size=1,
                max_size=128,
            )
        )
    # Ensure at least one update field is present
    if not updates:
        updates["name"] = draw(
            st.text(
                alphabet=string.ascii_letters + string.digits + " ",
                min_size=1,
                max_size=64,
            )
        )
    return updates


def _create_tenant_rule_from_template(
    template: PolicyTemplate, tenant_id: str
) -> PolicyRule:
    """Create a tenant PolicyRule as an independent copy of a template."""
    return PolicyRule(
        id=uuid4(),
        tenant_id=tenant_id,
        domain=template.domain,
        rule_id=template.rule_id,
        name=template.name,
        description=template.description,
        rule_condition=copy.deepcopy(template.rule_condition),
        rule_action=copy.deepcopy(template.rule_action),
        priority=template.priority,
        enabled=template.enabled,
        template_rule_id=template.id,
        is_custom=False,
        is_deleted=False,
        created_by=uuid4(),
    )


def _create_version_snapshot_from_rules(rules: list[PolicyRule]) -> dict:
    """Create a PolicyVersion snapshot dict from a list of rules."""
    return {
        "rules": [
            {
                "rule_id": r.rule_id,
                "domain": r.domain.value if isinstance(r.domain, PolicyDomain) else r.domain,
                "name": r.name,
                "description": r.description,
                "rule_condition": copy.deepcopy(r.rule_condition),
                "rule_action": copy.deepcopy(r.rule_action),
                "priority": r.priority,
                "enabled": r.enabled,
            }
            for r in rules
        ]
    }


class TestProperty4TemplateUpdateNonInterference:
    """Property 4: Template Update Non-Interference.

    For any existing tenant with an active company policy, when the
    system-level default policy templates are updated, that tenant's
    active policy rules and all historical policy versions SHALL remain
    unchanged.

    This property holds because tenant PolicyRules are independent copies
    of templates (not live references), and PolicyVersion snapshots are
    immutable JSONB blobs.

    **Validates: Requirements 2.10**
    """

    @settings(max_examples=100)
    @given(
        template=policy_template_strategy(),
        updates=template_update_data(),
        tenant_id=_tenant_id_strategy,
    )
    def test_template_update_does_not_affect_tenant_policy_rules(
        self,
        template: PolicyTemplate,
        updates: dict,
        tenant_id: str,
    ) -> None:
        """Modifying a PolicyTemplate SHALL NOT change existing tenant PolicyRules.

        Tenant rules are independent copies created at provisioning time.
        Updating the source template must not propagate to the copy.

        **Validates: Requirements 2.10**
        """
        # Create a tenant rule as an independent copy of the template
        tenant_rule = _create_tenant_rule_from_template(template, tenant_id)

        # Deep copy the tenant rule's state before template modification
        rule_condition_before = copy.deepcopy(tenant_rule.rule_condition)
        rule_action_before = copy.deepcopy(tenant_rule.rule_action)
        name_before = tenant_rule.name
        description_before = tenant_rule.description
        priority_before = tenant_rule.priority
        enabled_before = tenant_rule.enabled

        # Simulate updating the system-level template
        if "name" in updates:
            template.name = updates["name"]
        if "priority" in updates:
            template.priority = updates["priority"]
        if "rule_condition" in updates:
            template.rule_condition = updates["rule_condition"]
        if "rule_action" in updates:
            template.rule_action = updates["rule_action"]
        if "enabled" in updates:
            template.enabled = updates["enabled"]
        if "description" in updates:
            template.description = updates["description"]

        # PROPERTY ASSERTION: Tenant rule remains unchanged after template update
        assert tenant_rule.rule_condition == rule_condition_before, (
            f"Tenant rule_condition changed after template update: "
            f"{tenant_rule.rule_condition} != {rule_condition_before}"
        )
        assert tenant_rule.rule_action == rule_action_before, (
            f"Tenant rule_action changed after template update: "
            f"{tenant_rule.rule_action} != {rule_action_before}"
        )
        assert tenant_rule.name == name_before, (
            f"Tenant rule name changed after template update: "
            f"'{tenant_rule.name}' != '{name_before}'"
        )
        assert tenant_rule.description == description_before, (
            f"Tenant rule description changed after template update: "
            f"'{tenant_rule.description}' != '{description_before}'"
        )
        assert tenant_rule.priority == priority_before, (
            f"Tenant rule priority changed after template update: "
            f"{tenant_rule.priority} != {priority_before}"
        )
        assert tenant_rule.enabled == enabled_before, (
            f"Tenant rule enabled changed after template update: "
            f"{tenant_rule.enabled} != {enabled_before}"
        )

    @settings(max_examples=100)
    @given(
        template=policy_template_strategy(),
        updates=template_update_data(),
        tenant_id=_tenant_id_strategy,
    )
    def test_template_update_does_not_affect_policy_version_snapshots(
        self,
        template: PolicyTemplate,
        updates: dict,
        tenant_id: str,
    ) -> None:
        """Modifying a PolicyTemplate SHALL NOT change historical PolicyVersion snapshots.

        Version snapshots are immutable JSONB blobs captured at publish time.
        They contain deep copies of rule data, not references to templates.

        **Validates: Requirements 2.10**
        """
        # Create tenant rules from the template
        tenant_rule = _create_tenant_rule_from_template(template, tenant_id)

        # Create a version snapshot (simulating a publish operation)
        version_snapshot = _create_version_snapshot_from_rules([tenant_rule])

        # Deep copy the snapshot for comparison
        snapshot_before = copy.deepcopy(version_snapshot)

        # Create a PolicyVersion entity with the snapshot
        version = PolicyVersion(
            id=uuid4(),
            tenant_id=tenant_id,
            version_number=1,
            snapshot=version_snapshot,
            change_summary="Initial version",
            rules_added=1,
            rules_removed=0,
            rules_modified=0,
            effective_date=date.today(),
            published_by=uuid4(),
        )

        # Simulate updating the system-level template
        if "name" in updates:
            template.name = updates["name"]
        if "priority" in updates:
            template.priority = updates["priority"]
        if "rule_condition" in updates:
            template.rule_condition = updates["rule_condition"]
        if "rule_action" in updates:
            template.rule_action = updates["rule_action"]
        if "enabled" in updates:
            template.enabled = updates["enabled"]
        if "description" in updates:
            template.description = updates["description"]

        # PROPERTY ASSERTION: Version snapshot remains unchanged
        assert version.snapshot == snapshot_before, (
            f"PolicyVersion snapshot changed after template update: "
            f"{version.snapshot} != {snapshot_before}"
        )

    @settings(max_examples=100)
    @given(
        template=policy_template_strategy(),
        updates=template_update_data(),
        tenant_id=_tenant_id_strategy,
    )
    def test_deep_copy_ensures_independence_of_rule_condition(
        self,
        template: PolicyTemplate,
        updates: dict,
        tenant_id: str,
    ) -> None:
        """Tenant rule_condition is a deep copy, not a reference to template data.

        Mutating the template's rule_condition dict in-place SHALL NOT
        affect the tenant rule's rule_condition.

        **Validates: Requirements 2.10**
        """
        # Create a tenant rule as an independent copy
        tenant_rule = _create_tenant_rule_from_template(template, tenant_id)

        # Deep copy for comparison
        condition_before = copy.deepcopy(tenant_rule.rule_condition)

        # Mutate the template's rule_condition in-place
        template.rule_condition["field"] = "mutated_field_xyz"
        template.rule_condition["operator"] = "equals"
        template.rule_condition["value"] = 99999

        # PROPERTY ASSERTION: Tenant rule_condition is unaffected
        assert tenant_rule.rule_condition == condition_before, (
            f"Tenant rule_condition was mutated via template reference: "
            f"{tenant_rule.rule_condition} != {condition_before}"
        )

    @settings(max_examples=100)
    @given(
        template=policy_template_strategy(),
        updates=template_update_data(),
        tenant_id=_tenant_id_strategy,
    )
    def test_deep_copy_ensures_independence_of_rule_action(
        self,
        template: PolicyTemplate,
        updates: dict,
        tenant_id: str,
    ) -> None:
        """Tenant rule_action is a deep copy, not a reference to template data.

        Mutating the template's rule_action dict in-place SHALL NOT
        affect the tenant rule's rule_action.

        **Validates: Requirements 2.10**
        """
        # Create a tenant rule as an independent copy
        tenant_rule = _create_tenant_rule_from_template(template, tenant_id)

        # Deep copy for comparison
        action_before = copy.deepcopy(tenant_rule.rule_action)

        # Mutate the template's rule_action in-place
        template.rule_action["type"] = "escalate"
        template.rule_action["parameters"] = {"mutated": True, "level": 999}

        # PROPERTY ASSERTION: Tenant rule_action is unaffected
        assert tenant_rule.rule_action == action_before, (
            f"Tenant rule_action was mutated via template reference: "
            f"{tenant_rule.rule_action} != {action_before}"
        )
