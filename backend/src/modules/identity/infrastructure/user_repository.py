"""Repository for User entity CRUD operations.

Provides async database access for user lookup and upsert operations
using SQLAlchemy async sessions with SQLModel.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.modules.identity.api.schemas import GoogleUserInfo
from src.modules.identity.domain.entities import User, UserRole


class UserRepository:
    """Handles User entity persistence using async SQLAlchemy sessions.

    Attributes:
        session: The async database session for executing queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with an async database session.

        Args:
            session: An SQLAlchemy AsyncSession instance for database operations.
        """
        self.session = session

    async def get_by_email(self, email: str) -> User | None:
        """Retrieve a user by email address (case-insensitive).

        Args:
            email: The email address to search for.

        Returns:
            The User entity if found, None otherwise.
        """
        statement = select(User).where(func.lower(User.email) == email.lower())
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Retrieve a user by their unique identifier.

        Args:
            user_id: The UUID primary key of the user.

        Returns:
            The User entity if found, None otherwise.
        """
        statement = select(User).where(User.id == user_id)
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def upsert(self, google_user_info: GoogleUserInfo, role: UserRole | None = None) -> User:
        """Create a new user or update an existing one from Google profile data.

        If a user with the same email or google_sub already exists, updates
        their last_login timestamp and profile data (name, avatar_url).
        Otherwise, creates a new User record.

        Args:
            google_user_info: The user profile extracted from a Google ID token.
            role: Optional role to assign to a newly created user. If None,
                defaults to UserRole.USER. Ignored for existing users.

        Returns:
            The created or updated User entity.
        """
        # Check for existing user by email or google_sub
        statement = select(User).where(
            (func.lower(User.email) == google_user_info.email.lower())
            | (User.google_sub == google_user_info.sub)
        )
        result = await self.session.execute(statement)
        existing_user = result.scalars().first()

        if existing_user is not None:
            # Update existing user
            existing_user.last_login = datetime.now(UTC)
            existing_user.name = google_user_info.name
            existing_user.avatar_url = google_user_info.picture
            self.session.add(existing_user)
            await self.session.flush()
            return existing_user

        # Create new user with specified role (or default USER).
        new_user = User(
            email=google_user_info.email,
            name=google_user_info.name,
            avatar_url=google_user_info.picture,
            google_sub=google_user_info.sub,
            role=role if role is not None else UserRole.USER,
        )
        self.session.add(new_user)
        await self.session.flush()
        return new_user
