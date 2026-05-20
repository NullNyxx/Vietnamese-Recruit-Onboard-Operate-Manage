"""Unit tests for ReviewService.

Tests the CV manual review queue management including:
- list_review_queue: paginated listing of documents needing review
- submit_correction: validation and candidate creation from HR corrections
- retry_parse: LLM parse retry with 60 second timeout
- dismiss: marking documents as dismissed

Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7, 14.8
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.modules.recruitment.application.review_service import (
    PaginatedReviewQueue,
    ReviewService,
    ReviewValidationError,
    validate_correction,
)
from src.modules.recruitment.domain.entities import Candidate, CVDocument
from src.modules.recruitment.domain.enums import ProcessingStatus
from src.modules.recruitment.domain.exceptions import CVDocumentNotFoundError
from src.modules.recruitment.domain.value_objects import ParsedCV


# ─── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def mock_cv_document_repo():
    """Create a mock CV document repository."""
    repo = AsyncMock()
    repo.create = AsyncMock(side_effect=lambda doc: doc)
    repo.update = AsyncMock(side_effect=lambda doc: doc)
    repo.get_by_id = AsyncMock(return_value=None)
    repo.find_needs_review = AsyncMock(return_value=([], 0))
    return repo


@pytest.fixture
def mock_candidate_creator():
    """Create a mock candidate creator protocol."""
    creator = AsyncMock()
    candidate = Candidate(
        id=uuid4(),
        name="Nguyen Van A",
        email="test@example.com",
        phone="0901234567",
        skills=["Python"],
        experience=[],
        education=[],
        summary="Developer",
        status="new",
        confidence_score=1.0,
    )
    creator.create_or_update_candidate = AsyncMock(return_value=candidate)
    return creator


@pytest.fixture
def mock_cv_retry_parser():
    """Create a mock CV retry parser protocol."""
    parser = AsyncMock()
    parser.retry_llm_parse = AsyncMock(return_value=None)
    return parser


@pytest.fixture
def mock_session():
    """Create a mock async database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def service(
    mock_cv_document_repo,
    mock_candidate_creator,
    mock_cv_retry_parser,
    mock_session,
):
    """Create a ReviewService with all mocked dependencies."""
    return ReviewService(
        cv_document_repo=mock_cv_document_repo,
        candidate_creator=mock_candidate_creator,
        cv_retry_parser=mock_cv_retry_parser,
        session=mock_session,
    )


@pytest.fixture
def sample_cv_document():
    """Create a sample CVDocument for testing."""
    return CVDocument(
        id=uuid4(),
        gmail_message_id="msg_123",
        original_filename="resume.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        file_path="storage/cv/msg_123/resume.pdf",
        processing_status=ProcessingStatus.NEEDS_REVIEW,
        ocr_output="Nguyen Van A\nemail: test@example.com\nSkills: Python",
    )


@pytest.fixture
def valid_parsed_cv():
    """Create a valid ParsedCV for correction submission."""
    return ParsedCV(
        name="Nguyen Van A",
        email="test@example.com",
        phone="0901234567",
        skills=["Python", "FastAPI"],
        experience=[],
        education=[],
        summary="Experienced developer",
    )


# ─── Tests: validate_correction ───────────────────────────────────────


