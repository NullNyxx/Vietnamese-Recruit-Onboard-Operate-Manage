"""Repository and helper for Recruitment audit logging.

Provides the AuditRepository class for CRUD/query operations on
RecruitmentAuditLog entries, and a `log_audit` helper function that
creates audit entries with PII redaction and graceful failure handling.

Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6
"""

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.modules.recruitment.domain.entities import RecruitmentAuditLog
from src.modules.recruitment.infrastructure.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)

# Module-level PIIRedactor instance for use by log_audit helper
_pii_redactor = PIIRedactor()


class AuditRepository:
    """Handles RecruitmentAuditLog entity persistence using async SQLAlchemy sessions.

    Supports creating audit entries and querying by entity_id, user_id,
    operation_type, and timestamp range.

    Attributes:
        session: The async database session for executing queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with an async database session.

        Args:
            session: An SQLAlchemy AsyncSession instance for database operations.
        """
        self.session = session

    async def create(self, log: RecruitmentAuditLog) -> RecruitmentAuditLog:
        """Persist a new audit log entry to the database.

        Args:
            log: The RecruitmentAuditLog entity to create.

        Returns:
            The persisted RecruitmentAuditLog entity with generated fields populated.
        """
        self.session.add(log)
        await self.session.flush()
        return log

    async def find_by_entity_id(self, entity_id: UUID) -> list[RecruitmentAuditLog]:
        """Retrieve all audit log entries for a given entity.

        Args:
            entity_id: The UUID of the entity to query logs for.

        Returns:
            A list of RecruitmentAuditLog entries matching the entity_id,
            sorted by created_at descending.
        """
        statement = (
            select(RecruitmentAuditLog)
            .where(RecruitmentAuditLog.entity_id == entity_id)
            .order_by(RecruitmentAuditLog.created_at.desc())  # type: ignore[union-attr]
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def find_by_user_id(
        self, user_id: UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[RecruitmentAuditLog], int]:
        """Retrieve paginated audit log entries for a given user.

        Args:
            user_id: The UUID of the user to query logs for.
            page: Page number (1-indexed).
            page_size: Number of entries per page.

        Returns:
            A tuple of (list of RecruitmentAuditLog entries, total count).
        """
        # Count query
        count_statement = (
            select(func.count())
            .select_from(RecruitmentAuditLog)
            .where(RecruitmentAuditLog.user_id == user_id)
        )
        count_result = await self.session.execute(count_statement)
        total = count_result.scalar() or 0

        # Data query with pagination
        offset = (page - 1) * page_size
        statement = (
            select(RecruitmentAuditLog)
            .where(RecruitmentAuditLog.user_id == user_id)
            .order_by(RecruitmentAuditLog.created_at.desc())  # type: ignore[union-attr]
            .offset(offset)
            .limit(page_size)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all()), total

    async def find_by_operation_type(self, operation_type: str) -> list[RecruitmentAuditLog]:
        """Retrieve all audit log entries for a given operation type.

        Args:
            operation_type: The operation type string to filter by.

        Returns:
            A list of RecruitmentAuditLog entries matching the operation_type,
            sorted by created_at descending.
        """
        statement = (
            select(RecruitmentAuditLog)
            .where(RecruitmentAuditLog.operation_type == operation_type)
            .order_by(RecruitmentAuditLog.created_at.desc())  # type: ignore[union-attr]
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def find_by_timestamp_range(
        self, start: datetime, end: datetime
    ) -> list[RecruitmentAuditLog]:
        """Retrieve all audit log entries within a timestamp range.

        Args:
            start: The start of the time range (inclusive).
            end: The end of the time range (inclusive).

        Returns:
            A list of RecruitmentAuditLog entries within the range,
            sorted by created_at descending.
        """
        statement = (
            select(RecruitmentAuditLog)
            .where(
                RecruitmentAuditLog.created_at >= start,  # type: ignore[operator]
                RecruitmentAuditLog.created_at <= end,  # type: ignore[operator]
            )
            .order_by(RecruitmentAuditLog.created_at.desc())  # type: ignore[union-attr]
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())


async def log_audit(
    session: AsyncSession,
    operation_type: str,
    entity_type: str,
    entity_id: UUID | None = None,
    user_id: UUID | None = None,
    previous_value: dict | None = None,
    new_value: dict | None = None,
    change_summary: str | None = None,
    model_name: str | None = None,
    token_usage: dict | None = None,
    latency_ms: int | None = None,
    success: bool = True,
) -> RecruitmentAuditLog | None:
    """Create a RecruitmentAuditLog entry with PII redaction and graceful failure.

    This helper applies PII redaction to the change_summary before storing,
    and wraps the entire operation in a try/except so that audit logging
    failures never block the calling operation.

    Args:
        session: The async database session.
        operation_type: Type of operation (e.g., "intent_classify", "cv_parse").
        entity_type: Type of entity being audited (e.g., "candidate", "cv_document").
        entity_id: Optional UUID of the entity being audited.
        user_id: Optional UUID of the user performing the action.
        previous_value: Optional dict of previous state (for change tracking).
        new_value: Optional dict of new state (for change tracking).
        change_summary: Optional human-readable summary of the change.
        model_name: Optional LLM model name used in the operation.
        token_usage: Optional dict with token usage info (prompt_tokens, completion_tokens).
        latency_ms: Optional latency in milliseconds for the operation.
        success: Whether the operation succeeded (default True).

    Returns:
        The created RecruitmentAuditLog entry, or None if logging failed.
    """
    try:
        # Apply PII redaction to change_summary (Requirement 17.3)
        redacted_summary = None
        if change_summary is not None:
            redacted_summary = _pii_redactor.redact(change_summary)

        audit_entry = RecruitmentAuditLog(
            operation_type=operation_type,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            previous_value=previous_value,
            new_value=new_value,
            change_summary=redacted_summary,
            model_name=model_name,
            token_usage=token_usage,
            latency_ms=latency_ms,
            success=success,
        )

        repo = AuditRepository(session)
        return await repo.create(audit_entry)

    except Exception:
        # Requirement 17.5: If audit logging fails, log error but don't block
        logger.error(
            "Failed to create audit log entry: operation_type=%s, entity_type=%s, entity_id=%s",
            operation_type,
            entity_type,
            entity_id,
            exc_info=True,
        )
        return None
