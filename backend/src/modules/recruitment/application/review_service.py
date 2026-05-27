"""Review Service for the Recruitment module.

Manages the CV manual review queue: listing documents needing review,
submitting HR corrections, retrying LLM parse, and dismissing documents.

Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7, 14.8
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.recruitment.domain.entities import Candidate, CVDocument
from src.modules.recruitment.domain.enums import ProcessingStatus
from src.modules.recruitment.domain.exceptions import CVDocumentNotFoundError
from src.modules.recruitment.domain.value_objects import ParsedCV
from src.modules.recruitment.infrastructure.audit_repository import log_audit
from src.modules.recruitment.infrastructure.repositories import (
    CVDocumentRepository,
)

logger = logging.getLogger(__name__)


# ─── Validation ────────────────────────────────────────────────────────

# Basic email regex: must contain exactly one @ with non-empty local and domain parts
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Review retry timeout in seconds (Requirement 14.4)
_RETRY_TIMEOUT_SECONDS = 60


class ReviewValidationError(Exception):
    """Raised when corrected ParsedCV data fails validation.

    Attributes:
        errors: List of validation error dicts with field and reason.
    """

    def __init__(self, errors: list[dict]) -> None:
        self.errors = errors
        super().__init__(f"Review validation failed: {errors}")


def validate_correction(parsed_cv: ParsedCV) -> list[dict]:
    """Validate corrected ParsedCV data for the review submission.

    Checks:
    - name: at least 1 non-whitespace character, at most 200 characters
    - email: valid RFC 5322 basic format, at most 254 characters

    Args:
        parsed_cv: The corrected ParsedCV data to validate.

    Returns:
        List of validation error dicts. Empty list means validation passed.
    """
    errors: list[dict] = []

    # Validate name: 1-200 chars, at least 1 non-whitespace
    name = parsed_cv.name.strip() if parsed_cv.name else ""
    if not name:
        errors.append(
            {
                "field": "name",
                "reason": "Name is required and must contain at least 1 non-whitespace character",
            }
        )
    elif len(name) > 200:
        errors.append(
            {
                "field": "name",
                "reason": "Name must not exceed 200 characters",
            }
        )

    # Validate email: valid format, at most 254 chars
    email = parsed_cv.email.strip() if parsed_cv.email else ""
    if not email:
        errors.append(
            {
                "field": "email",
                "reason": "Email is required and cannot be empty",
            }
        )
    elif len(email) > 254:
        errors.append(
            {
                "field": "email",
                "reason": "Email must not exceed 254 characters",
            }
        )
    elif not _EMAIL_PATTERN.match(email):
        errors.append(
            {
                "field": "email",
                "reason": "Email must be a valid email address",
            }
        )

    return errors


# ─── Data classes ──────────────────────────────────────────────────────


@dataclass
class PaginatedReviewQueue:
    """Paginated list of CV documents needing review.

    Attributes:
        documents: List of CVDocument entities for the current page.
        total_count: Total number of documents needing review.
        page: Current page number (1-indexed).
        page_size: Number of items per page.
    """

    documents: list[CVDocument]
    total_count: int
    page: int
    page_size: int


# ─── Protocols ─────────────────────────────────────────────────────────

from typing import Protocol, runtime_checkable


@runtime_checkable
class CandidateCreatorProtocol(Protocol):
    """Protocol for creating/updating candidates from corrected CV data."""

    async def create_or_update_candidate(
        self,
        parsed_cv: ParsedCV,
        cv_document_id: UUID,
        source_email_id: UUID | None,
        confidence_score: float,
    ) -> Candidate:
        """Create new or update existing candidate by email match."""
        ...


@runtime_checkable
class CVRetryParserProtocol(Protocol):
    """Protocol for retrying LLM parse on stored OCR text."""

    async def retry_llm_parse(self, cv_document_id: UUID) -> ParsedCV | None:
        """Re-run LLM parse for a CV document."""
        ...


# ─── Service ───────────────────────────────────────────────────────────


class ReviewService:
    """Manages the CV manual review queue.

    Provides methods for listing documents needing review, submitting
    HR corrections, retrying LLM parse, and dismissing documents from
    the review queue.

    Args:
        cv_document_repo: Repository for CV document persistence.
        candidate_creator: Protocol for creating/updating candidates.
        cv_retry_parser: Protocol for retrying LLM parse.
        session: Async database session.
    """

    def __init__(
        self,
        cv_document_repo: CVDocumentRepository,
        candidate_creator: CandidateCreatorProtocol,
        cv_retry_parser: CVRetryParserProtocol,
        session: AsyncSession,
    ) -> None:
        self._cv_document_repo = cv_document_repo
        self._candidate_creator = candidate_creator
        self._cv_retry_parser = cv_retry_parser
        self._session = session

    async def list_review_queue(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedReviewQueue:
        """List CV documents needing review, paginated.

        Returns documents with processing_status "needs_review" or "failed",
        sorted by created_at descending.

        Args:
            page: Page number (1-indexed). Must be >= 1.
            page_size: Number of items per page. Must be between 1 and 100.

        Returns:
            PaginatedReviewQueue with documents and total count.

        Raises:
            ValueError: If page < 1 or page_size not in range 1–100.
        """
        if page < 1:
            raise ValueError("page must be >= 1")
        if page_size < 1 or page_size > 100:
            raise ValueError("page_size must be between 1 and 100")

        documents, total_count = await self._cv_document_repo.find_needs_review(
            page=page,
            page_size=page_size,
        )

        return PaginatedReviewQueue(
            documents=documents,
            total_count=total_count,
            page=page,
            page_size=page_size,
        )

    async def submit_correction(
        self,
        cv_document_id: UUID,
        corrected_data: ParsedCV,
    ) -> Candidate:
        """Apply HR corrections to a CV document and create/update candidate.

        Steps:
        1. Validate the corrected ParsedCV (name 1-200 chars, email valid ≤ 254 chars)
        2. Get the CVDocument by ID (raise CVDocumentNotFoundError if not found)
        3. Store the corrected parsed_cv_data on the CVDocument
        4. Call CandidateService.create_or_update_candidate with the corrected data
        5. Set CVDocument processing_status to "completed"
        6. Log audit entry

        Args:
            cv_document_id: UUID of the CV document to correct.
            corrected_data: The corrected ParsedCV data from HR.

        Returns:
            The created or updated Candidate entity.

        Raises:
            ReviewValidationError: If the corrected data fails validation.
            CVDocumentNotFoundError: If the CV document doesn't exist.
        """
        # Step 1: Validate corrected data
        validation_errors = validate_correction(corrected_data)
        if validation_errors:
            raise ReviewValidationError(validation_errors)

        # Step 2: Get CVDocument
        cv_doc = await self._cv_document_repo.get_by_id(cv_document_id)
        if cv_doc is None:
            raise CVDocumentNotFoundError(f"CV document not found: {cv_document_id}")

        # Step 3: Store corrected parsed_cv_data
        cv_doc.parsed_cv_data = corrected_data.model_dump()

        # Step 4: Create or update candidate
        candidate = await self._candidate_creator.create_or_update_candidate(
            parsed_cv=corrected_data,
            cv_document_id=cv_document_id,
            source_email_id=None,
            confidence_score=1.0,  # HR-corrected data has full confidence
        )

        # Step 5: Set processing_status to completed
        cv_doc.processing_status = ProcessingStatus.COMPLETED
        await self._cv_document_repo.update(cv_doc)
        await self._session.commit()

        # Step 6: Log audit entry
        await log_audit(
            session=self._session,
            operation_type="cv_review_correction",
            entity_type="cv_document",
            entity_id=cv_document_id,
            new_value={
                "processing_status": ProcessingStatus.COMPLETED,
                "candidate_id": str(candidate.id),
                "corrected_name": corrected_data.name,
            },
            change_summary=(
                f"HR correction submitted for CV document, "
                f"candidate created/updated: {candidate.name}"
            ),
            success=True,
        )
        await self._session.commit()

        logger.info(
            "CV review correction submitted: cv_document_id=%s, candidate_id=%s",
            cv_document_id,
            candidate.id,
        )

        return candidate

    async def retry_parse(self, cv_document_id: UUID) -> CVDocument:
        """Re-run LLM parse on stored OCR text with 60 second timeout.

        Delegates to CVProcessorService.retry_llm_parse with a timeout.
        If the retry fails or times out, sets processing_status back to
        "needs_review".

        Args:
            cv_document_id: UUID of the CV document to retry parsing for.

        Returns:
            The updated CVDocument entity.

        Raises:
            CVDocumentNotFoundError: If the CV document doesn't exist.
        """
        # Verify document exists first
        cv_doc = await self._cv_document_repo.get_by_id(cv_document_id)
        if cv_doc is None:
            raise CVDocumentNotFoundError(f"CV document not found: {cv_document_id}")

        try:
            # Run retry with 60 second timeout (Requirement 14.4)
            parsed_cv = await asyncio.wait_for(
                self._cv_retry_parser.retry_llm_parse(cv_document_id),
                timeout=_RETRY_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            # Timeout: set status back to needs_review (Requirement 14.5)
            cv_doc = await self._cv_document_repo.get_by_id(cv_document_id)
            if cv_doc is not None:
                cv_doc.processing_status = ProcessingStatus.NEEDS_REVIEW
                cv_doc.processing_error = "LLM parse retry timed out (60s)"
                await self._cv_document_repo.update(cv_doc)
                await self._session.commit()

            await log_audit(
                session=self._session,
                operation_type="cv_review_retry",
                entity_type="cv_document",
                entity_id=cv_document_id,
                change_summary="LLM parse retry timed out after 60 seconds",
                success=False,
            )
            await self._session.commit()

            logger.warning(
                "LLM parse retry timed out for CV document %s",
                cv_document_id,
            )

            # Re-fetch to return current state
            cv_doc = await self._cv_document_repo.get_by_id(cv_document_id)
            if cv_doc is None:
                raise CVDocumentNotFoundError(f"CV document not found: {cv_document_id}")
            return cv_doc

        except Exception as exc:
            # Other failure: set status back to needs_review (Requirement 14.5)
            cv_doc = await self._cv_document_repo.get_by_id(cv_document_id)
            if cv_doc is not None:
                cv_doc.processing_status = ProcessingStatus.NEEDS_REVIEW
                cv_doc.processing_error = f"LLM parse retry failed: {exc}"
                await self._cv_document_repo.update(cv_doc)
                await self._session.commit()

            await log_audit(
                session=self._session,
                operation_type="cv_review_retry",
                entity_type="cv_document",
                entity_id=cv_document_id,
                change_summary=f"LLM parse retry failed: {exc}",
                success=False,
            )
            await self._session.commit()

            logger.error(
                "LLM parse retry failed for CV document %s: %s",
                cv_document_id,
                exc,
            )

            # Re-fetch to return current state
            cv_doc = await self._cv_document_repo.get_by_id(cv_document_id)
            if cv_doc is None:
                raise CVDocumentNotFoundError(f"CV document not found: {cv_document_id}")
            return cv_doc

        # Success: log audit and return updated document
        await log_audit(
            session=self._session,
            operation_type="cv_review_retry",
            entity_type="cv_document",
            entity_id=cv_document_id,
            change_summary=(
                "LLM parse retry succeeded" + (f": {parsed_cv.name}" if parsed_cv else "")
            ),
            success=True,
        )
        await self._session.commit()

        # Re-fetch to return current state (retry_llm_parse updates the doc)
        cv_doc = await self._cv_document_repo.get_by_id(cv_document_id)
        if cv_doc is None:
            raise CVDocumentNotFoundError(f"CV document not found: {cv_document_id}")
        return cv_doc

    async def dismiss(self, cv_document_id: UUID) -> None:
        """Dismiss a CV document from the review queue.

        Sets processing_status to "dismissed", excluding it from the
        review queue without creating a Candidate record.

        Args:
            cv_document_id: UUID of the CV document to dismiss.

        Raises:
            CVDocumentNotFoundError: If the CV document doesn't exist.
        """
        cv_doc = await self._cv_document_repo.get_by_id(cv_document_id)
        if cv_doc is None:
            raise CVDocumentNotFoundError(f"CV document not found: {cv_document_id}")

        cv_doc.processing_status = ProcessingStatus.DISMISSED
        await self._cv_document_repo.update(cv_doc)
        await self._session.commit()

        await log_audit(
            session=self._session,
            operation_type="cv_review_dismissed",
            entity_type="cv_document",
            entity_id=cv_document_id,
            new_value={"processing_status": ProcessingStatus.DISMISSED},
            change_summary="CV document dismissed from review queue",
            success=True,
        )
        await self._session.commit()

        logger.info(
            "CV document dismissed from review queue: %s",
            cv_document_id,
        )