class TestValidateCorrection:
    """Tests for the validate_correction function."""

    def test_valid_data_passes(self, valid_parsed_cv):
        """Valid ParsedCV data should produce no errors."""
        errors = validate_correction(valid_parsed_cv)
        assert errors == []

    def test_empty_name_fails(self):
        """Empty name should produce a validation error."""
        parsed_cv = ParsedCV(name="", email="test@example.com")
        errors = validate_correction(parsed_cv)
        assert len(errors) == 1
        assert errors[0]["field"] == "name"

    def test_whitespace_only_name_fails(self):
        """Whitespace-only name should produce a validation error."""
        parsed_cv = ParsedCV(name="   ", email="test@example.com")
        errors = validate_correction(parsed_cv)
        assert len(errors) == 1
        assert errors[0]["field"] == "name"

    def test_name_exceeds_200_chars_fails(self):
        """Name exceeding 200 characters should produce a validation error.

        Note: ParsedCV has max_length=200 on name field, so Pydantic will
        reject names > 200 chars at model creation. This test verifies that
        our validation function correctly catches names at the boundary
        by using model_construct to bypass Pydantic validation.
        """
        parsed_cv = ParsedCV.model_construct(
            name="A" * 201,
            email="test@example.com",
            phone="",
            skills=[],
            experience=[],
            education=[],
            summary="",
        )
        errors = validate_correction(parsed_cv)
        assert len(errors) == 1
        assert errors[0]["field"] == "name"
        assert "200" in errors[0]["reason"]

    def test_name_exactly_200_chars_passes(self):
        """Name with exactly 200 characters should pass."""
        parsed_cv = ParsedCV(name="A" * 200, email="test@example.com")
        errors = validate_correction(parsed_cv)
        assert errors == []

    def test_empty_email_fails(self):
        """Empty email should produce a validation error."""
        parsed_cv = ParsedCV(name="Test Name", email="")
        errors = validate_correction(parsed_cv)
        assert len(errors) == 1
        assert errors[0]["field"] == "email"

    def test_email_exceeds_254_chars_fails(self):
        """Email exceeding 254 characters should produce a validation error.

        Note: ParsedCV has max_length=254 on email field, so we use
        model_construct to bypass Pydantic validation for this edge case test.
        """
        long_email = "a" * 246 + "@test.com"  # 255 chars, exceeds 254
        parsed_cv = ParsedCV.model_construct(
            name="Test Name",
            email=long_email,
            phone="",
            skills=[],
            experience=[],
            education=[],
            summary="",
        )
        errors = validate_correction(parsed_cv)
        assert len(errors) == 1
        assert errors[0]["field"] == "email"
        assert "254" in errors[0]["reason"]

    def test_invalid_email_format_fails(self):
        """Invalid email format should produce a validation error."""
        parsed_cv = ParsedCV(name="Test Name", email="not-an-email")
        errors = validate_correction(parsed_cv)
        assert len(errors) == 1
        assert errors[0]["field"] == "email"

    def test_email_without_domain_dot_fails(self):
        """Email without a dot in domain should fail."""
        parsed_cv = ParsedCV(name="Test Name", email="user@domain")
        errors = validate_correction(parsed_cv)
        assert len(errors) == 1
        assert errors[0]["field"] == "email"

    def test_valid_email_passes(self):
        """Valid email should pass."""
        parsed_cv = ParsedCV(name="Test Name", email="user@domain.com")
        errors = validate_correction(parsed_cv)
        assert errors == []

    def test_both_name_and_email_invalid(self):
        """Both invalid name and email should produce two errors."""
        parsed_cv = ParsedCV(name="", email="invalid")
        errors = validate_correction(parsed_cv)
        assert len(errors) == 2
        fields = [e["field"] for e in errors]
        assert "name" in fields
        assert "email" in fields


# ─── Tests: list_review_queue ──────────────────────────────────────────


class TestListReviewQueue:
    """Tests for the list_review_queue method."""

    @pytest.mark.asyncio
    async def test_returns_paginated_results(
        self, service, mock_cv_document_repo, sample_cv_document
    ):
        """Should return paginated review queue from repository."""
        mock_cv_document_repo.find_needs_review.return_value = (
            [sample_cv_document],
            1,
        )

        result = await service.list_review_queue(page=1, page_size=20)

        assert isinstance(result, PaginatedReviewQueue)
        assert result.documents == [sample_cv_document]
        assert result.total_count == 1
        assert result.page == 1
        assert result.page_size == 20
        mock_cv_document_repo.find_needs_review.assert_called_once_with(
            page=1, page_size=20
        )

    @pytest.mark.asyncio
    async def test_empty_queue(self, service, mock_cv_document_repo):
        """Should return empty list when no documents need review."""
        mock_cv_document_repo.find_needs_review.return_value = ([], 0)

        result = await service.list_review_queue()

        assert result.documents == []
        assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_custom_pagination(self, service, mock_cv_document_repo):
        """Should pass custom pagination parameters to repository."""
        mock_cv_document_repo.find_needs_review.return_value = ([], 0)

        await service.list_review_queue(page=3, page_size=50)

        mock_cv_document_repo.find_needs_review.assert_called_once_with(
            page=3, page_size=50
        )

    @pytest.mark.asyncio
    async def test_invalid_page_raises_error(self, service):
        """Should raise ValueError for page < 1."""
        with pytest.raises(ValueError, match="page must be >= 1"):
            await service.list_review_queue(page=0)

    @pytest.mark.asyncio
    async def test_invalid_page_size_raises_error(self, service):
        """Should raise ValueError for page_size outside 1-100."""
        with pytest.raises(ValueError, match="page_size must be between 1 and 100"):
            await service.list_review_queue(page_size=101)

        with pytest.raises(ValueError, match="page_size must be between 1 and 100"):
            await service.list_review_queue(page_size=0)


