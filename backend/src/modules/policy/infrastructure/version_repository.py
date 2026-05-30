"""Repository for PolicyVersion entity operations.

Provides async database access for policy version storage and retrieval,
including paginated listing, date-based resolution, and version number
management.
"""

from datetime import date

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.modules.policy.domain.entities import PolicyVersion


class VersionRepository:
    """Handles PolicyVersion entity persistence using async SQLAlchemy sessions.

    Attributes:
        session: The async database session for executing queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with an async database session.

        Args:
            session: An SQLAlchemy AsyncSession instance for database operations.
        """
        self.session = session

    async def create_version(self, version: PolicyVersion) -> PolicyVersion:
        """Persist a new PolicyVersion record.

        Args:
            version: The PolicyVersion entity to persist.

        Returns:
            The persisted PolicyVersion entity with any generated fields populated.
        """
        self.session.add(version)
        await self.session.flush()
        return version

    async def get_versions(
        self,
        tenant_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> list[PolicyVersion]:
        """Retrieve a paginated list of versions for a tenant.

        Results are ordered by version_number descending (newest first).

        Args:
            tenant_id: The tenant identifier to filter by.
            page: The page number (1-indexed).
            page_size: The number of results per page.

        Returns:
            A list of PolicyVersion entities for the requested page.
        """
        offset = (page - 1) * page_size
        statement = (
            select(PolicyVersion)
            .where(PolicyVersion.tenant_id == tenant_id)
            .order_by(PolicyVersion.version_number.desc())  # type: ignore[attr-defined]
            .offset(offset)
            .limit(page_size)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_version(
        self,
        tenant_id: str,
        version_number: int,
    ) -> PolicyVersion | None:
        """Find a specific version by tenant_id and version_number.

        Args:
            tenant_id: The tenant identifier.
            version_number: The version number to look up.

        Returns:
            The PolicyVersion entity if found, None otherwise.
        """
        statement = select(PolicyVersion).where(
            PolicyVersion.tenant_id == tenant_id,
            PolicyVersion.version_number == version_number,
        )
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def get_active_version(
        self,
        tenant_id: str,
        evaluation_date: date,
    ) -> PolicyVersion | None:
        """Find the active version for a tenant on a given date.

        Returns the version whose effective_date is the maximum value
        less than or equal to the given evaluation date (the most recent
        effective version as of that date).

        Args:
            tenant_id: The tenant identifier.
            evaluation_date: The date to resolve the active version for.

        Returns:
            The active PolicyVersion if one exists, None otherwise.
        """
        statement = (
            select(PolicyVersion)
            .where(
                PolicyVersion.tenant_id == tenant_id,
                PolicyVersion.effective_date <= evaluation_date,
            )
            .order_by(PolicyVersion.effective_date.desc())  # type: ignore[attr-defined]
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def count_versions(self, tenant_id: str) -> int:
        """Count the total number of versions for a tenant.

        Used for pagination metadata.

        Args:
            tenant_id: The tenant identifier.

        Returns:
            The total number of versions for the tenant.
        """
        statement = (
            select(func.count())
            .select_from(PolicyVersion)
            .where(PolicyVersion.tenant_id == tenant_id)
        )
        result = await self.session.execute(statement)
        return result.scalar_one()

    async def get_latest_version_number(self, tenant_id: str) -> int | None:
        """Return the highest version_number for a tenant.

        Used to determine the next version number for monotonic increment.

        Args:
            tenant_id: The tenant identifier.

        Returns:
            The highest version number if any versions exist, None otherwise.
        """
        statement = select(func.max(PolicyVersion.version_number)).where(
            PolicyVersion.tenant_id == tenant_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
