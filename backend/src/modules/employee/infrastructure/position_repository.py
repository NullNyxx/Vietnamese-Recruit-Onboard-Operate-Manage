"""Repository for Position entity CRUD operations.

Provides async database access for position listing, lookup,
creation, update, hard-delete, and active-employee checks using
SQLAlchemy async sessions with SQLModel.
"""

from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.modules.employee.domain.entities import Employee, Position


class PositionRepository:
    """Handles Position entity persistence using async SQLAlchemy sessions.

    Attributes:
        session: The async database session for executing queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with an async database session.

        Args:
            session: An SQLAlchemy AsyncSession instance for database operations.
        """
        self.session = session

    async def list_all(self) -> list[Position]:
        """Retrieve all positions ordered by name.

        Returns:
            A list of all Position entities sorted alphabetically by name.
        """
        statement = select(Position).order_by(Position.name)  # type: ignore[arg-type]
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_by_id(self, position_id: UUID) -> Position | None:
        """Retrieve a position by its unique identifier.

        Args:
            position_id: The UUID primary key of the position.

        Returns:
            The Position entity if found, None otherwise.
        """
        statement = select(Position).where(Position.id == position_id)
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def get_by_name(self, name: str) -> Position | None:
        """Retrieve a position by name (case-insensitive).

        Used for uniqueness checks when creating or updating positions.

        Args:
            name: The position name to search for.

        Returns:
            The Position entity if found, None otherwise.
        """
        statement = select(Position).where(func.lower(Position.name) == name.lower())
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def create(self, position: Position) -> Position:
        """Persist a new position entity to the database.

        Args:
            position: The Position entity to create.

        Returns:
            The persisted Position entity with generated fields populated.
        """
        self.session.add(position)
        await self.session.flush()
        return position

    async def update(self, position_id: UUID, data: dict) -> Position | None:
        """Update an existing position with partial data.

        Only the fields present in the data dict are updated.

        Args:
            position_id: The UUID of the position to update.
            data: A dictionary of field names to new values.

        Returns:
            The updated Position entity if found, None otherwise.
        """
        statement = select(Position).where(Position.id == position_id)
        result = await self.session.execute(statement)
        position = result.scalars().first()

        if position is None:
            return None

        for key, value in data.items():
            if hasattr(position, key):
                setattr(position, key, value)

        self.session.add(position)
        await self.session.flush()
        return position

    async def delete(self, position_id: UUID) -> bool:
        """Hard-delete a position from the database.

        Args:
            position_id: The UUID of the position to delete.

        Returns:
            True if the position was found and deleted, False otherwise.
        """
        statement = select(Position).where(Position.id == position_id)
        result = await self.session.execute(statement)
        position = result.scalars().first()

        if position is None:
            return False

        await self.session.delete(position)
        await self.session.flush()
        return True

    async def has_active_employees(self, position_id: UUID) -> bool:
        """Check if any active employee holds this position.

        Used for cascade protection — positions cannot be deleted
        if active employees reference them.

        Args:
            position_id: The UUID of the position to check.

        Returns:
            True if at least one active employee holds this position.
        """
        statement = (
            select(func.count())
            .select_from(Employee)
            .where(
                Employee.position_id == position_id,
                Employee.is_active == True,  # noqa: E712
            )
        )
        result = await self.session.execute(statement)
        count = result.scalar() or 0
        return count > 0