# ─── Tests: submit_correction ──────────────────────────────────────────


class TestSubmitCorrection:
    """Tests for the submit_correction method."""

    @pytest.mark.asyncio
    async def test_successful_correction(
        self,
        service,
        mock_cv_document_repo,
        mock_candidate_creator,
        sample_cv_document,
        valid_parsed_cv,
    ):
        """Should validate, store correction, create candidate, and set status to completed."""
        mock_cv_document_repo.get_by_id.return_value = sample_cv_document

        with patch(
            "src.modules.recruitment.application.review_service.log_audit",
            new_callable=AsyncMock,
        ):
            result = await service.submit_correction(
                cv_document_id=sample_cv_document.id,
                corrected_data=valid_parsed_cv,
            )

        # Candidate should be created
        mock_candidate_creator.create_or_update_candidate.assert_called_once_with(
            parsed_cv=valid_parsed_cv,
            cv_document_id=sample_cv_document.id,
            source_email_id=None,
            confidence_score=1.0,
        )

        # CVDocument should be updated with corrected data and completed status
        assert sample_cv_document.parsed_cv_data == valid_parsed_cv.model_dump()
        assert sample_cv_document.processing_status == ProcessingStatus.COMPLETED
        mock_cv_document_repo.update.assert_called()

    @pytest.mark.asyncio
    async def test_validation_failure_raises_error(
        self, service, mock_cv_document_repo
    ):
        """Should raise ReviewValidationError when corrected data is invalid."""
        invalid_cv = ParsedCV(name="", email="invalid")

        with pytest.raises(ReviewValidationError) as exc_info:
            await service.submit_correction(
                cv_document_id=uuid4(),
                corrected_data=invalid_cv,
            )

        assert len(exc_info.value.errors) == 2
        # Should not attempt to get document or create candidate
        mock_cv_document_repo.get_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_document_not_found_raises_error(
        self, service, mock_cv_document_repo, valid_parsed_cv
    ):
        """Should raise CVDocumentNotFoundError when document doesn't exist."""
        mock_cv_document_repo.get_by_id.return_value = None

        with pytest.raises(CVDocumentNotFoundError):
            await service.submit_correction(
                cv_document_id=uuid4(),
                corrected_data=valid_parsed_cv,
            )

    @pytest.mark.asyncio
    async def test_correction_stores_parsed_cv_data(
        self,
        service,
        mock_cv_document_repo,
        sample_cv_document,
        valid_parsed_cv,
    ):
        """Should store the corrected parsed_cv_data on the CVDocument."""
        mock_cv_document_repo.get_by_id.return_value = sample_cv_document

        with patch(
            "src.modules.recruitment.application.review_service.log_audit",
            new_callable=AsyncMock,
        ):
            await service.submit_correction(
                cv_document_id=sample_cv_document.id,
                corrected_data=valid_parsed_cv,
            )

        assert sample_cv_document.parsed_cv_data == valid_parsed_cv.model_dump()


# ─── Tests: retry_parse ────────────────────────────────────────────────


