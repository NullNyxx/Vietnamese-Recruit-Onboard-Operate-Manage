"""Candidate Service for the Recruitment module.

Manages Candidate CRUD operations, status transitions, list/search,
and detail retrieval with linked CV documents and presigned URLs.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9,
6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 7.1, 7.2, 7.3, 7.4, 7.5, 13.2
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.modules.employee.domain.entities import Employee
from src.modules.recruitment.domain.entities import Candidate, CVDocument
from src.modules.recruitment.domain.enums import CandidateStatus
from src.modules.recruitment.domain.exceptions import (
    CandidateNotFoundError,
    GmailNotConnectedError,
    InvalidStatusTransitionError,
)
from src.modules.recruitment.domain.value_objects import ParsedCV
from src.modules.recruitment.infrastructure.audit_repository import log_audit
from src.modules.recruitment.infrastructure.minio_client import RecruitmentMinIOClient
from src.modules.recruitment.infrastructure.repositories import (
    CandidateRepository,
    CVDocumentRepository,
)

logger = logging.getLogger(__name__)


# ─── State Machine Definition ──────────────────────────────────────────

VALID_TRANSITIONS: dict[str, set[str]] = {
    CandidateStatus.NEW: {
        CandidateStatus.REVIEWING,
        CandidateStatus.INTERVIEW_SCHEDULED,
        CandidateStatus.REJECTED,
        CandidateStatus.ARCHIVED,
    },
    CandidateStatus.REVIEWING: {
        CandidateStatus.INTERVIEW_SCHEDULED,
        CandidateStatus.ACCEPTED,
        CandidateStatus.REJECTED,
        CandidateStatus.ARCHIVED,
    },
    CandidateStatus.INTERVIEW_SCHEDULED: {
        CandidateStatus.ACCEPTED,
        CandidateStatus.REJECTED,
        CandidateStatus.ARCHIVED,
    },
    CandidateStatus.ACCEPTED: set(),
    CandidateStatus.REJECTED: set(),
    CandidateStatus.ARCHIVED: set(),
}


# ─── Validation ────────────────────────────────────────────────────────

# Basic email regex: must contain exactly one @ with non-empty local and domain parts
_EMAIL_PATTERN = re.compile(r"^[^@]+@[^@]+$")


class CandidateValidationError(Exception):
    """Raised when candidate field validation fails.

    Attributes:
        errors: List of validation error dicts with field and reason.
    """

    def __init__(self, errors: list[dict]) -> None:
        self.errors = errors
        super().__init__(f"Candidate validation failed: {errors}")


def validate_candidate_fields(parsed_cv: ParsedCV) -> list[dict]:
    """Validate required candidate fields from parsed CV data.

    Checks:
    - name: non-empty, ≤ 255 characters
    - email: valid format (contains @, non-empty local and domain parts), ≤ 255 chars

    Args:
        parsed_cv: The parsed CV data to validate.

    Returns:
        List of validation error dicts. Empty list means validation passed.
    """
    errors: list[dict] = []

    # Validate name
    name = parsed_cv.name.strip() if parsed_cv.name else ""
    if not name:
        errors.append({"field": "name", "reason": "Name is required and cannot be empty"})
    elif len(name) > 255:
        errors.append({"field": "name", "reason": "Name must not exceed 255 characters"})

    # Validate email
    email = parsed_cv.email.strip() if parsed_cv.email else ""
    if not email:
        errors.append({"field": "email", "reason": "Email is required and cannot be empty"})
    elif len(email) > 255:
        errors.append({"field": "email", "reason": "Email must not exceed 255 characters"})
    elif not _EMAIL_PATTERN.match(email):
        errors.append(
            {
                "field": "email",
                "reason": (
                    "Email must contain exactly one '@' with non-empty local and domain parts"
                ),
            }
        )

    return errors


# ─── Protocols for cross-module communication ──────────────────────────


@runtime_checkable
class GmailLabelProtocol(Protocol):
    """Protocol for applying Gmail labels to messages.

    Abstracts the Gmail module's label service to avoid direct imports.
    """

    async def add_label(
        self,
        user_id: UUID,
        message_id: str,
        label_name: str,
        access_token: str,
    ) -> None:
        """Add a label to a Gmail message."""
        ...


@runtime_checkable
class GmailSendProtocol(Protocol):
    """Protocol for sending emails via Gmail.

    Abstracts the Gmail module's send service to avoid direct imports.
    """

    async def send_email(
        self,
        user_id: UUID,
        to: str,
        subject: str,
        body_html: str,
    ) -> None:
        """Send an email to the specified recipient."""
        ...


@runtime_checkable
class GmailConnectionChecker(Protocol):
    """Protocol for checking Gmail connection status."""

    async def is_connected(self, user_id: UUID) -> bool:
        """Check if the user's Gmail is connected."""
        ...


