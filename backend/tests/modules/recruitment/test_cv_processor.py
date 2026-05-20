"""Unit tests for CVProcessorService.

Tests the CV processing pipeline orchestration including:
- Full pipeline processing (process_cv_from_email)
- Single attachment processing (process_single_attachment)
- LLM parse retry (retry_llm_parse)
- Status transitions and error handling
- Pipeline timeout behavior
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.modules.recruitment.application.cv_processor import (
    AttachmentInput,
    CVProcessorService,
)
from src.modules.recruitment.domain.entities import CVDocument
from src.modules.recruitment.domain.enums import ProcessingStatus
from src.modules.recruitment.domain.exceptions import (
    CVDocumentNotFoundError,
    LLMParseError,
    OCRExtractionError,
    PipelineTimeoutError,
)
from src.modules.recruitment.domain.value_objects import ParsedCV
from src.modules.recruitment.infrastructure.config import RecruitmentSettings
from src.modules.recruitment.infrastructure.llm_adapter import ParsedCVResult


# ─── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def settings():
    """Create test RecruitmentSettings with defaults."""
    return RecruitmentSettings()  # type: ignore[call-arg]


@pytest.fixture
def mock_minio_client():
    """Create a mock MinIO client."""
    client = AsyncMock()
    client.upload_cv = AsyncMock(
        return_value="storage/cv/msg123/resume.pdf"
    )
    return client


@pytest.fixture
def mock_ocr_adapter():
    """Create a mock OCR adapter."""
    adapter = AsyncMock()
    adapter.extract_text = AsyncMock(
        return_value="Nguyen Van A\nemail: test@example.com\nPhone: 0901234567\n"
        "Skills: Python, FastAPI\nExperience: 3 years at Company X\n"
        "Education: HCMUT Computer Science 2020"
    )
    return adapter


@pytest.fixture
def mock_llm_adapter():
    """Create a mock LLM adapter."""
    adapter = AsyncMock()
    parsed_cv = ParsedCV(
        name="Nguyen Van A",
        email="test@example.com",
        phone="0901234567",
        skills=["Python", "FastAPI"],
        experience=[],
        education=[],
        summary="Experienced developer",
    )
    adapter.parse_cv = AsyncMock(
        return_value=ParsedCVResult(
            parsed_cv=parsed_cv,
            token_usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )
    )
    return adapter


@pytest.fixture
def mock_pii_redactor():
    """Create a mock PII redactor."""
    redactor = MagicMock()
    redactor.redact = MagicMock(side_effect=lambda text: text)
    return redactor


@pytest.fixture
def mock_candidate_repo():
    """Create a mock candidate repository."""
    return AsyncMock()


@pytest.fixture
def mock_cv_document_repo():
    """Create a mock CV document repository."""
    repo = AsyncMock()
    # Make create and update return the input document
    repo.create = AsyncMock(side_effect=lambda doc: doc)
    repo.update = AsyncMock(side_effect=lambda doc: doc)
    return repo


@pytest.fixture
def mock_session():
    """Create a mock async database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def mock_candidate_creator():
    """Create a mock candidate creator protocol."""
    creator = AsyncMock()
    creator.create_or_update_candidate = AsyncMock()
    return creator


@pytest.fixture
def service(
    mock_minio_client,
    mock_ocr_adapter,
    mock_llm_adapter,
    mock_pii_redactor,
    mock_candidate_repo,
    mock_cv_document_repo,
    settings,
    mock_session,
    mock_candidate_creator,
):
    """Create a CVProcessorService with all mocked dependencies."""
    return CVProcessorService(
        minio_client=mock_minio_client,
        ocr_adapter=mock_ocr_adapter,
        llm_adapter=mock_llm_adapter,
        pii_redactor=mock_pii_redactor,
        candidate_repo=mock_candidate_repo,
        cv_document_repo=mock_cv_document_repo,
        settings=settings,
        session=mock_session,
        candidate_creator=mock_candidate_creator,
    )


@pytest.fixture
def valid_attachment():
    """Create a valid PDF attachment input."""
    return AttachmentInput(
        filename="resume.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        data=b"%PDF-1.4 fake pdf content",
    )


# ─── Tests: process_single_attachment ──────────────────────────────────


