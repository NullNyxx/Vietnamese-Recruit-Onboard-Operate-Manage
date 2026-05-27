"""Repository for OAuthConfig entity CRUD operations.

Provides async database access for OAuth provider configuration
lookup and upsert operations using SQLAlchemy async sessions with SQLModel.
"""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.modules.identity.domain.entities import OAuthConfig


class OAuthConfigRepository:
    """Handles OAuthConfig entity persistence using async SQLAlchemy sessions.

    Supports retrieving the active OAuth configuration for a provider
    and upserting (deactivating old configs, inserting/updating new ones).

    Attributes:
        session: The async database session for executing queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with an async database session.

        Args:
            session: An SQLAlchemy AsyncSession instance for database operations.
        """
        self.session = session

    async def get_active(self, provider: str = "google") -> OAuthConfig | None:
        """Retrieve the active OAuth configuration for a provider.

        Looks up the configuration where provider matches and is_active is True.
        Each provider has at most one active configuration at any time.

        Args:
            provider: The OAuth provider name (defaults to "google").

        Returns:
            The OAuthConfig entity if an active config exists, None otherwise.
        """
        statement = select(OAuthConfig).where(
            OAuthConfig.provider == provider,
            OAuthConfig.is_active == True,  # noqa: E712
        )
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def upsert(self, config: OAuthConfig) -> OAuthConfig:
        """Create or update an OAuth configuration for a provider.

        Deactivates any existing active configurations for the same provider,
        then inserts or updates the provided configuration as the new active one.

        Args:
            config: The OAuthConfig entity to persist. If it has an existing id
                that matches a record in the database, that record is updated.
                Otherwise, a new record is created.

        Returns:
            The persisted OAuthConfig entity.
        """
        # Deactivate all existing active configs for this provider
        statement = select(OAuthConfig).where(
            OAuthConfig.provider == config.provider,
            OAuthConfig.is_active == True,  # noqa: E712
        )
        result = await self.session.execute(statement)
        existing_configs = result.scalars().all()

        for existing in existing_configs:
            if existing.id != config.id:
                existing.is_active = False
                existing.updated_at = datetime.now(UTC)
                self.session.add(existing)

        # Check if this config already exists in the database
        if config.id:
            existing_statement = select(OAuthConfig).where(OAuthConfig.id == config.id)
            existing_result = await self.session.execute(existing_statement)
            existing_config = existing_result.scalars().first()

            if existing_config is not None:
                existing_config.client_id = config.client_id
                existing_config.client_secret_enc = config.client_secret_enc
                existing_config.redirect_uri = config.redirect_uri
                existing_config.is_active = config.is_active
                existing_config.updated_at = datetime.now(UTC)
                existing_config.updated_by_user_id = config.updated_by_user_id
                self.session.add(existing_config)
                await self.session.flush()
                return existing_config

        # Insert new config
        config.is_active = True
        config.updated_at = datetime.now(UTC)
        self.session.add(config)
        await self.session.flush()
        return config