@runtime_checkable
class DomainEventPublisher(Protocol):
    """Protocol for publishing domain events."""

    async def publish(self, event_type: str, payload: dict) -> None:
        """Publish a domain event."""
        ...


@dataclass
class CVDocumentDetail:
    """CV document metadata with an optional presigned download URL.

    Attributes:
        id: UUID of the CV document.
        original_filename: Original filename of the uploaded CV.
        mime_type: MIME type of the file.
        size_bytes: File size in bytes.
        uploaded_at: Timestamp when the file was uploaded.
        presigned_url: Presigned MinIO URL for direct download, or None
            if URL generation failed.
        url_error: Error message if presigned URL generation failed.
    """

    id: UUID
    original_filename: str
    mime_type: str
    size_bytes: int
    uploaded_at: datetime
    presigned_url: str | None = None
    url_error: str | None = None


@dataclass
class CandidateDetail:
    """Full candidate detail including linked CV documents with presigned URLs.

    Attributes:
        candidate: The Candidate entity with all fields.
        cv_documents: List of CV documents with presigned download URLs.
    """

    candidate: Candidate
    cv_documents: list[CVDocumentDetail] = field(default_factory=list)


@dataclass
class PaginatedCandidates:
    """Paginated list of candidates with total count.

    Attributes:
        candidates: List of Candidate entities for the current page.
        total_count: Total number of candidates matching the query filters.
        page: Current page number (1-indexed).
        page_size: Number of items per page.
    """

    candidates: list[Candidate]
    total_count: int
    page: int
    page_size: int