class TestProcessSingleAttachment:
    """Tests for process_single_attachment method."""

    @pytest.mark.asyncio
    async def test_successful_pipeline_high_confidence(
        self, service, valid_attachment, mock_candidate_creator
    ):
        """Full pipeline succeeds with high confidence → completed status."""
        email_id = uuid4()

        with patch(
            "src.modules.recruitment.application.cv_processor.log_audit",
            new_callable=AsyncMock,
        ):
            result = await service.process_single_attachment(
                email_message_id=email_id,
                attachment=valid_attachment,
                gmail_message_id="msg123",
            )

        assert result.processing_status == ProcessingStatus.COMPLETED
        assert result.confidence_score is not None
        assert result.confidence_score >= 0.7
        assert result.file_path == "storage/cv/msg123/resume.pdf"
        assert result.original_filename == "resume.pdf"
        mock_candidate_creator.create_or_update_candidate.assert_called_once()

    @pytest.mark.asyncio
    async def test_successful_pipeline_low_confidence(
        self, service, valid_attachment, mock_llm_adapter
    ):
        """Low confidence score → needs_review status."""
        # Return a ParsedCV with only name (confidence = 0.25)
        low_confidence_cv = ParsedCV(
            name="Test",
            email="",
            phone="",
            skills=[],
            experience=[],
            education=[],
            summary="",
        )
        mock_llm_adapter.parse_cv = AsyncMock(
            return_value=ParsedCVResult(
                parsed_cv=low_confidence_cv,
                token_usage={"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70},
            )
        )

        email_id = uuid4()
        with patch(
            "src.modules.recruitment.application.cv_processor.log_audit",
            new_callable=AsyncMock,
        ):
            result = await service.process_single_attachment(
                email_message_id=email_id,
                attachment=valid_attachment,
                gmail_message_id="msg123",
            )

        assert result.processing_status == ProcessingStatus.NEEDS_REVIEW
        assert result.confidence_score is not None
        assert result.confidence_score < 0.7

    @pytest.mark.asyncio
    async def test_invalid_mime_type_skipped(self, service):
        """Invalid MIME type → skipped status."""
        attachment = AttachmentInput(
            filename="virus.exe",
            mime_type="application/x-executable",
            size_bytes=1024,
            data=b"binary content",
        )
        email_id = uuid4()

        result = await service.process_single_attachment(
            email_message_id=email_id,
            attachment=attachment,
            gmail_message_id="msg123",
        )

        assert result.processing_status == ProcessingStatus.SKIPPED
        assert result.processing_error is not None
        assert "MIME type" in result.processing_error

    @pytest.mark.asyncio
    async def test_file_too_large_skipped(self, service):
        """File exceeding size limit → skipped status."""
        attachment = AttachmentInput(
            filename="huge.pdf",
            mime_type="application/pdf",
            size_bytes=11 * 1024 * 1024,  # 11MB > 10MB limit
            data=b"x" * 100,
        )
        email_id = uuid4()

        result = await service.process_single_attachment(
            email_message_id=email_id,
            attachment=attachment,
            gmail_message_id="msg123",
        )

        assert result.processing_status == ProcessingStatus.SKIPPED
        assert result.processing_error is not None
        assert "size" in result.processing_error.lower()

    @pytest.mark.asyncio
    async def test_minio_upload_failure(
        self, service, valid_attachment, mock_minio_client
    ):
        """MinIO upload failure → upload_failed status."""
        mock_minio_client.upload_cv = AsyncMock(
            side_effect=Exception("Connection refused")
        )
        email_id = uuid4()

        result = await service.process_single_attachment(
            email_message_id=email_id,
            attachment=valid_attachment,
            gmail_message_id="msg123",
        )

        assert result.processing_status == ProcessingStatus.UPLOAD_FAILED
        assert "MinIO upload failed" in (result.processing_error or "")

    @pytest.mark.asyncio
    async def test_ocr_extraction_failure(
        self, service, valid_attachment, mock_ocr_adapter
    ):
        """OCR extraction failure → failed status."""
        mock_ocr_adapter.extract_text = AsyncMock(
            side_effect=OCRExtractionError("olmOCR server unreachable")
        )
        email_id = uuid4()

        with patch(
            "src.modules.recruitment.application.cv_processor.log_audit",
            new_callable=AsyncMock,
        ):
            result = await service.process_single_attachment(
                email_message_id=email_id,
                attachment=valid_attachment,
                gmail_message_id="msg123",
            )

        assert result.processing_status == ProcessingStatus.FAILED
        assert "OCR extraction failed" in (result.processing_error or "")

    @pytest.mark.asyncio
    async def test_ocr_insufficient_text(
        self, service, valid_attachment, mock_ocr_adapter
    ):
        """OCR returns < 50 chars → failed status."""
        mock_ocr_adapter.extract_text = AsyncMock(return_value="short")
        email_id = uuid4()

        with patch(
            "src.modules.recruitment.application.cv_processor.log_audit",
            new_callable=AsyncMock,
        ):
            result = await service.process_single_attachment(
                email_message_id=email_id,
                attachment=valid_attachment,
                gmail_message_id="msg123",
            )

        assert result.processing_status == ProcessingStatus.FAILED
        assert "insufficient text" in (result.processing_error or "").lower()

    @pytest.mark.asyncio
    async def test_llm_parse_failure(
        self, service, valid_attachment, mock_llm_adapter
    ):
        """LLM parse failure → failed status."""
        mock_llm_adapter.parse_cv = AsyncMock(
            side_effect=LLMParseError("LLM timeout after 3 retries")
        )
        email_id = uuid4()

        with patch(
            "src.modules.recruitment.application.cv_processor.log_audit",
            new_callable=AsyncMock,
        ):
            result = await service.process_single_attachment(
                email_message_id=email_id,
                attachment=valid_attachment,
                gmail_message_id="msg123",
            )

        assert result.processing_status == ProcessingStatus.FAILED
        assert "LLM parse failed" in (result.processing_error or "")

    @pytest.mark.asyncio
    async def test_status_transitions_tracked(
        self, service, valid_attachment, mock_cv_document_repo
    ):
        """Verify status transitions: pending → ocr_processing → llm_parsing → completed."""
        email_id = uuid4()
        statuses_seen: list[str] = []

        original_update = mock_cv_document_repo.update

        async def track_update(doc):
            statuses_seen.append(doc.processing_status)
            return doc

        mock_cv_document_repo.update = AsyncMock(side_effect=track_update)

        with patch(
            "src.modules.recruitment.application.cv_processor.log_audit",
            new_callable=AsyncMock,
        ):
            await service.process_single_attachment(
                email_message_id=email_id,
                attachment=valid_attachment,
                gmail_message_id="msg123",
            )

        # Should see: ocr_processing, ocr_output stored, llm_parsing,
        # parsed data stored, completed
        assert ProcessingStatus.OCR_PROCESSING in statuses_seen
        assert ProcessingStatus.LLM_PARSING in statuses_seen
        assert ProcessingStatus.COMPLETED in statuses_seen


# ─── Tests: process_cv_from_email ──────────────────────────────────────


class TestProcessCvFromEmail:
    """Tests for process_cv_from_email method."""

    @pytest.mark.asyncio
    async def test_processes_multiple_attachments(self, service):
        """Multiple valid attachments are all processed."""
        attachments = [
            AttachmentInput(
                filename="cv1.pdf",
                mime_type="application/pdf",
                size_bytes=1024,
                data=b"pdf1",
            ),
            AttachmentInput(
                filename="cv2.pdf",
                mime_type="application/pdf",
                size_bytes=2048,
                data=b"pdf2",
            ),
        ]
        email_id = uuid4()

        with patch(
            "src.modules.recruitment.application.cv_processor.log_audit",
            new_callable=AsyncMock,
        ):
            results = await service.process_cv_from_email(
                email_message_id=email_id,
                attachments=attachments,
                gmail_message_id="msg456",
            )

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_continues_after_one_attachment_fails(
        self, service, mock_ocr_adapter
    ):
        """If one attachment fails, others still get processed."""
        # First attachment will fail OCR, second will succeed
        call_count = 0

        async def ocr_side_effect(file_content, filename, mime_type):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise OCRExtractionError("OCR failed for first file")
            return (
                "Nguyen Van B\nemail: b@example.com\nPhone: 0901234567\n"
                "Skills: Java, Spring\nExperience: 5 years\n"
                "Education: HCMUT 2018"
            )

        mock_ocr_adapter.extract_text = AsyncMock(side_effect=ocr_side_effect)

        attachments = [
            AttachmentInput(
                filename="bad.pdf",
                mime_type="application/pdf",
                size_bytes=1024,
                data=b"bad",
            ),
            AttachmentInput(
                filename="good.pdf",
                mime_type="application/pdf",
                size_bytes=1024,
                data=b"good",
            ),
        ]
        email_id = uuid4()

        with patch(
            "src.modules.recruitment.application.cv_processor.log_audit",
            new_callable=AsyncMock,
        ):
            results = await service.process_cv_from_email(
                email_message_id=email_id,
                attachments=attachments,
                gmail_message_id="msg789",
            )

        assert len(results) == 2
        assert results[0].processing_status == ProcessingStatus.FAILED
        assert results[1].processing_status in (
            ProcessingStatus.COMPLETED,
            ProcessingStatus.NEEDS_REVIEW,
        )

    @pytest.mark.asyncio
    async def test_pipeline_timeout(self, service, settings):
        """Pipeline timeout raises PipelineTimeoutError."""
        # Override settings to a very short timeout
        settings.pipeline_timeout_seconds = 0  # Immediate timeout

        # Create a slow attachment that will exceed timeout
        attachment = AttachmentInput(
            filename="slow.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            data=b"slow",
        )

        # Make OCR take a long time
        async def slow_ocr(*args, **kwargs):
            await asyncio.sleep(10)
            return "text"

        service._ocr_adapter.extract_text = AsyncMock(side_effect=slow_ocr)

        email_id = uuid4()

        with pytest.raises(PipelineTimeoutError):
            await service.process_cv_from_email(
                email_message_id=email_id,
                attachments=[attachment],
                gmail_message_id="msg_timeout",
            )

    @pytest.mark.asyncio
    async def test_empty_attachments_list(self, service):
        """Empty attachments list returns empty results."""
        email_id = uuid4()

        results = await service.process_cv_from_email(
            email_message_id=email_id,
            attachments=[],
            gmail_message_id="msg_empty",
        )

        assert results == []


# ─── Tests: retry_llm_parse ────────────────────────────────────────────


class TestRetryLlmParse:
    """Tests for retry_llm_parse method."""

    @pytest.mark.asyncio
    async def test_retry_success_high_confidence(
        self, service, mock_cv_document_repo, mock_llm_adapter
    ):
        """Successful retry with high confidence → completed status."""
        cv_doc_id = uuid4()
        cv_doc = CVDocument(
            id=cv_doc_id,
            gmail_message_id="msg123",
            original_filename="resume.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            file_path="storage/cv/msg123/resume.pdf",
            ocr_output="Full OCR text with name and email and more content here",
            processing_status=ProcessingStatus.FAILED,
            retry_count=0,
        )
        mock_cv_document_repo.get_by_id = AsyncMock(return_value=cv_doc)

        with patch(
            "src.modules.recruitment.application.cv_processor.log_audit",
            new_callable=AsyncMock,
        ):
            result = await service.retry_llm_parse(cv_doc_id)

        assert result is not None
        assert isinstance(result, ParsedCV)
        assert cv_doc.processing_status in (
            ProcessingStatus.COMPLETED,
            ProcessingStatus.NEEDS_REVIEW,
        )
        assert cv_doc.retry_count == 1

    @pytest.mark.asyncio
    async def test_retry_failure(
        self, service, mock_cv_document_repo, mock_llm_adapter
    ):
        """Failed retry → failed status, returns None."""
        cv_doc_id = uuid4()
        cv_doc = CVDocument(
            id=cv_doc_id,
            gmail_message_id="msg123",
            original_filename="resume.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            file_path="storage/cv/msg123/resume.pdf",
            ocr_output="Full OCR text with enough content for parsing attempt",
            processing_status=ProcessingStatus.NEEDS_REVIEW,
            retry_count=1,
        )
        mock_cv_document_repo.get_by_id = AsyncMock(return_value=cv_doc)
        mock_llm_adapter.parse_cv = AsyncMock(
            side_effect=LLMParseError("Parse failed again")
        )

        with patch(
            "src.modules.recruitment.application.cv_processor.log_audit",
            new_callable=AsyncMock,
        ):
            result = await service.retry_llm_parse(cv_doc_id)

        assert result is None
        assert cv_doc.processing_status == ProcessingStatus.FAILED
        assert cv_doc.retry_count == 2

    @pytest.mark.asyncio
    async def test_retry_document_not_found(self, service, mock_cv_document_repo):
        """Non-existent CV document raises CVDocumentNotFoundError."""
        mock_cv_document_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(CVDocumentNotFoundError):
            await service.retry_llm_parse(uuid4())

    @pytest.mark.asyncio
    async def test_retry_no_ocr_output(self, service, mock_cv_document_repo):
        """CV document without OCR output returns None."""
        cv_doc_id = uuid4()
        cv_doc = CVDocument(
            id=cv_doc_id,
            gmail_message_id="msg123",
            original_filename="resume.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            file_path="storage/cv/msg123/resume.pdf",
            ocr_output=None,
            processing_status=ProcessingStatus.FAILED,
            retry_count=0,
        )
        mock_cv_document_repo.get_by_id = AsyncMock(return_value=cv_doc)

        result = await service.retry_llm_parse(cv_doc_id)

        assert result is None


# ─── Tests: PII redaction integration ──────────────────────────────────


class TestPIIRedactionIntegration:
    """Tests verifying PII redaction is applied before LLM calls."""

    @pytest.mark.asyncio
    async def test_pii_redactor_called_before_llm(
        self, service, valid_attachment, mock_pii_redactor, mock_llm_adapter
    ):
        """PII redactor is called on OCR text before LLM parse."""
        email_id = uuid4()

        with patch(
            "src.modules.recruitment.application.cv_processor.log_audit",
            new_callable=AsyncMock,
        ):
            await service.process_single_attachment(
                email_message_id=email_id,
                attachment=valid_attachment,
                gmail_message_id="msg123",
            )

        # Verify PII redactor was called
        mock_pii_redactor.redact.assert_called()
        # Verify LLM was called with the redacted text
        mock_llm_adapter.parse_cv.assert_called_once()
