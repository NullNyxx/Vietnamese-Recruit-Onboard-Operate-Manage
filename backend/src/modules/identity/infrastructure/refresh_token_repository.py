"""Repository for RefreshToken entity CRUD operations.

Provides async database access for refresh token creation, lookup,
and revocation using SQLAlchemy async sessions with SQLModel.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.modules.identity.domain.entities import RefreshToken, User


@dataclass(frozen=True)
class RefreshTokenWithEmail:
    """A refresh token record enriched with the owning user's email.

    This dataclass satisfies the RefreshTokenRecord protocol expected
    by TokenService, which requires an email property for issuing
    new access tokens during refresh.

    Attributes:
        user_id: The UUID of the user who owns this token.
        token_hash: The SHA-256 hex digest of the raw token.
        expires_at: When the token expires.
        revoked_at: When the token was revoked, or None if active.
        email: The email address of the owning user.
    """

    user_id: UUID
    token_hash: str
    expires_at: datetime
    revoked_at: datetime | None
    email: str


class RefreshTokenRepository:
    """Handles RefreshToken entity persistence using async SQLAlchemy sessions.

    Provides methods for creating, looking up, and revoking refresh
    tokens. The find_by_token_hash method joins with the User table
    to include the user's email in the result.

    Attributes:
        session: The async database session for executing queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with an async database session.

        Args:
            session: An SQLAlchemy AsyncSession instance for database operations.
        """
        self.session = session

    async def create(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        user_agent: str | None = None,
    ) -> RefreshToken:
        """Create a new refresh token record in the database.

        Persists a hashed refresh token along with its expiry and
        optional user-agent metadata.

        Args:
            user_id: The UUID of the user who owns this token.
            token_hash: The SHA-256 hex digest of the raw token.
            expires_at: When the token should expire.
            user_agent: Optional HTTP User-Agent string from the client.

        Returns:
            The newly created RefreshToken entity.
        """
        refresh_token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
        )
        self.session.add(refresh_token)
        await self.session.flush()
        return refresh_token

    async def find_by_token_hash(self, token_hash: str) -> RefreshTokenWithEmail | None:
        """Look up a refresh token by its SHA-256 hash, including user email.

        Performs a join with the User table to retrieve the email address
        needed for issuing new access tokens during token refresh.

        Args:
            token_hash: The SHA-256 hex digest of the raw token.

        Returns:
            A RefreshTokenWithEmail containing token data and user email
            if found, None otherwise.
        """
        statement = (
            select(RefreshToken, User.email)
            .join(User, RefreshToken.user_id == User.id)
            .where(RefreshToken.token_hash == token_hash)
        )
        result = await self.session.execute(statement)
        row = result.first()

        if row is None:
            return None

        token, email = row
        return RefreshTokenWithEmail(
            user_id=token.user_id,
            token_hash=token.token_hash,
            expires_at=token.expires_at,
            revoked_at=token.revoked_at,
            email=email,
        )

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        """Revoke all active refresh tokens for a user.

        Sets revoked_at to the current UTC time on all tokens belonging
        to the specified user that have not already been revoked. This
        enforces the single active session invariant.

        Args:
            user_id: The UUID of the user whose tokens to revoke.
        """
        statement = select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at == None,  # noqa: E711
        )
        result = await self.session.execute(statement)
        tokens = result.scalars().all()

        now = datetime.now(UTC)
        for token in tokens:
            token.revoked_at = now
            self.session.add(token)

        if tokens:
            await self.session.flush()

    async def store(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        user_agent: str | None = None,
    ) -> RefreshToken:
        """Store a new refresh token hash in the database.

        Alias for :meth:`create` to satisfy the TokenService protocol.

        Args:
            user_id: The UUID of the user who owns this token.
            token_hash: The SHA-256 hex digest of the raw token.
            expires_at: When the token should expire.
            user_agent: Optional HTTP User-Agent string from the client.

        Returns:
            The newly created RefreshToken entity.
        """
        return await self.create(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
        )

    async def revoke(self, token_hash: str) -> None:
        """Revoke a single refresh token by its hash.

        Sets revoked_at to the current UTC time on the token matching
        the given hash.

        Args:
            token_hash: The SHA-256 hex digest of the token to revoke.
        """
        statement = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self.session.execute(statement)
        token = result.scalars().first()

        if token is not None:
            token.revoked_at = datetime.now(UTC)
            self.session.add(token)
            await self.session.flush()