class CandidateService:
    """Manages Candidate lifecycle, list/search, and detail retrieval.

    Provides methods for creating/updating candidates from parsed CVs,
    listing candidates with filters and search, and retrieving full
    candidate details with linked CV documents and presigned URLs.

    Implements the CandidateCreator protocol from cv_processor.py,
    providing the `create_or_update_candidate` method that the CV
    processing pipeline calls after successful parsing.

    Args:
        candidate_repo: Repository for candidate persistence.
        cv_document_repo: Repository for CV document persistence.
        minio_client: MinIO client for generating presigned URLs.
        session: Async database session.
        gmail_label_service: Optional protocol-based Gmail label service.
        access_token_provider: Optional callable returning the current OAuth token.
        user_id_provider: Optional callable returning the current user UUID.
    """

    def __init__(
        self,
        candidate_repo: CandidateRepository,
        cv_document_repo: CVDocumentRepository,
        minio_client: RecruitmentMinIOClient,
        session: AsyncSession,
        gmail_label_service: GmailLabelProtocol | None = None,
        gmail_sender: GmailSendProtocol | None = None,
        gmail_checker: GmailConnectionChecker | None = None,
        event_publisher: DomainEventPublisher | None = None,
        access_token_provider: object | None = None,
        user_id_provider: object | None = None,
        user_id: UUID | None = None,
    ) -> None:
        self._candidate_repo = candidate_repo
        self._cv_document_repo = cv_document_repo
        self._minio_client = minio_client
        self._session = session
        self._gmail_label_service = gmail_label_service
        self._gmail_sender = gmail_sender
        self._gmail_checker = gmail_checker
        self._event_publisher = event_publisher
        self._access_token_provider = access_token_provider
        self._user_id_provider = user_id_provider
        self._user_id = user_id

    # ─── Create / Update (CandidateCreator protocol) ───────────────────

    async def create_or_update_candidate(
        self,
        parsed_cv: ParsedCV,
        cv_document_id: UUID,
        source_email_id: UUID | None,
        confidence_score: float,
    ) -> Candidate:
        """Create a new candidate or update an existing one by email match.

        Implements the CandidateCreator protocol. This method:
        1. Validates name and email fields
        2. Checks for existing candidate with same email (deduplication)
        3. If exists: updates data fields but preserves existing status
        4. If new: creates with status="new"
        5. Links the CV document to the candidate
        6. Stores confidence_score and parsed_cv_json
        7. Applies "VroomHR/processed" Gmail label
        8. Logs audit entry

        Args:
            parsed_cv: Structured CV data from LLM parsing.
            cv_document_id: UUID of the associated CV document.
            source_email_id: UUID of the source email message (or None).
            confidence_score: Confidence score from LLM parsing (0.0-1.0).

        Returns:
            The created or updated Candidate entity.

        Raises:
            CandidateValidationError: If name or email validation fails.
        """
        # Step 1: Validate required fields
        validation_errors = validate_candidate_fields(parsed_cv)
        if validation_errors:
            # Store validation errors on the CV document
            cv_doc = await self._cv_document_repo.get_by_id(cv_document_id)
            if cv_doc is not None:
                cv_doc.validation_errors = validation_errors
                await self._cv_document_repo.update(cv_doc)
                await self._session.commit()

            logger.warning(
                "Candidate validation failed for CV document %s: %s",
                cv_document_id,
                validation_errors,
            )
            raise CandidateValidationError(validation_errors)

        # Step 2: Check for existing candidate by email (deduplication)
        email = parsed_cv.email.strip().lower()
        existing_candidate = await self._candidate_repo.find_by_email(email)

        if existing_candidate is not None:
            # Step 3: Update existing candidate — preserve status
            candidate = await self._update_existing_candidate(
                existing_candidate, parsed_cv, confidence_score
            )
            operation = "candidate_updated"
        else:
            # Step 4: Create new candidate with status "new"
            candidate = await self._create_new_candidate(
                parsed_cv, source_email_id, confidence_score
            )
            operation = "candidate_created"

        # Step 5: Link CV document to candidate
        await self._link_cv_document(cv_document_id, candidate.id)

        # Commit all changes
        await self._session.commit()

        # Step 6: Apply Gmail label "VroomHR/processed" (best-effort)
        await self._apply_processed_label(source_email_id)

        # Step 7: Log audit entry
        await log_audit(
            session=self._session,
            operation_type=operation,
            entity_type="candidate",
            entity_id=candidate.id,
            new_value={
                "name": candidate.name,
                "email": candidate.email,
                "status": candidate.status,
                "confidence_score": confidence_score,
                "cv_document_id": str(cv_document_id),
            },
            change_summary=(
                f"Candidate {operation.replace('candidate_', '')}: "
                f"{candidate.name} ({candidate.email}), "
                f"confidence={confidence_score:.2f}"
            ),
            success=True,
        )
        await self._session.commit()

        logger.info(
            "Candidate %s: id=%s, email=%s, confidence=%.2f",
            operation,
            candidate.id,
            candidate.email,
            confidence_score,
        )

        return candidate

    # ─── List / Detail ─────────────────────────────────────────────────

    async def list_candidates(
        self,
        *,
        status: list[str] | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        min_confidence: float | None = None,
        skills: list[str] | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedCandidates:
        """Retrieve a paginated list of candidates with optional filters.

        Validates pagination parameters before delegating to the repository.
        Archived candidates are excluded by default unless the status filter
        explicitly includes "archived".

        Args:
            status: Optional list of status values to filter by.
            date_from: Optional start date for created_at range filter.
            date_to: Optional end date for created_at range filter.
            min_confidence: Optional minimum confidence score filter (0.0–1.0).
            skills: Optional list of skills to filter by (OR logic, case-insensitive).
            search: Optional text to search in name, email, phone, skills
                (case-insensitive partial match).
            page: Page number (1-indexed). Must be >= 1.
            page_size: Number of items per page. Must be between 1 and 100.

        Returns:
            PaginatedCandidates with the list of candidates and total count.

        Raises:
            ValueError: If page < 1 or page_size not in range 1–100.
        """
        # Validate pagination parameters
        if page < 1:
            raise ValueError("page must be >= 1")
        if page_size < 1 or page_size > 100:
            raise ValueError("page_size must be between 1 and 100")

        candidates, total_count = await self._candidate_repo.list_candidates(
            status=status,
            date_from=date_from,
            date_to=date_to,
            min_confidence=min_confidence,
            skills=skills,
            search=search,
            page=page,
            page_size=page_size,
        )

        return PaginatedCandidates(
            candidates=candidates,
            total_count=total_count,
            page=page,
            page_size=page_size,
        )

    async def get_candidate(self, candidate_id: UUID) -> CandidateDetail:
        """Retrieve full candidate detail with linked CV documents and presigned URLs.

        Fetches the candidate by ID, retrieves all linked CV documents,
        and generates a presigned download URL for each document. If URL
        generation fails for a document (e.g., MinIO unavailable or file
        missing), the document is still returned with url set to None and
        an error indicator.

        Args:
            candidate_id: UUID of the candidate to retrieve.

        Returns:
            CandidateDetail with the candidate and CV documents (each with
            a presigned URL or error indicator).

        Raises:
            CandidateNotFoundError: If no candidate exists with the given ID.
        """
        candidate = await self._candidate_repo.get_by_id(candidate_id)
        if candidate is None:
            raise CandidateNotFoundError(f"Candidate not found: {candidate_id}")

        # Fetch all linked CV documents
        cv_documents = await self._cv_document_repo.find_by_candidate_id(candidate_id)

        # Generate presigned URLs for each document
        cv_document_details: list[CVDocumentDetail] = []
        for doc in cv_documents:
            detail = await self._build_cv_document_detail(doc)
            cv_document_details.append(detail)

        return CandidateDetail(
            candidate=candidate,
            cv_documents=cv_document_details,
        )

    async def _build_cv_document_detail(self, doc: CVDocument) -> CVDocumentDetail:
        """Build a CVDocumentDetail with presigned URL for a single document.

        Attempts to generate a presigned URL. If generation fails (MinIO
        unavailable or file missing), returns the document metadata with
        url=None and an error indicator.

        Args:
            doc: The CVDocument entity to build detail for.

        Returns:
            CVDocumentDetail with presigned URL or error information.
        """
        presigned_url: str | None = None
        url_error: str | None = None

        if doc.file_path:
            try:
                presigned_url = await self._minio_client.generate_presigned_url(doc.file_path)
            except Exception as exc:
                logger.warning(
                    "Failed to generate presigned URL for CV document %s (path: %s): %s",
                    doc.id,
                    doc.file_path,
                    exc,
                )
                url_error = str(exc)

        return CVDocumentDetail(
            id=doc.id,
            original_filename=doc.original_filename,
            mime_type=doc.mime_type,
            size_bytes=doc.size_bytes,
            uploaded_at=doc.uploaded_at,
            presigned_url=presigned_url,
            url_error=url_error,
        )

    # ─── Private helpers for create/update ─────────────────────────────

    async def _create_new_candidate(
        self,
        parsed_cv: ParsedCV,
        source_email_id: UUID | None,
        confidence_score: float,
    ) -> Candidate:
        """Create a new Candidate entity from parsed CV data.

        Sets status to "new" and stores the complete parsed_cv_json.

        Args:
            parsed_cv: Structured CV data.
            source_email_id: UUID of the source email message.
            confidence_score: Confidence score from parsing.

        Returns:
            The newly created Candidate entity.
        """
        candidate = Candidate(
            name=parsed_cv.name.strip(),
            email=parsed_cv.email.strip().lower(),
            phone=parsed_cv.phone or "",
            skills=parsed_cv.skills or [],
            experience=[exp.model_dump() for exp in parsed_cv.experience]
            if parsed_cv.experience
            else [],
            education=[edu.model_dump() for edu in parsed_cv.education]
            if parsed_cv.education
            else [],
            summary=parsed_cv.summary or "",
            parsed_cv_json=parsed_cv.model_dump(),
            status=CandidateStatus.NEW,
            confidence_score=confidence_score,
            source_email_message_id=source_email_id,
        )

        return await self._candidate_repo.create(candidate)

    async def _update_existing_candidate(
        self,
        existing: Candidate,
        parsed_cv: ParsedCV,
        confidence_score: float,
    ) -> Candidate:
        """Update an existing Candidate with new parsed CV data.

        Preserves the existing candidate's status while updating
        all data fields with the latest parsed CV information.

        Args:
            existing: The existing Candidate entity to update.
            parsed_cv: New structured CV data.
            confidence_score: New confidence score.

        Returns:
            The updated Candidate entity.
        """
        # Update data fields — preserve status
        existing.name = parsed_cv.name.strip()
        existing.phone = parsed_cv.phone or ""
        existing.skills = parsed_cv.skills or []
        existing.experience = (
            [exp.model_dump() for exp in parsed_cv.experience] if parsed_cv.experience else []
        )
        existing.education = (
            [edu.model_dump() for edu in parsed_cv.education] if parsed_cv.education else []
        )
        existing.summary = parsed_cv.summary or ""
        existing.parsed_cv_json = parsed_cv.model_dump()
        existing.confidence_score = confidence_score
        # Status is intentionally NOT updated (Requirement 5.5)

        return await self._candidate_repo.update(existing)

    async def _link_cv_document(self, cv_document_id: UUID, candidate_id: UUID) -> None:
        """Link a CV document to a candidate by setting candidate_id.

        Args:
            cv_document_id: UUID of the CV document to link.
            candidate_id: UUID of the candidate to link to.
        """
        cv_doc = await self._cv_document_repo.get_by_id(cv_document_id)
        if cv_doc is not None:
            cv_doc.candidate_id = candidate_id
            await self._cv_document_repo.update(cv_doc)

    async def _apply_processed_label(self, source_email_id: UUID | None) -> None:
        """Apply "VroomHR/processed" Gmail label to the source email.

        This is a best-effort operation — failures are logged but do not
        block candidate creation.

        Args:
            source_email_id: UUID of the source email message, or None.
        """
        if (
            self._gmail_label_service is None
            or source_email_id is None
            or self._access_token_provider is None
            or self._user_id_provider is None
        ):
            return

        try:
            # Get access token and user_id from providers
            access_token = None
            user_id = None

            if callable(self._access_token_provider):
                access_token = await self._access_token_provider()  # type: ignore[misc]
            if callable(self._user_id_provider):
                user_id = await self._user_id_provider()  # type: ignore[misc]

            if access_token and user_id:
                await self._gmail_label_service.add_label(
                    user_id=user_id,
                    message_id=str(source_email_id),
                    label_name="VroomHR/processed",
                    access_token=access_token,
                )
        except Exception as exc:
            # Best-effort: log but don't block candidate creation
            logger.warning(
                "Failed to apply 'VroomHR/processed' label for email %s: %s",
                source_email_id,
                exc,
            )

    # ─── Status transition validation ──────────────────────────────────

    def _validate_transition(self, current_status: str, target_status: str, action: str) -> None:
        """Validate that a status transition is allowed by the state machine.

        Args:
            current_status: The candidate's current status.
            target_status: The desired target status.
            action: The action name being performed (for error messages).

        Raises:
            InvalidStatusTransitionError: If the transition is not allowed.
        """
        allowed = VALID_TRANSITIONS.get(current_status, set())
        if target_status not in allowed:
            raise InvalidStatusTransitionError(current_status, action)

    async def _get_candidate_or_raise(self, candidate_id: UUID) -> Candidate:
        """Retrieve a candidate by ID or raise CandidateNotFoundError.

        Args:
            candidate_id: The UUID of the candidate.

        Returns:
            The Candidate entity.

        Raises:
            CandidateNotFoundError: If the candidate doesn't exist.
        """
        candidate = await self._candidate_repo.get_by_id(candidate_id)
        if candidate is None:
            raise CandidateNotFoundError(f"Candidate not found: {candidate_id}")
        return candidate

    # ─── Status transition actions ─────────────────────────────────────

    async def reject_candidate(self, candidate_id: UUID, reason: str | None = None) -> Candidate:
        """Transition candidate to rejected status.

        Validates the transition, stores the rejection reason and
        rejected_at timestamp, and logs an audit entry.

        Args:
            candidate_id: UUID of the candidate to reject.
            reason: Optional rejection reason (max 1000 characters).

        Returns:
            The updated Candidate entity.

        Raises:
            CandidateNotFoundError: If the candidate doesn't exist.
            InvalidStatusTransitionError: If the transition is not allowed.
        """
        candidate = await self._get_candidate_or_raise(candidate_id)
        previous_status = candidate.status

        self._validate_transition(
            current_status=candidate.status,
            target_status=CandidateStatus.REJECTED,
            action="reject",
        )

        candidate.status = CandidateStatus.REJECTED
        candidate.rejection_reason = reason
        candidate.rejected_at = datetime.now(UTC)
        candidate = await self._candidate_repo.update(candidate)
        await self._session.commit()

        await log_audit(
            session=self._session,
            operation_type="candidate_rejected",
            entity_type="candidate",
            entity_id=candidate.id,
            user_id=self._user_id,
            previous_value={"status": previous_status},
            new_value={"status": CandidateStatus.REJECTED},
            change_summary=(f"Candidate rejected: {reason[:200] if reason else 'no reason'}"),
        )

        return candidate

    async def accept_candidate(self, candidate_id: UUID) -> Candidate:
        """Transition candidate to accepted status.

        Only allowed from interview_scheduled or reviewing status.
        Stores accepted_at timestamp, emits domain event, and logs audit.

        Args:
            candidate_id: UUID of the candidate to accept.

        Returns:
            The updated Candidate entity.

        Raises:
            CandidateNotFoundError: If the candidate doesn't exist.
            InvalidStatusTransitionError: If the transition is not allowed.
        """
        candidate = await self._get_candidate_or_raise(candidate_id)
        previous_status = candidate.status

        self._validate_transition(
            current_status=candidate.status,
            target_status=CandidateStatus.ACCEPTED,
            action="accept",
        )

        candidate.status = CandidateStatus.ACCEPTED
        candidate.accepted_at = datetime.now(UTC)
        candidate = await self._candidate_repo.update(candidate)
        await self._session.commit()

        # Emit domain event for downstream modules (onboarding)
        if self._event_publisher:
            await self._event_publisher.publish(
                event_type="candidate_accepted",
                payload={
                    "candidate_id": str(candidate.id),
                    "name": candidate.name,
                    "email": candidate.email,
                },
            )

        await log_audit(
            session=self._session,
            operation_type="candidate_accepted",
            entity_type="candidate",
            entity_id=candidate.id,
            user_id=self._user_id,
            previous_value={"status": previous_status},
            new_value={"status": CandidateStatus.ACCEPTED},
            change_summary="Candidate accepted",
        )

        return candidate

    async def archive_candidate(self, candidate_id: UUID) -> Candidate:
        """Transition candidate to archived status.

        Not allowed from accepted status. Idempotent for already-archived
        candidates (returns existing record without modification).

        Args:
            candidate_id: UUID of the candidate to archive.

        Returns:
            The updated Candidate entity.

        Raises:
            CandidateNotFoundError: If the candidate doesn't exist.
            InvalidStatusTransitionError: If the transition is not allowed
                (e.g., from accepted status).
        """
        candidate = await self._get_candidate_or_raise(candidate_id)
        previous_status = candidate.status

        # Idempotent: already archived is a no-op
        if candidate.status == CandidateStatus.ARCHIVED:
            return candidate

        self._validate_transition(
            current_status=candidate.status,
            target_status=CandidateStatus.ARCHIVED,
            action="archive",
        )

        candidate.status = CandidateStatus.ARCHIVED
        candidate.archived_at = datetime.now(UTC)
        candidate = await self._candidate_repo.update(candidate)
        await self._session.commit()

        await log_audit(
            session=self._session,
            operation_type="candidate_archived",
            entity_type="candidate",
            entity_id=candidate.id,
            user_id=self._user_id,
            previous_value={"status": previous_status},
            new_value={"status": CandidateStatus.ARCHIVED},
            change_summary=f"Candidate archived from status '{previous_status}'",
        )

        return candidate

    async def schedule_interview(
        self,
        candidate_id: UUID,
        interviewer_ids: list[UUID],
        date: str | None = None,
        time: str | None = None,
        duration_minutes: int | None = None,
        notes: str | None = None,
    ) -> Candidate:
        """Schedule an interview for a candidate.

        Validates the status transition (not from rejected/archived),
        validates interviewer_ids against employee records, updates
        status to interview_scheduled, emits domain event, and logs audit.

        Args:
            candidate_id: UUID of the candidate.
            interviewer_ids: List of employee UUIDs to be interviewers.
            date: Optional interview date string.
            time: Optional interview time string.
            duration_minutes: Optional duration in minutes.
            notes: Optional notes for the interview.

        Returns:
            The updated Candidate entity.

        Raises:
            CandidateNotFoundError: If the candidate doesn't exist.
            InvalidStatusTransitionError: If the transition is not allowed.
            ValueError: If any interviewer_id doesn't match an employee.
        """
        candidate = await self._get_candidate_or_raise(candidate_id)
        previous_status = candidate.status

        self._validate_transition(
            current_status=candidate.status,
            target_status=CandidateStatus.INTERVIEW_SCHEDULED,
            action="schedule_interview",
        )

        # Validate interviewer_ids against employee records
        invalid_ids = await self._validate_interviewer_ids(interviewer_ids)
        if invalid_ids:
            raise ValueError(f"Invalid interviewer IDs: {[str(id) for id in invalid_ids]}")

        candidate.status = CandidateStatus.INTERVIEW_SCHEDULED
        candidate = await self._candidate_repo.update(candidate)
        await self._session.commit()

        # Emit domain event for interview module
        if self._event_publisher:
            await self._event_publisher.publish(
                event_type="interview_scheduled",
                payload={
                    "candidate_id": str(candidate.id),
                    "candidate_name": candidate.name,
                    "candidate_email": candidate.email,
                    "interviewer_ids": [str(id) for id in interviewer_ids],
                    "date": date,
                    "time": time,
                    "duration_minutes": duration_minutes,
                    "notes": notes,
                },
            )

        await log_audit(
            session=self._session,
            operation_type="schedule_interview",
            entity_type="candidate",
            entity_id=candidate.id,
            user_id=self._user_id,
            previous_value={"status": previous_status},
            new_value={
                "status": CandidateStatus.INTERVIEW_SCHEDULED,
                "interviewer_ids": [str(id) for id in interviewer_ids],
            },
            change_summary=(f"Interview scheduled with {len(interviewer_ids)} interviewer(s)"),
        )

        return candidate

    async def _validate_interviewer_ids(self, interviewer_ids: list[UUID]) -> list[UUID]:
        """Validate that all interviewer IDs correspond to existing employees.

        Args:
            interviewer_ids: List of employee UUIDs to validate.

        Returns:
            List of invalid IDs that don't match any employee record.
        """
        if not interviewer_ids:
            return []

        statement = select(Employee.id).where(Employee.id.in_(interviewer_ids))  # type: ignore[union-attr]
        result = await self._session.execute(statement)
        found_ids = {row[0] for row in result.all()}

        return [id for id in interviewer_ids if id not in found_ids]

    async def send_email_to_candidate(
        self,
        candidate_id: UUID,
        subject: str,
        body_html: str,
        template_name: str | None = None,
    ) -> None:
        """Send an email to a candidate via Gmail adapter.

        Validates Gmail connection, validates candidate email, sends
        the email via the Gmail adapter protocol, and logs an audit entry.

        Args:
            candidate_id: UUID of the candidate to email.
            subject: Email subject line.
            body_html: HTML body content.
            template_name: Optional template name for the email.

        Raises:
            CandidateNotFoundError: If the candidate doesn't exist.
            GmailNotConnectedError: If Gmail is not connected.
            ValueError: If the candidate's email is invalid.
        """
        candidate = await self._get_candidate_or_raise(candidate_id)

        # Validate Gmail connection
        if self._gmail_checker:
            is_connected = await self._gmail_checker.is_connected(self._user_id or UUID(int=0))
            if not is_connected:
                raise GmailNotConnectedError()
        elif self._gmail_sender is None:
            raise GmailNotConnectedError()

        # Validate candidate email
        if not candidate.email or not candidate.email.strip():
            raise ValueError(f"Candidate email is empty or invalid: '{candidate.email}'")
        email = candidate.email.strip()
        if "@" not in email or email.startswith("@") or email.endswith("@"):
            raise ValueError(f"Candidate email is empty or invalid: '{candidate.email}'")

        # Send email via Gmail adapter
        if self._gmail_sender is None:
            raise GmailNotConnectedError()

        await self._gmail_sender.send_email(
            user_id=self._user_id or UUID(int=0),
            to=email,
            subject=subject,
            body_html=body_html,
        )

        # Audit log
        await log_audit(
            session=self._session,
            operation_type="candidate_email_sent",
            entity_type="candidate",
            entity_id=candidate.id,
            user_id=self._user_id,
            new_value={
                "subject": subject[:100],
                "template_name": template_name,
            },
            change_summary=(f"Email sent to candidate: subject='{subject[:100]}'"),
        )
