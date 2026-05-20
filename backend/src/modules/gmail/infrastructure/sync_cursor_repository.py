"""Repository for SyncCursor entity persistence.

Provides async database access for retrieving and upserting the Gmail
synchronization cursor (history_id) per user. Each user has at most one
cursor, enforced by a unique constraint on user_id.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.modules.gmail.domain.entities import SyncCursor


class SyncCursorRepository:
    """Handles SyncCursor entity persistence using async SQLAlchemy sessions.

    Attributes:
        session: The async database session for executing queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with an async database session.

        Args:
            session: An SQLAlchemy AsyncSession instance for database operations.
        """
        self.session = session

    async def get_cursor(self, user_id: UUID) -> SyncCursor | None:
        """Retrieve the sync cursor for a given user.

        Args:
            user_id: The UUID of the user whose cursor to retrieve.

        Returns:
            The SyncCursor entity if found, None otherwise.
        """
        statement = select(SyncCursor).where(SyncCursor.user_id == user_id)
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def upsert_cursor(self, user_id: UUID, history_id: str) -> SyncCursor:
        """Create or update the sync cursor for a user.

        If a cursor already exists for the user, updates the history_id
        and last_poll_at timestamp. Otherwise, creates a new cursor record.
        This ensures the unique constraint on user_id is respected.

        Args:
            user_id: The UUID of the user whose cursor to upsert.
            history_id: The latest Gmail history_id to store.

        Returns:
            The created or updated SyncCursor entity.
        """
        now = datetime.now(UTC)

        statement = select(SyncCursor).where(SyncCursor.user_id == user_id)
        result = await self.session.execute(statement)
        cursor = result.scalars().first()

        if cursor is not None:
            cursor.history_id = history_id
            cursor.last_poll_at = now
            cursor.updated_at = now
            self.session.add(cursor)
            await self.session.flush()
            return cursor

        cursor = SyncCursor(
            user_id=user_id,
            history_id=history_id,
            last_poll_at=now,
        )
        self.session.add(cursor)
        await self.session.flush()
        return cursor
