"""FastAPI router for policy management endpoints.

Defines the /api/policies/* endpoints for managing policy rules,
publishing versions, viewing version history, computing diffs,
performing rollbacks, and retrying template initialization.
All endpoints require the authenticated user to have the Admin role.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query

from src.modules.policy.api.schemas import (
    PolicyDiffResponse,
    PolicyRuleCreateRequest,
    PolicyRuleResponse,
    PolicyRuleUpdateRequest,
    PolicyVersionListResponse,
    PolicyVersionResponse,
    PublishRequest,
    RuleDiffEntry,
)
from src.modules.policy.application.policy_service import PolicyService
from src.modules.policy.application.template_service import TemplateService
from src.modules.policy.application.version_service import VersionService
from src.modules.policy.container import (
    PolicyAdminDep,
    get_policy_service,
    get_template_service,
    get_version_repository,
    get_version_service,
)
from src.modules.policy.domain.exceptions import (
    PolicyRuleNotFoundError,
    TemplateRuleDeletionError,
)
from src.modules.policy.infrastructure.version_repository import VersionRepository

logger = logging.getLogger(__name__)

policy_router = APIRouter(prefix="/api/policies", tags=["policies"])


def _get_tenant_id(user: Any) -> str:
    """Extract the tenant identifier from the authenticated user.

    Uses the user's ID as the tenant identifier. In a full multi-tenant
    deployment, this would be replaced with an organization/company lookup.

    Args:
        user: The authenticated User entity.

    Returns:
        The tenant identifier string.
    """
    return str(user.id)


# ---------------------------------------------------------------------------
# Policy Rules CRUD
# ---------------------------------------------------------------------------


@policy_router.get("/rules", response_model=dict[str, list[PolicyRuleResponse]])
async def list_rules(
    admin_user: PolicyAdminDep,
    policy_service: PolicyService = Depends(get_policy_service),
) -> dict[str, list[PolicyRuleResponse]]:
    """List all policy rules for the authenticated tenant, grouped by domain.

    Returns all active (non-deleted) rules for the admin's tenant,
    organized by policy domain.

    Args:
        admin_user: The authenticated admin user.
        policy_service: The PolicyService for rule retrieval.

    Returns:
        A dict mapping domain names to lists of PolicyRuleResponse.
    """
    tenant_id = _get_tenant_id(admin_user)
    rules = await policy_service.policy_repo.get_rules_by_tenant(tenant_id)

    grouped: dict[str, list[PolicyRuleResponse]] = {}
    for rule in rules:
        domain_key = rule.domain.value if hasattr(rule.domain, "value") else str(rule.domain)
        if domain_key not in grouped:
            grouped[domain_key] = []
        grouped[domain_key].append(PolicyRuleResponse.model_validate(rule))

    return grouped


@policy_router.post("/rules", response_model=PolicyRuleResponse, status_code=201)
async def create_rule(
    body: PolicyRuleCreateRequest,
    admin_user: PolicyAdminDep,
    policy_service: PolicyService = Depends(get_policy_service),
) -> PolicyRuleResponse:
    """Create a new custom policy rule for the authenticated tenant.

    Validates the rule structure, enforces the 500 custom rule limit,
    and persists the rule.

    Args:
        body: The rule creation request payload.
        admin_user: The authenticated admin user.
        policy_service: The PolicyService for rule creation.

    Returns:
        The created PolicyRuleResponse.

    Raises:
        CustomRuleLimitError: If the tenant has reached 500 custom rules.
        PolicyValidationError: If the rule data fails validation.
    """
    tenant_id = _get_tenant_id(admin_user)

    rule_data: dict[str, Any] = {
        "domain": body.domain.value,
        "rule_id": body.rule_id,
        "name": body.name,
        "description": body.description,
        "rule_condition": body.rule_condition.model_dump(),
        "rule_action": body.rule_action.model_dump(),
        "priority": body.priority,
        "enabled": body.enabled,
    }

    rule = await policy_service.create_custom_rule(
        tenant_id=tenant_id,
        rule_data=rule_data,
        user_id=admin_user.id,
    )

    return PolicyRuleResponse.model_validate(rule)


@policy_router.put("/rules/{rule_id}", response_model=PolicyRuleResponse)
async def update_rule(
    rule_id: str,
    body: PolicyRuleUpdateRequest,
    admin_user: PolicyAdminDep,
    policy_service: PolicyService = Depends(get_policy_service),
) -> PolicyRuleResponse:
    """Update an existing policy rule or create an override for a template rule.

    Only provided fields are updated. For template-based rules, this
    creates/updates the tenant's override. Legal minimum constraints
    and type validation are enforced.

    Args:
        rule_id: The rule identifier to update.
        body: The update request payload with optional fields.
        admin_user: The authenticated admin user.
        policy_service: The PolicyService for rule updates.

    Returns:
        The updated PolicyRuleResponse.

    Raises:
        PolicyRuleNotFoundError: If the rule does not exist for the tenant.
        LegalMinimumViolationError: If an update violates legal minimums.
        PolicyValidationError: If update values fail type validation.
    """
    tenant_id = _get_tenant_id(admin_user)

    # Build updates dict from non-None fields
    updates: dict[str, Any] = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.description is not None:
        updates["description"] = body.description
    if body.rule_condition is not None:
        updates["rule_condition"] = body.rule_condition.model_dump()
    if body.rule_action is not None:
        updates["rule_action"] = body.rule_action.model_dump()
    if body.priority is not None:
        updates["priority"] = body.priority
    if body.enabled is not None:
        updates["enabled"] = body.enabled

    rule = await policy_service.update_rule(
        tenant_id=tenant_id,
        rule_id=rule_id,
        updates=updates,
        user_id=admin_user.id,
    )

    return PolicyRuleResponse.model_validate(rule)


@policy_router.delete("/rules/{rule_id}", response_model=PolicyRuleResponse)
async def delete_rule(
    rule_id: str,
    admin_user: PolicyAdminDep,
    policy_service: PolicyService = Depends(get_policy_service),
) -> PolicyRuleResponse:
    """Soft delete a custom policy rule.

    For custom rules, performs a soft delete (is_deleted=True).
    For template-based rules, rejects the deletion with an error
    indicating that template rules can only be disabled via PUT.

    Args:
        rule_id: The rule identifier to delete.
        admin_user: The authenticated admin user.
        policy_service: The PolicyService for rule deletion.

    Returns:
        The updated PolicyRuleResponse (with is_deleted=True).

    Raises:
        PolicyRuleNotFoundError: If the rule does not exist for the tenant.
        TemplateRuleDeletionError: If attempting to delete a template rule.
    """
    tenant_id = _get_tenant_id(admin_user)

    # Check if the rule is template-based before attempting deletion
    rule = await policy_service.policy_repo.get_rule(tenant_id, rule_id)
    if rule is None:
        raise PolicyRuleNotFoundError()

    if not rule.is_custom:
        raise TemplateRuleDeletionError()

    deleted_rule = await policy_service.disable_rule(
        tenant_id=tenant_id,
        rule_id=rule_id,
    )

    return PolicyRuleResponse.model_validate(deleted_rule)


# ---------------------------------------------------------------------------
# Publish
# ---------------------------------------------------------------------------


@policy_router.post("/publish", response_model=PolicyVersionResponse, status_code=201)
async def publish_version(
    body: PublishRequest,
    admin_user: PolicyAdminDep,
    version_service: VersionService = Depends(get_version_service),
) -> PolicyVersionResponse:
    """Create a new policy version from the current draft state.

    Takes a snapshot of all active rules, assigns a monotonically
    increasing version number, and invalidates the Redis cache.

    Args:
        body: The publish request with effective_date and change_summary.
        admin_user: The authenticated admin user.
        version_service: The VersionService for publishing.

    Returns:
        The newly created PolicyVersionResponse.
    """
    tenant_id = _get_tenant_id(admin_user)

    effective = body.effective_date if body.effective_date else date.today()

    version = await version_service.publish(
        tenant_id=tenant_id,
        user_id=admin_user.id,
        effective_date=effective,
        change_summary=body.change_summary,
    )

    return PolicyVersionResponse.model_validate(version)


# ---------------------------------------------------------------------------
# Version History
# ---------------------------------------------------------------------------


@policy_router.get("/versions", response_model=PolicyVersionListResponse)
async def list_versions(
    admin_user: PolicyAdminDep,
    version_repo: VersionRepository = Depends(get_version_repository),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page (max 100)"),
) -> PolicyVersionListResponse:
    """List paginated version history for the authenticated tenant.

    Returns versions ordered by version_number descending (newest first).

    Args:
        admin_user: The authenticated admin user.
        version_repo: The VersionRepository for querying versions.
        page: The page number (1-indexed, default 1).
        page_size: Items per page (default 20, max 100).

    Returns:
        A paginated PolicyVersionListResponse.
    """
    tenant_id = _get_tenant_id(admin_user)

    versions = await version_repo.get_versions(
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
    )
    total = await version_repo.count_versions(tenant_id)

    return PolicyVersionListResponse(
        items=[PolicyVersionResponse.model_validate(v) for v in versions],
        total=total,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# Version Diff
# ---------------------------------------------------------------------------


@policy_router.get(
    "/versions/{version_number}/diff/{other_version}",
    response_model=PolicyDiffResponse,
)
async def diff_versions(
    version_number: int,
    other_version: int,
    admin_user: PolicyAdminDep,
    version_service: VersionService = Depends(get_version_service),
) -> PolicyDiffResponse:
    """Compute the diff between two policy versions.

    Categorizes every rule as added, removed, modified, or unchanged
    between the two specified versions.

    Args:
        version_number: The first (base) version number.
        other_version: The second (target) version number.
        admin_user: The authenticated admin user.
        version_service: The VersionService for diff computation.

    Returns:
        A PolicyDiffResponse with categorized rule changes.

    Raises:
        PolicyVersionNotFoundError: If either version does not exist.
    """
    tenant_id = _get_tenant_id(admin_user)

    diff_result = await version_service.diff(
        tenant_id=tenant_id,
        version_a=version_number,
        version_b=other_version,
    )

    return PolicyDiffResponse(
        version_a=version_number,
        version_b=other_version,
        rules_added=[
            RuleDiffEntry(
                rule_id=r.get("rule_id", ""),
                name=r.get("name", ""),
                details=r.get("details"),
            )
            for r in diff_result.added
        ],
        rules_removed=[
            RuleDiffEntry(
                rule_id=r.get("rule_id", ""),
                name=r.get("name", ""),
                details=r.get("details"),
            )
            for r in diff_result.removed
        ],
        rules_modified=[
            RuleDiffEntry(
                rule_id=r.get("rule_id", ""),
                name=r.get("name", ""),
                details=r.get("details"),
            )
            for r in diff_result.modified
        ],
        rules_unchanged=[
            RuleDiffEntry(
                rule_id=r.get("rule_id", ""),
                name=r.get("name", ""),
                details=r.get("details"),
            )
            for r in diff_result.unchanged
        ],
    )


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------


@policy_router.post(
    "/versions/{version_number}/rollback",
    response_model=PolicyVersionResponse,
    status_code=201,
)
async def rollback_version(
    version_number: int,
    admin_user: PolicyAdminDep,
    version_service: VersionService = Depends(get_version_service),
) -> PolicyVersionResponse:
    """Rollback to a previous policy version.

    Creates a new version with the target version's snapshot,
    following the same publish flow (new version number, cache
    invalidation, audit log).

    Args:
        version_number: The target version number to rollback to.
        admin_user: The authenticated admin user.
        version_service: The VersionService for rollback.

    Returns:
        The newly created PolicyVersionResponse (with rolled-back snapshot).

    Raises:
        PolicyVersionNotFoundError: If the target version does not exist.
    """
    tenant_id = _get_tenant_id(admin_user)

    version = await version_service.rollback(
        tenant_id=tenant_id,
        target_version=version_number,
        user_id=admin_user.id,
    )

    return PolicyVersionResponse.model_validate(version)


# ---------------------------------------------------------------------------
# Template Retry
# ---------------------------------------------------------------------------


@policy_router.post("/templates/retry/{tenant_id}", status_code=200)
async def retry_template_initialization(
    tenant_id: str,
    admin_user: PolicyAdminDep,
    template_service: TemplateService = Depends(get_template_service),
) -> dict[str, Any]:
    """Retry failed template initialization for a tenant.

    When template provisioning fails during tenant registration,
    this endpoint allows an admin to retry the operation.

    Args:
        tenant_id: The tenant identifier to retry initialization for.
        admin_user: The authenticated admin user.
        template_service: The TemplateService for provisioning.

    Returns:
        A dict with status and count of provisioned rules.

    Raises:
        TemplateInitializationError: If the retry also fails.
    """
    rules = await template_service.provision_templates(
        tenant_id=tenant_id,
        system_user_id=admin_user.id,
    )

    return {
        "status": "success",
        "tenant_id": tenant_id,
        "rules_provisioned": len(rules),
    }
