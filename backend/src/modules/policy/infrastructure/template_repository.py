"""Repository for PolicyTemplate entity read-only queries.

Provides async database access for retrieving policy templates
by domain or rule_id. Templates are populated via seed data/migrations
and are not modified at runtime.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.modules.policy.domain.entities import PolicyTemplate
from src.modules.policy.domain.enums import PolicyDomain


class TemplateRepository:
    """Handles PolicyTemplate entity retrieval using async SQLAlchemy sessions.

    This is a read-only repository — templates are populated via seed
    data or migrations and shared across all tenants.

    Attributes:
        session: The async database session for executing queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with an async database session.

        Args:
            session: An SQLAlchemy AsyncSession instance for database operations.
        """
        self.session = session

    async def get_all_templates(self) -> list[PolicyTemplate]:
        """Retrieve all policy templates from the database.

        Returns templates ordered by domain and priority for consistent
        ordering across calls.

        Returns:
            A list of all PolicyTemplate entities.
        """
        statement = select(PolicyTemplate).order_by(
            PolicyTemplate.domain,  # type: ignore[arg-type]
            PolicyTemplate.priority,  # type: ignore[arg-type]
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_templates_by_domain(self, domain: PolicyDomain) -> list[PolicyTemplate]:
        """Retrieve all policy templates for a specific domain.

        Args:
            domain: The PolicyDomain enum value to filter by.

        Returns:
            A list of PolicyTemplate entities matching the given domain,
            ordered by priority ascending.
        """
        statement = (
            select(PolicyTemplate)
            .where(PolicyTemplate.domain == domain)  # type: ignore[arg-type]
            .order_by(PolicyTemplate.priority)  # type: ignore[arg-type]
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_template(self, rule_id: str) -> PolicyTemplate | None:
        """Retrieve a single policy template by its unique rule_id.

        Args:
            rule_id: The unique rule identifier string.

        Returns:
            The matching PolicyTemplate entity, or None if not found.
        """
        statement = select(PolicyTemplate).where(PolicyTemplate.rule_id == rule_id)
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def get_template_by_uuid(self, template_id: UUID) -> PolicyTemplate | None:
        """Retrieve a single policy template by its UUID primary key.

        Args:
            template_id: The UUID primary key of the template.

        Returns:
            The matching PolicyTemplate entity, or None if not found.
        """
        statement = select(PolicyTemplate).where(PolicyTemplate.id == template_id)
        result = await self.session.execute(statement)
        return result.scalars().first()
