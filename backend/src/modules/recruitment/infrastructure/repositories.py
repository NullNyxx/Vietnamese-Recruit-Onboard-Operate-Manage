"""Repositories for Recruitment module entities.

Provides async database access for Candidate and CVDocument entities
using SQLAlchemy async sessions with SQLModel. Follows the same
patterns established in the employee module.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import desc, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.modules.recruitment.domain.entities import Candidate, CVDocument
from src.modules.recruitment.domain.enums import CandidateStatus, ProcessingStatus


class CandidateRepository:
    """Handles Candidate entity persistence using async SQLAlchemy sessions.

    Attributes:
        session: The async database session for executing queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with an async database session.

        Args:
            session: An SQLAlchemy AsyncSession instance for database operations.
        """
        self.session = session

    async def create(self, candidate: Candidate) -> Candidate:
        """Persist a new candidate entity to the database.

        Args:
            candidate: The Candidate entity to create.

        Returns:
            The persisted Candidate entity with generated fields populated.
        """
        self.session.add(candidate)
        await self.session.flush()
        return candidate

    async def get_by_id(self, id: UUID) -> Candidate | None:
        """Retrieve a candidate by their unique identifier.

        Args:
            id: The UUID primary key of the candidate.

        Returns:
            The Candidate entity if found, None otherwise.
        """
        statement = select(Candidate).where(Candidate.id == id)
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def find_by_email(self, email: str) -> Candidate | None:
        """Retrieve a candidate by email address (case-insensitive).

        Used for deduplication when processing new CVs.

        Args:
            email: The email address to search for.

        Returns:
            The Candidate entity if found, None otherwise.
        """
        statement = select(Candidate).where(func.lower(Candidate.email) == email.lower())
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def update(self, candidate: Candidate) -> Candidate:
        """Update an existing candidate entity.

        Updates the updated_at timestamp automatically.

        Args:
            candidate: The Candidate entity with updated fields.

        Returns:
            The updated Candidate entity.
        """
        candidate.updated_at = datetime.now(UTC)
        self.session.add(candidate)
        await self.session.flush()
        return candidate

    async def delete(self, id: UUID) -> None:
        """Hard-delete a candidate from the database.

        Args:
            id: The UUID of the candidate to delete.
        """
        statement = select(Candidate).where(Candidate.id == id)
        result = await self.session.execute(statement)
        candidate = result.scalars().first()

        if candidate is not None:
            await self.session.delete(candidate)
            await self.session.flush()

    async def list_candidates(
        self,
        status: list[str] | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        min_confidence: float | None = None,
        skills: list[str] | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Candidate], int]:
        """Retrieve a paginated list of candidates with optional filters.

        Archived candidates are excluded by default unless the status
        filter explicitly includes "archived".

        Args:
            status: Optional list of status values to filter by.
            date_from: Optional start date for created_at range filter.
            date_to: Optional end date for created_at range filter.
            min_confidence: Optional minimum confidence score filter.
            skills: Optional list of skills to filter by (OR logic, case-insensitive).
            search: Optional text to search in name, email, phone, skills
                (case-insensitive partial match).
            page: The page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            A tuple of (list of Candidate entities, total count).
        """
        statement = select(Candidate)
        count_statement = select(func.count()).select_from(Candidate)

        # Exclude archived candidates unless explicitly requested
        if status is not None:
            statement = statement.where(Candidate.status.in_(status))  # type: ignore[union-attr]
            count_statement = count_statement.where(Candidate.status.in_(status))  # type: ignore[union-attr]
        else:
            statement = statement.where(Candidate.status != CandidateStatus.ARCHIVED)
            count_statement = count_statement.where(Candidate.status != CandidateStatus.ARCHIVED)

        # Apply date range filter
        if date_from is not None:
            statement = statement.where(Candidate.created_at >= date_from)  # type: ignore[arg-type]
            count_statement = count_statement.where(Candidate.created_at >= date_from)  # type: ignore[arg-type]

        if date_to is not None:
            statement = statement.where(Candidate.created_at <= date_to)  # type: ignore[arg-type]
            count_statement = count_statement.where(Candidate.created_at <= date_to)  # type: ignore[arg-type]

        # Apply minimum confidence filter
        if min_confidence is not None:
            statement = statement.where(Candidate.confidence_score >= min_confidence)
            count_statement = count_statement.where(Candidate.confidence_score >= min_confidence)

        # Apply skills filter (OR logic, case-insensitive)
        # Cast JSONB array to text and use ilike for partial matching
        if skills:
            skills_conditions = []
            for skill in skills:
                skill_pattern = f"%{skill.lower()}%"
                skills_conditions.append(
                    func.lower(
                        func.cast(Candidate.skills, func.text())  # type: ignore[arg-type]
                    ).ilike(skill_pattern)
                )
            skills_filter = or_(*skills_conditions)
            statement = statement.where(skills_filter)
            count_statement = count_statement.where(skills_filter)

        # Apply text search filter (case-insensitive partial match)
        if search:
            search_term = f"%{search.lower()}%"
            search_conditions = [
                func.lower(Candidate.name).ilike(search_term),
                func.lower(Candidate.email).ilike(search_term),
                func.lower(Candidate.phone).ilike(search_term),
                # Search within skills JSONB array cast to text
                func.lower(func.cast(Candidate.skills, func.text())).ilike(  # type: ignore[arg-type]
                    search_term
                ),
            ]
            search_filter = or_(*search_conditions)
            statement = statement.where(search_filter)
            count_statement = count_statement.where(search_filter)

        # Get total count
        count_result = await self.session.execute(count_statement)
        total = count_result.scalar() or 0

        # Apply sorting and pagination
        offset = (page - 1) * page_size
        statement = statement.order_by(desc(Candidate.created_at))  # type: ignore[arg-type]
        statement = statement.offset(offset).limit(page_size)

        # Execute query
        result = await self.session.execute(statement)
        candidates = list(result.scalars().all())

        return candidates, total


class CVDocumentRepository:
    """Handles CVDocument entity persistence using async SQLAlchemy sessions.

    Attributes:
        session: The async database session for executing queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with an async database session.

        Args:
            session: An SQLAlchemy AsyncSession instance for database operations.
        """
        self.session = session

    async def create(self, doc: CVDocument) -> CVDocument:
        """Persist a new CV document entity to the database.

        Args:
            doc: The CVDocument entity to create.

        Returns:
            The persisted CVDocument entity with generated fields populated.
        """
        self.session.add(doc)
        await self.session.flush()
        return doc

    async def get_by_id(self, id: UUID) -> CVDocument | None:
        """Retrieve a CV document by its unique identifier.

        Args:
            id: The UUID primary key of the CV document.

        Returns:
            The CVDocument entity if found, None otherwise.
        """
        statement = select(CVDocument).where(CVDocument.id == id)
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def find_by_candidate_id(self, candidate_id: UUID) -> list[CVDocument]:
        """Retrieve all CV documents for a given candidate.

        Results are ordered by created_at descending.

        Args:
            candidate_id: The UUID of the candidate.

        Returns:
            A list of CVDocument entities for the candidate.
        """
        statement = (
            select(CVDocument)
            .where(CVDocument.candidate_id == candidate_id)
            .order_by(desc(CVDocument.created_at))  # type: ignore[arg-type]
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def find_needs_review(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[CVDocument], int]:
        """Retrieve paginated CV documents that need manual review.

        Returns documents with processing_status in ("needs_review", "failed"),
        ordered by created_at descending.

        Args:
            page: The page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            A tuple of (list of CVDocument entities, total count).
        """
        review_statuses = [
            ProcessingStatus.NEEDS_REVIEW,
            ProcessingStatus.FAILED,
        ]

        statement = select(CVDocument).where(
            CVDocument.processing_status.in_(review_statuses)  # type: ignore[union-attr]
        )
        count_statement = (
            select(func.count())
            .select_from(CVDocument)
            .where(
                CVDocument.processing_status.in_(review_statuses)  # type: ignore[union-attr]
            )
        )

        # Get total count
        count_result = await self.session.execute(count_statement)
        total = count_result.scalar() or 0

        # Apply sorting and pagination
        offset = (page - 1) * page_size
        statement = statement.order_by(desc(CVDocument.created_at))  # type: ignore[arg-type]
        statement = statement.offset(offset).limit(page_size)

        # Execute query
        result = await self.session.execute(statement)
        documents = list(result.scalars().all())

        return documents, total

    async def find_by_gmail_message_id(self, gmail_message_id: str) -> list[CVDocument]:
        """Retrieve all CV documents associated with a Gmail message ID.

        Args:
            gmail_message_id: The Gmail message identifier string.

        Returns:
            A list of CVDocument entities for the given message.
        """
        statement = (
            select(CVDocument)
            .where(CVDocument.gmail_message_id == gmail_message_id)
            .order_by(desc(CVDocument.created_at))  # type: ignore[arg-type]
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def update(self, doc: CVDocument) -> CVDocument:
        """Update an existing CV document entity.

        Updates the updated_at timestamp automatically.

        Args:
            doc: The CVDocument entity with updated fields.

        Returns:
            The updated CVDocument entity.
        """
        doc.updated_at = datetime.now(UTC)
        self.session.add(doc)
        await self.session.flush()
        return doc

    async def delete(self, id: UUID) -> None:
        """Hard-delete a CV document from the database.

        Args:
            id: The UUID of the CV document to delete.
        """
        statement = select(CVDocument).where(CVDocument.id == id)
        result = await self.session.execute(statement)
        doc = result.scalars().first()

        if doc is not None:
            await self.session.delete(doc)
            await self.session.flush()
