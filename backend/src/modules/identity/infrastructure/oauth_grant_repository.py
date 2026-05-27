"""Repository for OAuthGrant entity CRUD operations.

Provides async database access for OAuth grant lookup, upsert, and
invalidation operations using SQLAlchemy async sessions with SQLModel.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.modules.identity.domain.entities import OAuthGrant


class OAuthGrantRepository:
    """Handles OAuthGrant entity persistence using async SQLAlchemy sessions.

    Attributes:
        session: The async database session for executing queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with an async database session.

        Args:
            session: An SQLAlchemy AsyncSession instance for database operations.
        """
        self.session = session

    async def get_by_user_id(self, user_id: UUID) -> OAuthGrant | None:
        """Retrieve the active OAuth grant for a user.

        Looks up the grant where user_id matches and is_valid is True.
        Each user has at most one active grant at any time.

        Args:
            user_id: The UUID of the user whose grant to retrieve.

        Returns:
            The OAuthGrant entity if a valid grant exists, None otherwise.
        """
        statement = select(OAuthGrant).where(
            OAuthGrant.user_id == user_id,
            OAuthGrant.is_valid == True,  # noqa: E712
        )
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def upsert(
        self,
        user_id: UUID,
        access_token_enc: str,
        refresh_token_enc: str,
        scopes: list[str],
        token_expires_at: datetime,
    ) -> OAuthGrant:
        """Create or update an OAuth grant for a user.

        If a grant already exists for the given user_id, updates the
        tokens, scopes, expiry, and updated_at timestamp. Otherwise,
        creates a new OAuthGrant record.

        Args:
            user_id: The UUID of the user who owns the grant.
            access_token_enc: The AES-256-GCM encrypted Google access token.
            refresh_token_enc: The AES-256-GCM encrypted Google refresh token.
            scopes: The list of OAuth scopes that were authorized.
            token_expires_at: When the Google access token expires.

        Returns:
            The created or updated OAuthGrant entity.
        """
        statement = select(OAuthGrant).where(OAuthGrant.user_id == user_id)
        result = await self.session.execute(statement)
        existing_grant = result.scalars().first()

        if existing_grant is not None:
            existing_grant.access_token_enc = access_token_enc
            existing_grant.refresh_token_enc = refresh_token_enc
            existing_grant.scopes = scopes
            existing_grant.token_expires_at = token_expires_at
            existing_grant.is_valid = True
            existing_grant.updated_at = datetime.now(UTC)
            self.session.add(existing_grant)
            await self.session.flush()
            return existing_grant

        new_grant = OAuthGrant(
            user_id=user_id,
            access_token_enc=access_token_enc,
            refresh_token_enc=refresh_token_enc,
            scopes=scopes,
            token_expires_at=token_expires_at,
        )
        self.session.add(new_grant)
        await self.session.flush()
        return new_grant

    async def get_all_valid_with_scopes(self, required_scopes: list[str]) -> list[OAuthGrant]:
        """Retrieve all valid OAuth grants that contain the specified scopes.

        Used by the ARQ worker to find all users with active Gmail connections.

        Args:
            required_scopes: List of scope strings that must all be present.

        Returns:
            List of OAuthGrant entities matching the criteria.
        """
        statement = select(OAuthGrant).where(
            OAuthGrant.is_valid == True,  # noqa: E712
        )
        result = await self.session.execute(statement)
        grants = result.scalars().all()

        # Filter in Python since ARRAY containment varies by dialect
        return [
            grant for grant in grants if all(scope in grant.scopes for scope in required_scopes)
        ]

    async def mark_invalid(self, user_id: UUID) -> None:
        """Mark the user's OAuth grant as invalid.

        Sets is_valid to False on the grant for the given user. This is
        called when Google token refresh fails (e.g., user revoked access).

        Args:
            user_id: The UUID of the user whose grant to invalidate.
        """
        statement = select(OAuthGrant).where(OAuthGrant.user_id == user_id)
        result = await self.session.execute(statement)
        grant = result.scalars().first()

        if grant is not None:
            grant.is_valid = False
            grant.updated_at = datetime.now(UTC)
            self.session.add(grant)
            await self.session.flush()
