"""Repository for AuditLog entity CRUD operations.

Provides async database access for creating audit log entries and
retrieving them with pagination and filtering support using
SQLAlchemy async sessions with SQLModel.
"""

from datetime import datetime

from sqlalchemy import desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.modules.identity.domain.entities import AuditActionType, AuditLog


class AuditLogRepository:
    """Handles AuditLog entity persistence using async SQLAlchemy sessions.

    Provides methods for creating audit log entries and querying them
    with pagination, action type filtering, and date range filtering.

    Attributes:
        session: The async database session for executing queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with an async database session.

        Args:
            session: An SQLAlchemy AsyncSession instance for database operations.
        """
        self.session = session

    async def create(self, log: AuditLog) -> AuditLog:
        """Persist a new audit log entry to the database.

        Args:
            log: The AuditLog entity to persist.

        Returns:
            The persisted AuditLog entity with any database-generated fields.
        """
        self.session.add(log)
        await self.session.flush()
        return log

    async def get_paginated(
        self,
        offset: int,
        limit: int,
        filters: dict | None = None,
    ) -> tuple[list[AuditLog], int]:
        """Retrieve audit log entries with pagination and optional filtering.

        Returns a page of audit log entries ordered by creation time
        (most recent first), along with the total count of matching entries.

        Args:
            offset: The number of entries to skip (for pagination).
            limit: The maximum number of entries to return.
            filters: Optional dictionary of filter criteria. Supported keys:
                - action_type (AuditActionType): Filter by action type.
                - start_date (datetime): Filter entries created on or after this date.
                - end_date (datetime): Filter entries created on or before this date.

        Returns:
            A tuple of (items, total_count) where items is the list of
            AuditLog entries for the requested page and total_count is
            the total number of entries matching the filters.
        """
        if filters is None:
            filters = {}

        # Build base query with filters
        statement = select(AuditLog)
        count_statement = select(func.count()).select_from(AuditLog)

        if "action_type" in filters and filters["action_type"] is not None:
            action_type = filters["action_type"]
            if isinstance(action_type, str):
                action_type = AuditActionType(action_type)
            statement = statement.where(AuditLog.action_type == action_type)
            count_statement = count_statement.where(AuditLog.action_type == action_type)

        if "start_date" in filters and filters["start_date"] is not None:
            start_date: datetime = filters["start_date"]
            statement = statement.where(
                AuditLog.created_at >= start_date  # type: ignore[operator]
            )
            count_statement = count_statement.where(
                AuditLog.created_at >= start_date  # type: ignore[operator]
            )

        if "end_date" in filters and filters["end_date"] is not None:
            end_date: datetime = filters["end_date"]
            statement = statement.where(
                AuditLog.created_at <= end_date  # type: ignore[operator]
            )
            count_statement = count_statement.where(
                AuditLog.created_at <= end_date  # type: ignore[operator]
            )

        # Get total count
        count_result = await self.session.execute(count_statement)
        total = count_result.scalar_one()

        # Get paginated items ordered by most recent first
        statement = statement.order_by(
            desc(AuditLog.created_at)  # type: ignore[arg-type]
        )
        statement = statement.offset(offset).limit(limit)

        result = await self.session.execute(statement)
        items = list(result.scalars().all())

        return items, total