class TestRetryParse:
    """Tests for the retry_parse method."""

    @pytest.mark.asyncio
    async def test_successful_retry(
        self,
        service,
        mock_cv_document_repo,
        mock_cv_retry_parser,
        sample_cv_document,
    ):
        """Should delegate to cv_retry_parser and return updated document."""
        parsed_cv = ParsedCV(
            name="Nguyen Van A",
            email="test@example.com",
            phone="0901234567",
            skills=["Python"],
        )
        mock_cv_retry_parser.retry_llm_parse.return_value = parsed_cv

        # First call returns the document, subsequent calls return updated doc
        updated_doc = CVDocument(
            id=sample_cv_document.id,
            gmail_message_id="msg_123",
            original_filename="resume.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            file_path="storage/cv/msg_123/resume.pdf",
            processing_status=ProcessingStatus.COMPLETED,
        )
        mock_cv_document_repo.get_by_id.side_effect = [
            sample_cv_document,  # initial check
            updated_doc,  # final fetch
        ]

        with patch(
            "src.modules.recruitment.application.review_service.log_audit",
            new_callable=AsyncMock,
        ):
            result = await service.retry_parse(sample_cv_document.id)

        assert result.processing_status == ProcessingStatus.COMPLETED
        mock_cv_retry_parser.retry_llm_parse.assert_called_once_with(
            sample_cv_document.id
        )

    @pytest.mark.asyncio
    async def test_document_not_found_raises_error(
        self, service, mock_cv_document_repo
    ):
        """Should raise CVDocumentNotFoundError when document doesn't exist."""
        mock_cv_document_repo.get_by_id.return_value = None

        with pytest.raises(CVDocumentNotFoundError):
            await service.retry_parse(uuid4())

    @pytest.mark.asyncio
    async def test_timeout_sets_needs_review(
        self,
        service,
        mock_cv_document_repo,
        mock_cv_retry_parser,
        sample_cv_document,
    ):
        """Should set status to needs_review when retry times out."""

        async def slow_parse(cv_document_id):
            await asyncio.sleep(120)  # Exceeds 60s timeout
            return None

        mock_cv_retry_parser.retry_llm_parse.side_effect = slow_parse
        mock_cv_document_repo.get_by_id.return_value = sample_cv_document

        with patch(
            "src.modules.recruitment.application.review_service.log_audit",
            new_callable=AsyncMock,
        ), patch(
            "src.modules.recruitment.application.review_service._RETRY_TIMEOUT_SECONDS",
            0.1,  # Use very short timeout for test
        ):
            result = await service.retry_parse(sample_cv_document.id)

        assert result.processing_status == ProcessingStatus.NEEDS_REVIEW
        assert "timed out" in (result.processing_error or "")

    @pytest.mark.asyncio
    async def test_failure_sets_needs_review(
        self,
        service,
        mock_cv_document_repo,
        mock_cv_retry_parser,
        sample_cv_document,
    ):
        """Should set status to needs_review when retry fails with exception."""
        mock_cv_retry_parser.retry_llm_parse.side_effect = RuntimeError(
            "LLM service unavailable"
        )
        mock_cv_document_repo.get_by_id.return_value = sample_cv_document

        with patch(
            "src.modules.recruitment.application.review_service.log_audit",
            new_callable=AsyncMock,
        ):
            result = await service.retry_parse(sample_cv_document.id)

        assert result.processing_status == ProcessingStatus.NEEDS_REVIEW
        assert "LLM service unavailable" in (result.processing_error or "")


# ─── Tests: dismiss ────────────────────────────────────────────────────


class TestDismiss:
    """Tests for the dismiss method."""

    @pytest.mark.asyncio
    async def test_successful_dismiss(
        self,
        service,
        mock_cv_document_repo,
        mock_session,
        sample_cv_document,
    ):
        """Should set processing_status to dismissed."""
        mock_cv_document_repo.get_by_id.return_value = sample_cv_document

        with patch(
            "src.modules.recruitment.application.review_service.log_audit",
            new_callable=AsyncMock,
        ):
            await service.dismiss(sample_cv_document.id)

        assert sample_cv_document.processing_status == ProcessingStatus.DISMISSED
        mock_cv_document_repo.update.assert_called_with(sample_cv_document)
        mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_document_not_found_raises_error(
        self, service, mock_cv_document_repo
    ):
        """Should raise CVDocumentNotFoundError when document doesn't exist."""
        mock_cv_document_repo.get_by_id.return_value = None

        with pytest.raises(CVDocumentNotFoundError):
            await service.dismiss(uuid4())
