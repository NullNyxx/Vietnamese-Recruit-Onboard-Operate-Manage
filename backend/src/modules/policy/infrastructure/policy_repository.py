"""Repository for PolicyRule entity CRUD operations.

Provides async database access for policy rule listing, retrieval,
creation, update, and soft-delete operations scoped by tenant_id
using SQLAlchemy async sessions with SQLModel.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import asc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.modules.policy.domain.entities import PolicyRule
from src.modules.policy.domain.enums import PolicyDomain


class PolicyRepository:
    """Handles PolicyRule entity persistence using async SQLAlchemy sessions.

    All operations are scoped by tenant_id to enforce multi-tenant
    isolation. Queries exclude soft-deleted records by default.

    Attributes:
        session: The async database session for executing queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with an async database session.

        Args:
            session: An SQLAlchemy AsyncSession instance for database operations.
        """
        self.session = session

    async def get_rules_by_tenant(
        self,
        tenant_id: str,
        domain: PolicyDomain | None = None,
    ) -> list[PolicyRule]:
        """Retrieve all active policy rules for a tenant.

        Returns non-deleted rules for the specified tenant, optionally
        filtered by policy domain. Results are ordered by priority
        ascending, then rule_id alphabetically.

        Args:
            tenant_id: The tenant identifier to scope the query.
            domain: Optional policy domain filter.

        Returns:
            A list of PolicyRule entities matching the criteria.
        """
        statement = select(PolicyRule).where(
            PolicyRule.tenant_id == tenant_id,
            PolicyRule.is_deleted == False,  # noqa: E712
        )

        if domain is not None:
            statement = statement.where(PolicyRule.domain == domain)

        statement = statement.order_by(
            asc(PolicyRule.priority),  # type: ignore[arg-type]
            asc(PolicyRule.rule_id),
        )

        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_rule(
        self,
        tenant_id: str,
        rule_id: str,
    ) -> PolicyRule | None:
        """Retrieve a single active policy rule by tenant and rule_id.

        Args:
            tenant_id: The tenant identifier to scope the query.
            rule_id: The rule identifier (unique within a tenant).

        Returns:
            The PolicyRule entity if found and not deleted, None otherwise.
        """
        statement = select(PolicyRule).where(
            PolicyRule.tenant_id == tenant_id,
            PolicyRule.rule_id == rule_id,
            PolicyRule.is_deleted == False,  # noqa: E712
        )

        result = await self.session.execute(statement)
        return result.scalars().first()

    async def create_rule(self, rule: PolicyRule) -> PolicyRule:
        """Persist a new policy rule to the database.

        Args:
            rule: The PolicyRule entity to create.

        Returns:
            The persisted PolicyRule entity with generated fields populated.
        """
        self.session.add(rule)
        await self.session.flush()
        return rule

    async def update_rule(
        self,
        tenant_id: str,
        rule_id: str,
        data: dict[str, Any],
    ) -> PolicyRule | None:
        """Update an existing policy rule with partial data.

        Only the fields present in the data dict are updated.
        The updated_at timestamp is always refreshed. The query is
        scoped by tenant_id to enforce isolation.

        Args:
            tenant_id: The tenant identifier to scope the query.
            rule_id: The rule identifier of the rule to update.
            data: A dictionary of field names to new values.

        Returns:
            The updated PolicyRule entity if found, None otherwise.
        """
        statement = select(PolicyRule).where(
            PolicyRule.tenant_id == tenant_id,
            PolicyRule.rule_id == rule_id,
            PolicyRule.is_deleted == False,  # noqa: E712
        )
        result = await self.session.execute(statement)
        rule = result.scalars().first()

        if rule is None:
            return None

        for key, value in data.items():
            if hasattr(rule, key):
                setattr(rule, key, value)

        rule.updated_at = datetime.now(UTC)
        self.session.add(rule)
        await self.session.flush()
        return rule

    async def soft_delete_rule(
        self,
        tenant_id: str,
        rule_id: str,
    ) -> PolicyRule | None:
        """Soft-delete a policy rule by setting is_deleted=True.

        The query is scoped by tenant_id to enforce isolation.

        Args:
            tenant_id: The tenant identifier to scope the query.
            rule_id: The rule identifier of the rule to soft-delete.

        Returns:
            The updated PolicyRule entity if found, None otherwise.
        """
        statement = select(PolicyRule).where(
            PolicyRule.tenant_id == tenant_id,
            PolicyRule.rule_id == rule_id,
            PolicyRule.is_deleted == False,  # noqa: E712
        )
        result = await self.session.execute(statement)
        rule = result.scalars().first()

        if rule is None:
            return None

        rule.is_deleted = True
        rule.updated_at = datetime.now(UTC)
        self.session.add(rule)
        await self.session.flush()
        return rule

    async def count_custom_rules(self, tenant_id: str) -> int:
        """Count active custom rules for a tenant.

        Used to enforce the 500 custom rule limit per tenant.
        Only counts rules where is_custom=True and is_deleted=False.

        Args:
            tenant_id: The tenant identifier to scope the query.

        Returns:
            The number of active custom rules for the tenant.
        """
        statement = (
            select(func.count())
            .select_from(PolicyRule)
            .where(
                PolicyRule.tenant_id == tenant_id,
                PolicyRule.is_custom == True,  # noqa: E712
                PolicyRule.is_deleted == False,  # noqa: E712
            )
        )

        result = await self.session.execute(statement)
        return result.scalar_one()

    async def get_rule_by_uuid(
        self,
        tenant_id: str,
        rule_uuid: UUID,
    ) -> PolicyRule | None:
        """Retrieve a single active policy rule by tenant and primary key UUID.

        Args:
            tenant_id: The tenant identifier to scope the query.
            rule_uuid: The UUID primary key of the rule.

        Returns:
            The PolicyRule entity if found and not deleted, None otherwise.
        """
        statement = select(PolicyRule).where(
            PolicyRule.tenant_id == tenant_id,
            PolicyRule.id == rule_uuid,
            PolicyRule.is_deleted == False,  # noqa: E712
        )

        result = await self.session.execute(statement)
        return result.scalars().first()
