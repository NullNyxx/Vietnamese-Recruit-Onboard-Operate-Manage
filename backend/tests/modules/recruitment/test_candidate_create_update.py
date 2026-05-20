"""Unit tests for CandidateService — create/update and deduplication (Task 5.1).

Tests cover:
- Candidate creation from valid parsed CV data
- Candidate update (deduplication by email, preserving status)
- Field validation (name, email)
- CV document linking
- Confidence score storage
- Parsed CV JSON storage
- Gmail label application

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.modules.recruitment.application.candidate_service import (
    CandidateService,
    CandidateValidationError,
    validate_candidate_fields,
)
from src.modules.recruitment.domain.entities import Candidate, CVDocument
from src.modules.recruitment.domain.enums import CandidateStatus
from src.modules.recruitment.domain.value_objects import (
    EducationItem,
    ExperienceItem,
    ParsedCV,
)


# ─── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def mock_candidate_repo() -> AsyncMock:
    """Create a mock CandidateRepository."""
    repo = AsyncMock()
    repo.find_by_email = AsyncMock(return_value=None)
    repo.create = AsyncMock(side_effect=lambda c: c)
    repo.update = AsyncMock(side_effect=lambda c: c)
    return repo


@pytest.fixture
def mock_cv_document_repo() -> AsyncMock:
    """Create a mock CVDocumentRepository."""
    repo = AsyncMock()
    cv_doc = CVDocument(
        id=uuid4(),
        gmail_message_id="msg_123",
        original_filename="cv.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        file_path="storage/cv/msg_123/cv.pdf",
    )
    repo.get_by_id = AsyncMock(return_value=cv_doc)
    repo.update = AsyncMock(side_effect=lambda d: d)
    return repo


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock AsyncSession."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def sample_parsed_cv() -> ParsedCV:
    """Create a sample ParsedCV with valid data."""
    return ParsedCV(
        name="Nguyen Van A",
        email="nguyen.a@example.com",
        phone="0901234567",
        skills=["Python", "FastAPI", "PostgreSQL"],
        experience=[
            ExperienceItem(
                company="Tech Corp",
                title="Senior Developer",
                duration="2020-2023",
                description="Built microservices",
            )
        ],
        education=[
            EducationItem(
                institution="HCMUT",
                degree="Bachelor",
                field="Computer Science",
                year="2020",
            )
        ],
        summary="Experienced Python developer",
    )


@pytest.fixture
def candidate_service(
    mock_candidate_repo: AsyncMock,
    mock_cv_document_repo: AsyncMock,
    mock_session: AsyncMock,
) -> CandidateService:
    """Create a CandidateService with mocked dependencies."""
    return CandidateService(
        candidate_repo=mock_candidate_repo,
        cv_document_repo=mock_cv_document_repo,
        minio_client=AsyncMock(),
        session=mock_session,
    )


# ─── Validation tests ─────────────────────────────────────────────────


class TestValidateCandidateFields:
    """Tests for the validate_candidate_fields function."""

    def test_valid_fields_returns_empty_errors(self) -> None:
        """Valid name and email produce no errors."""
        cv = ParsedCV(name="John Doe", email="john@example.com")
        errors = validate_candidate_fields(cv)
        assert errors == []

    def test_empty_name_returns_error(self) -> None:
        """Empty name produces a validation error."""
        cv = ParsedCV(name="", email="john@example.com")
        errors = validate_candidate_fields(cv)
        assert len(errors) == 1
        assert errors[0]["field"] == "name"

    def test_whitespace_only_name_returns_error(self) -> None:
        """Whitespace-only name produces a validation error."""
        cv = ParsedCV(name="   ", email="john@example.com")
        errors = validate_candidate_fields(cv)
        assert len(errors) == 1
        assert errors[0]["field"] == "name"

    def test_name_exceeds_255_chars_returns_error(self) -> None:
        """Name exceeding 255 characters produces a validation error.

        Note: ParsedCV model limits name to 200 chars, so this test
        constructs a ParsedCV with model_construct to bypass Pydantic
        validation and test our validator directly.
        """
        cv = ParsedCV.model_construct(name="A" * 256, email="john@example.com")
        errors = validate_candidate_fields(cv)
        assert len(errors) == 1
        assert errors[0]["field"] == "name"
        assert "255" in errors[0]["reason"]

    def test_name_exactly_255_chars_is_valid(self) -> None:
        """Name at exactly 255 characters is valid (within ParsedCV max_length=200)."""
        cv = ParsedCV(name="A" * 200, email="john@example.com")
        errors = validate_candidate_fields(cv)
        assert errors == []

    def test_empty_email_returns_error(self) -> None:
        """Empty email produces a validation error."""
        cv = ParsedCV(name="John", email="")
        errors = validate_candidate_fields(cv)
        assert len(errors) == 1
        assert errors[0]["field"] == "email"

    def test_email_without_at_returns_error(self) -> None:
        """Email without @ produces a validation error."""
        cv = ParsedCV(name="John", email="johnexample.com")
        errors = validate_candidate_fields(cv)
        assert len(errors) == 1
        assert errors[0]["field"] == "email"

    def test_email_with_empty_local_part_returns_error(self) -> None:
        """Email with empty local part produces a validation error."""
        cv = ParsedCV(name="John", email="@example.com")
        errors = validate_candidate_fields(cv)
        assert len(errors) == 1
        assert errors[0]["field"] == "email"

    def test_email_with_empty_domain_returns_error(self) -> None:
        """Email with empty domain part produces a validation error."""
        cv = ParsedCV(name="John", email="john@")
        errors = validate_candidate_fields(cv)
        assert len(errors) == 1
        assert errors[0]["field"] == "email"

    def test_both_invalid_returns_multiple_errors(self) -> None:
        """Both invalid name and email produce two errors."""
        cv = ParsedCV(name="", email="invalid")
        errors = validate_candidate_fields(cv)
        assert len(errors) == 2
        fields = {e["field"] for e in errors}
        assert fields == {"name", "email"}

    def test_valid_email_formats(self) -> None:
        """Various valid email formats pass validation."""
        valid_emails = [
            "user@domain.com",
            "user.name@domain.co.uk",
            "user+tag@domain.com",
            "a@b.c",
        ]
        for email in valid_emails:
            cv = ParsedCV(name="John", email=email)
            errors = validate_candidate_fields(cv)
            assert errors == [], f"Expected no errors for email: {email}"


# ─── Service tests ─────────────────────────────────────────────────────


class TestCandidateServiceCreateOrUpdate:
    """Tests for CandidateService.create_or_update_candidate."""

    @pytest.mark.asyncio
    async def test_creates_new_candidate_when_no_existing(
        self,
        candidate_service: CandidateService,
        mock_candidate_repo: AsyncMock,
        mock_cv_document_repo: AsyncMock,
        sample_parsed_cv: ParsedCV,
    ) -> None:
        """Creates a new candidate when no existing candidate with same email."""
        cv_doc_id = uuid4()
        source_email_id = uuid4()

        with patch(
            "src.modules.recruitment.application.candidate_service.log_audit",
            new_callable=AsyncMock,
        ):
            result = await candidate_service.create_or_update_candidate(
                parsed_cv=sample_parsed_cv,
                cv_document_id=cv_doc_id,
                source_email_id=source_email_id,
                confidence_score=0.85,
            )

        assert result.name == "Nguyen Van A"
        assert result.email == "nguyen.a@example.com"
        assert result.status == CandidateStatus.NEW
        assert result.confidence_score == 0.85
        assert result.parsed_cv_json is not None
        assert result.parsed_cv_json["name"] == "Nguyen Van A"
        mock_candidate_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_updates_existing_candidate_preserving_status(
        self,
        candidate_service: CandidateService,
        mock_candidate_repo: AsyncMock,
        mock_cv_document_repo: AsyncMock,
        sample_parsed_cv: ParsedCV,
    ) -> None:
        """Updates existing candidate data but preserves their status."""
        existing = Candidate(
            id=uuid4(),
            name="Old Name",
            email="nguyen.a@example.com",
            phone="0900000000",
            skills=["Java"],
            experience=[],
            education=[],
            summary="Old summary",
            status=CandidateStatus.REVIEWING,
            confidence_score=0.6,
        )
        mock_candidate_repo.find_by_email = AsyncMock(return_value=existing)

        cv_doc_id = uuid4()

        with patch(
            "src.modules.recruitment.application.candidate_service.log_audit",
            new_callable=AsyncMock,
        ):
            result = await candidate_service.create_or_update_candidate(
                parsed_cv=sample_parsed_cv,
                cv_document_id=cv_doc_id,
                source_email_id=None,
                confidence_score=0.9,
            )

        # Data fields updated
        assert result.name == "Nguyen Van A"
        assert result.phone == "0901234567"
        assert result.skills == ["Python", "FastAPI", "PostgreSQL"]
        assert result.confidence_score == 0.9
        assert result.summary == "Experienced Python developer"
        # Status preserved
        assert result.status == CandidateStatus.REVIEWING
        mock_candidate_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_links_cv_document_to_candidate(
        self,
        candidate_service: CandidateService,
        mock_candidate_repo: AsyncMock,
        mock_cv_document_repo: AsyncMock,
        sample_parsed_cv: ParsedCV,
    ) -> None:
        """Links the CV document to the candidate after creation."""
        cv_doc_id = uuid4()
        cv_doc = CVDocument(
            id=cv_doc_id,
            gmail_message_id="msg_456",
            original_filename="resume.pdf",
            mime_type="application/pdf",
            size_bytes=2048,
            file_path="storage/cv/msg_456/resume.pdf",
        )
        mock_cv_document_repo.get_by_id = AsyncMock(return_value=cv_doc)

        with patch(
            "src.modules.recruitment.application.candidate_service.log_audit",
            new_callable=AsyncMock,
        ):
            result = await candidate_service.create_or_update_candidate(
                parsed_cv=sample_parsed_cv,
                cv_document_id=cv_doc_id,
                source_email_id=None,
                confidence_score=0.8,
            )

        # Verify CV document was linked
        assert cv_doc.candidate_id == result.id

    @pytest.mark.asyncio
    async def test_stores_parsed_cv_json(
        self,
        candidate_service: CandidateService,
        mock_candidate_repo: AsyncMock,
        sample_parsed_cv: ParsedCV,
    ) -> None:
        """Stores the complete parsed_cv_json on the Candidate record."""
        cv_doc_id = uuid4()

        with patch(
            "src.modules.recruitment.application.candidate_service.log_audit",
            new_callable=AsyncMock,
        ):
            result = await candidate_service.create_or_update_candidate(
                parsed_cv=sample_parsed_cv,
                cv_document_id=cv_doc_id,
                source_email_id=None,
                confidence_score=0.75,
            )

        assert result.parsed_cv_json is not None
        assert result.parsed_cv_json["name"] == "Nguyen Van A"
        assert result.parsed_cv_json["email"] == "nguyen.a@example.com"
        assert result.parsed_cv_json["skills"] == ["Python", "FastAPI", "PostgreSQL"]
        assert len(result.parsed_cv_json["experience"]) == 1
        assert len(result.parsed_cv_json["education"]) == 1

    @pytest.mark.asyncio
    async def test_raises_validation_error_for_empty_name(
        self,
        candidate_service: CandidateService,
        mock_cv_document_repo: AsyncMock,
    ) -> None:
        """Raises CandidateValidationError when name is empty."""
        cv = ParsedCV(name="", email="valid@example.com")
        cv_doc_id = uuid4()

        with pytest.raises(CandidateValidationError) as exc_info:
            await candidate_service.create_or_update_candidate(
                parsed_cv=cv,
                cv_document_id=cv_doc_id,
                source_email_id=None,
                confidence_score=0.8,
            )

        assert any(e["field"] == "name" for e in exc_info.value.errors)

    @pytest.mark.asyncio
    async def test_raises_validation_error_for_invalid_email(
        self,
        candidate_service: CandidateService,
        mock_cv_document_repo: AsyncMock,
    ) -> None:
        """Raises CandidateValidationError when email is invalid."""
        cv = ParsedCV(name="John", email="not-an-email")
        cv_doc_id = uuid4()

        with pytest.raises(CandidateValidationError) as exc_info:
            await candidate_service.create_or_update_candidate(
                parsed_cv=cv,
                cv_document_id=cv_doc_id,
                source_email_id=None,
                confidence_score=0.8,
            )

        assert any(e["field"] == "email" for e in exc_info.value.errors)

    @pytest.mark.asyncio
    async def test_stores_validation_errors_on_cv_document(
        self,
        candidate_service: CandidateService,
        mock_cv_document_repo: AsyncMock,
    ) -> None:
        """Stores validation errors on the CV document when validation fails."""
        cv = ParsedCV(name="", email="invalid")
        cv_doc_id = uuid4()
        cv_doc = CVDocument(
            id=cv_doc_id,
            gmail_message_id="msg_789",
            original_filename="cv.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            file_path="storage/cv/msg_789/cv.pdf",
        )
        mock_cv_document_repo.get_by_id = AsyncMock(return_value=cv_doc)

        with pytest.raises(CandidateValidationError):
            await candidate_service.create_or_update_candidate(
                parsed_cv=cv,
                cv_document_id=cv_doc_id,
                source_email_id=None,
                confidence_score=0.8,
            )

        assert cv_doc.validation_errors is not None
        assert len(cv_doc.validation_errors) == 2

    @pytest.mark.asyncio
    async def test_new_candidate_has_source_email_id(
        self,
        candidate_service: CandidateService,
        mock_candidate_repo: AsyncMock,
        sample_parsed_cv: ParsedCV,
    ) -> None:
        """New candidate stores the source_email_message_id."""
        cv_doc_id = uuid4()
        source_email_id = uuid4()

        with patch(
            "src.modules.recruitment.application.candidate_service.log_audit",
            new_callable=AsyncMock,
        ):
            result = await candidate_service.create_or_update_candidate(
                parsed_cv=sample_parsed_cv,
                cv_document_id=cv_doc_id,
                source_email_id=source_email_id,
                confidence_score=0.85,
            )

        assert result.source_email_message_id == source_email_id

    @pytest.mark.asyncio
    async def test_email_deduplication_is_case_insensitive(
        self,
        candidate_service: CandidateService,
        mock_candidate_repo: AsyncMock,
        mock_cv_document_repo: AsyncMock,
    ) -> None:
        """Deduplication by email is case-insensitive."""
        existing = Candidate(
            id=uuid4(),
            name="Old Name",
            email="john@example.com",
            status=CandidateStatus.NEW,
            confidence_score=0.7,
        )
        mock_candidate_repo.find_by_email = AsyncMock(return_value=existing)

        cv = ParsedCV(name="John Doe", email="JOHN@EXAMPLE.COM")
        cv_doc_id = uuid4()

        with patch(
            "src.modules.recruitment.application.candidate_service.log_audit",
            new_callable=AsyncMock,
        ):
            result = await candidate_service.create_or_update_candidate(
                parsed_cv=cv,
                cv_document_id=cv_doc_id,
                source_email_id=None,
                confidence_score=0.9,
            )

        # Should update existing, not create new
        assert result.id == existing.id
        assert result.name == "John Doe"
        mock_candidate_repo.update.assert_called_once()
        mock_candidate_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_gmail_label_applied_on_success(
        self,
        mock_candidate_repo: AsyncMock,
        mock_cv_document_repo: AsyncMock,
        mock_session: AsyncMock,
        sample_parsed_cv: ParsedCV,
    ) -> None:
        """Gmail label 'VroomHR/processed' is applied after candidate creation."""
        mock_label_service = AsyncMock()
        user_id = uuid4()
        access_token = "test_token"

        service = CandidateService(
            candidate_repo=mock_candidate_repo,
            cv_document_repo=mock_cv_document_repo,
            minio_client=AsyncMock(),
            session=mock_session,
            gmail_label_service=mock_label_service,
            access_token_provider=AsyncMock(return_value=access_token),
            user_id_provider=AsyncMock(return_value=user_id),
        )

        source_email_id = uuid4()
        cv_doc_id = uuid4()

        with patch(
            "src.modules.recruitment.application.candidate_service.log_audit",
            new_callable=AsyncMock,
        ):
            await service.create_or_update_candidate(
                parsed_cv=sample_parsed_cv,
                cv_document_id=cv_doc_id,
                source_email_id=source_email_id,
                confidence_score=0.85,
            )

        mock_label_service.add_label.assert_called_once_with(
            user_id=user_id,
            message_id=str(source_email_id),
            label_name="VroomHR/processed",
            access_token=access_token,
        )

    @pytest.mark.asyncio
    async def test_gmail_label_failure_does_not_block(
        self,
        mock_candidate_repo: AsyncMock,
        mock_cv_document_repo: AsyncMock,
        mock_session: AsyncMock,
        sample_parsed_cv: ParsedCV,
    ) -> None:
        """Gmail label failure does not prevent candidate creation."""
        mock_label_service = AsyncMock()
        mock_label_service.add_label = AsyncMock(side_effect=Exception("Gmail error"))

        service = CandidateService(
            candidate_repo=mock_candidate_repo,
            cv_document_repo=mock_cv_document_repo,
            minio_client=AsyncMock(),
            session=mock_session,
            gmail_label_service=mock_label_service,
            access_token_provider=AsyncMock(return_value="token"),
            user_id_provider=AsyncMock(return_value=uuid4()),
        )

        cv_doc_id = uuid4()
        source_email_id = uuid4()

        with patch(
            "src.modules.recruitment.application.candidate_service.log_audit",
            new_callable=AsyncMock,
        ):
            # Should not raise despite Gmail failure
            result = await service.create_or_update_candidate(
                parsed_cv=sample_parsed_cv,
                cv_document_id=cv_doc_id,
                source_email_id=source_email_id,
                confidence_score=0.85,
            )

        assert result.name == "Nguyen Van A"

    @pytest.mark.asyncio
    async def test_handles_missing_optional_fields(
        self,
        candidate_service: CandidateService,
        mock_candidate_repo: AsyncMock,
    ) -> None:
        """Creates candidate with defaults when optional fields are missing."""
        cv = ParsedCV(name="Minimal", email="min@test.com")
        cv_doc_id = uuid4()

        with patch(
            "src.modules.recruitment.application.candidate_service.log_audit",
            new_callable=AsyncMock,
        ):
            result = await candidate_service.create_or_update_candidate(
                parsed_cv=cv,
                cv_document_id=cv_doc_id,
                source_email_id=None,
                confidence_score=0.5,
            )

        assert result.phone == ""
        assert result.skills == []
        assert result.experience == []
        assert result.education == []
        assert result.summary == ""
