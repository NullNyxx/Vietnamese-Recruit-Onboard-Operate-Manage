"""Audit logging service for the Policy Engine module.

Provides centralized audit logging for policy operations including
rule CRUD, version creation, and cross-tenant access attempts.
Stores entries in the policy_audit_logs table.

Requirements: 1.7, 4.7, 10.7
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.policy.domain.entities import PolicyAuditLog

logger = logging.getLogger(__name__)


class PolicyAuditService:
    """Service for recording audit log entries for policy operations.

    Provides methods for logging rule CRUD operations, version creation,
    cross-tenant access attempts, and other policy-related actions.

    Attributes:
        session: The async database session for persisting audit logs.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize PolicyAuditService with a database session.

        Args:
            session: The async database session for persisting audit logs.
        """
        self._session = session

    async def log_rule_created(
        self,
        tenant_id: str,
        user_id: UUID,
        rule_id: str,
        domain: str,
        rule_name: str,
    ) -> None:
        """Log a policy rule creation event.

        Args:
            tenant_id: The tenant identifier.
            user_id: The UUID of the user who created the rule.
            rule_id: The rule identifier.
            domain: The policy domain of the rule.
            rule_name: The name of the created rule.
        """
        await self._create_log(
            tenant_id=tenant_id,
            user_id=user_id,
            action_type="rule_created",
            details={
                "rule_id": rule_id,
                "domain": domain,
                "rule_name": rule_name,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    async def log_rule_updated(
        self,
        tenant_id: str,
        user_id: UUID,
        rule_id: str,
        changes: dict[str, Any],
    ) -> None:
        """Log a policy rule update event.

        Args:
            tenant_id: The tenant identifier.
            user_id: The UUID of the user who updated the rule.
            rule_id: The rule identifier.
            changes: Dictionary of field names that were changed.
        """
        await self._create_log(
            tenant_id=tenant_id,
            user_id=user_id,
            action_type="rule_updated",
            details={
                "rule_id": rule_id,
                "changed_fields": list(changes.keys()),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    async def log_rule_disabled(
        self,
        tenant_id: str,
        user_id: UUID,
        rule_id: str,
        is_custom: bool,
    ) -> None:
        """Log a policy rule disable/soft-delete event.

        Args:
            tenant_id: The tenant identifier.
            user_id: The UUID of the user who disabled the rule.
            rule_id: The rule identifier.
            is_custom: Whether the rule is a custom rule (soft-deleted)
                or template-based (disabled).
        """
        action = "rule_soft_deleted" if is_custom else "rule_disabled"
        await self._create_log(
            tenant_id=tenant_id,
            user_id=user_id,
            action_type=action,
            details={
                "rule_id": rule_id,
                "is_custom": is_custom,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    async def log_rule_reset(
        self,
        tenant_id: str,
        user_id: UUID,
        rule_id: str,
    ) -> None:
        """Log a policy rule reset-to-template event.

        Args:
            tenant_id: The tenant identifier.
            user_id: The UUID of the user who reset the rule.
            rule_id: The rule identifier.
        """
        await self._create_log(
            tenant_id=tenant_id,
            user_id=user_id,
            action_type="rule_reset",
            details={
                "rule_id": rule_id,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    async def log_cross_tenant_access_attempt(
        self,
        requesting_tenant_id: str,
        requesting_user_id: UUID,
        target_tenant_id: str,
        action: str,
        resource_id: str | None = None,
    ) -> None:
        """Log a rejected cross-tenant access attempt.

        Records when a user attempts to access resources belonging
        to a different tenant. This is required by Requirement 1.7.

        Args:
            requesting_tenant_id: The tenant ID of the requesting user.
            requesting_user_id: The UUID of the requesting user.
            target_tenant_id: The tenant ID being accessed.
            action: The action attempted (read, update, delete, etc.).
            resource_id: Optional identifier of the target resource.
        """
        await self._create_log(
            tenant_id=requesting_tenant_id,
            user_id=requesting_user_id,
            action_type="cross_tenant_access_rejected",
            details={
                "target_tenant_id": target_tenant_id,
                "action_attempted": action,
                "resource_id": resource_id,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    async def log_version_created(
        self,
        tenant_id: str,
        user_id: UUID,
        version_number: int,
        change_summary: str,
        rules_added: int,
        rules_removed: int,
        rules_modified: int,
    ) -> None:
        """Log a policy version creation event.

        Records every policy version publication with actor, timestamp,
        version number, and change summary with counts. Required by
        Requirement 4.7.

        Args:
            tenant_id: The tenant identifier.
            user_id: The UUID of the user who published the version.
            version_number: The new version number.
            change_summary: Human-readable summary of changes.
            rules_added: Count of rules added in this version.
            rules_removed: Count of rules removed in this version.
            rules_modified: Count of rules modified in this version.
        """
        await self._create_log(
            tenant_id=tenant_id,
            user_id=user_id,
            action_type="version_published",
            details={
                "version_number": version_number,
                "change_summary": change_summary,
                "rules_added": rules_added,
                "rules_removed": rules_removed,
                "rules_modified": rules_modified,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    async def _create_log(
        self,
        tenant_id: str,
        user_id: UUID,
        action_type: str,
        details: dict[str, Any],
    ) -> None:
        """Create and persist an audit log entry.

        Args:
            tenant_id: The tenant identifier.
            user_id: The UUID of the acting user.
            action_type: The type of action being logged.
            details: Additional details about the action.
        """
        audit_log = PolicyAuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action_type=action_type,
            details=details,
        )

        try:
            self._session.add(audit_log)
            await self._session.flush()
        except Exception as exc:
            logger.warning(
                "Failed to persist audit log for tenant '%s', action '%s': %s",
                tenant_id,
                action_type,
                exc,
            )
