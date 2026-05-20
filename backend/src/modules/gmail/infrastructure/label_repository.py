"""Repository for GmailLabelMapping entity persistence.

Provides async database access for retrieving and upserting Gmail label
mappings per user. Each (user_id, label_name) pair is unique, allowing
the system to map VroomHR label names to Gmail internal label IDs.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.modules.gmail.domain.entities import GmailLabelMapping


class LabelRepository:
    """Handles GmailLabelMapping entity persistence using async SQLAlchemy sessions.

    Attributes:
        session: The async database session for executing queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with an async database session.

        Args:
            session: An SQLAlchemy AsyncSession instance for database operations.
        """
        self.session = session

    async def get_mappings(self, user_id: UUID) -> list[GmailLabelMapping]:
        """Retrieve all label mappings for a given user.

        Args:
            user_id: The UUID of the user whose label mappings to retrieve.

        Returns:
            A list of GmailLabelMapping entities for the user.
        """
        statement = select(GmailLabelMapping).where(
            GmailLabelMapping.user_id == user_id
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def upsert_mappings(
        self, user_id: UUID, mappings: list[dict[str, str]]
    ) -> list[GmailLabelMapping]:
        """Create or update label mappings for a user.

        For each mapping in the list, if a record with the same
        (user_id, label_name) already exists, updates the gmail_label_id
        and marks it as initialized. Otherwise, creates a new record.

        Args:
            user_id: The UUID of the user whose mappings to upsert.
            mappings: A list of dicts with keys "label_name" and "gmail_label_id".

        Returns:
            A list of the created or updated GmailLabelMapping entities.
        """
        now = datetime.now(UTC)
        results: list[GmailLabelMapping] = []

        for mapping in mappings:
            label_name = mapping["label_name"]
            gmail_label_id = mapping["gmail_label_id"]

            statement = select(GmailLabelMapping).where(
                GmailLabelMapping.user_id == user_id,
                GmailLabelMapping.label_name == label_name,
            )
            result = await self.session.execute(statement)
            existing = result.scalars().first()

            if existing is not None:
                existing.gmail_label_id = gmail_label_id
                existing.is_initialized = True
                existing.updated_at = now
                self.session.add(existing)
                results.append(existing)
            else:
                new_mapping = GmailLabelMapping(
                    user_id=user_id,
                    label_name=label_name,
                    gmail_label_id=gmail_label_id,
                    is_initialized=True,
                )
                self.session.add(new_mapping)
                results.append(new_mapping)

        await self.session.flush()
        return results

    async def get_label_id_by_name(
        self, user_id: UUID, label_name: str
    ) -> str | None:
        """Retrieve the Gmail label ID for a specific label name and user.

        Args:
            user_id: The UUID of the user.
            label_name: The VroomHR label name (e.g., "VroomHR/processed").

        Returns:
            The Gmail internal label ID string if found, None otherwise.
        """
        statement = select(GmailLabelMapping).where(
            GmailLabelMapping.user_id == user_id,
            GmailLabelMapping.label_name == label_name,
        )
        result = await self.session.execute(statement)
        mapping = result.scalars().first()

        if mapping is None:
            return None

        return mapping.gmail_label_id
