"""Unit tests for AttachmentService."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.modules.gmail.application.attachment_service import (
    AttachmentMetadata,
    AttachmentService,
)
from src.modules.gmail.domain.exceptions import GmailFetchError
from src.modules.gmail.infrastructure.config import GmailSettings


@pytest.fixture
def settings() -> GmailSettings:
    """Create GmailSettings with defaults."""
    return GmailSettings()


@pytest.fixture
def gmail_adapter() -> AsyncMock:
    """Create a mocked GmailAdapter."""
    adapter = AsyncMock()
    adapter.get_attachment = AsyncMock(return_value=b"fake_binary_data")
    return adapter


@pytest.fixture
def audit_logger() -> AsyncMock:
    """Create a mocked AuditLogger."""
    logger = AsyncMock()
    logger.log_operation = AsyncMock()
    return logger


@pytest.fixture
def attachment_service(
    gmail_adapter: AsyncMock,
    settings: GmailSettings,
    audit_logger: AsyncMock,
) -> AttachmentService:
    """Create an AttachmentService with mocked dependencies."""
    return AttachmentService(
        gmail_adapter=gmail_adapter,
        settings=settings,
        audit_logger=audit_logger,
    )


class TestValidateAttachment:
    """Tests for AttachmentService.validate_attachment."""

    def test_accepts_pdf(self, attachment_service: AttachmentService) -> None:
        """PDF MIME type within size limit is valid."""
        assert attachment_service.validate_attachment("application/pdf", 1024) is True

    def test_accepts_docx(self, attachment_service: AttachmentService) -> None:
        """DOCX MIME type within size limit is valid."""
        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert attachment_service.validate_attachment(mime, 5 * 1024 * 1024) is True

    def test_accepts_jpeg(self, attachment_service: AttachmentService) -> None:
        """JPEG MIME type within size limit is valid."""
        assert attachment_service.validate_attachment("image/jpeg", 2048) is True

    def test_accepts_png(self, attachment_service: AttachmentService) -> None:
        """PNG MIME type within size limit is valid."""
        assert attachment_service.validate_attachment("image/png", 500_000) is True

    def test_accepts_exactly_10mb(self, attachment_service: AttachmentService) -> None:
        """Attachment exactly at 10MB limit is valid."""
        assert attachment_service.validate_attachment("application/pdf", 10 * 1024 * 1024) is True

    def test_rejects_disallowed_mime_type(self, attachment_service: AttachmentService) -> None:
        """Disallowed MIME types are rejected."""
        assert attachment_service.validate_attachment("application/zip", 1024) is False
        assert attachment_service.validate_attachment("text/plain", 1024) is False
        assert attachment_service.validate_attachment("application/exe", 1024) is False

    def test_rejects_size_exceeding_10mb(self, attachment_service: AttachmentService) -> None:
        """Attachments exceeding 10MB are rejected."""
        over_limit = 10 * 1024 * 1024 + 1
        assert attachment_service.validate_attachment("application/pdf", over_limit) is False

    def test_rejects_invalid_mime_and_over_size(self, attachment_service: AttachmentService) -> None:
        """Attachment with both invalid MIME and over-size is rejected."""
        over_limit = 10 * 1024 * 1024 + 1
        assert attachment_service.validate_attachment("application/zip", over_limit) is False

    def test_accepts_zero_size(self, attachment_service: AttachmentService) -> None:
        """Zero-size attachment with valid MIME type is valid."""
        assert attachment_service.validate_attachment("application/pdf", 0) is True


class TestFetchAttachments:
    """Tests for AttachmentService.fetch_attachments."""

    @pytest.mark.asyncio
    async def test_fetches_valid_attachments(
        self,
        attachment_service: AttachmentService,
        gmail_adapter: AsyncMock,
    ) -> None:
        """Successfully fetches attachments with valid MIME type and size."""
        user_id = uuid4()
        attachments = [
            AttachmentMetadata(
                attachment_id="att_1",
                filename="resume.pdf",
                mime_type="application/pdf",
                size_bytes=1024,
            ),
            AttachmentMetadata(
                attachment_id="att_2",
                filename="photo.png",
                mime_type="image/png",
                size_bytes=2048,
            ),
        ]

        result = await attachment_service.fetch_attachments(
            user_id=user_id,
            message_id="msg_123",
            access_token="token_abc",
            attachments=attachments,
        )

        assert result.fetched_count == 2
        assert result.skipped_count == 0
        assert result.total_count == 2
        assert len(result.fetched) == 2
        assert result.fetched[0].filename == "resume.pdf"
        assert result.fetched[1].filename == "photo.png"

    @pytest.mark.asyncio
    async def test_skips_invalid_mime_type(
        self,
        attachment_service: AttachmentService,
        gmail_adapter: AsyncMock,
    ) -> None:
        """Skips attachments with disallowed MIME types."""
        user_id = uuid4()
        attachments = [
            AttachmentMetadata(
                attachment_id="att_1",
                filename="archive.zip",
                mime_type="application/zip",
                size_bytes=1024,
            ),
            AttachmentMetadata(
                attachment_id="att_2",
                filename="resume.pdf",
                mime_type="application/pdf",
                size_bytes=1024,
            ),
        ]

        result = await attachment_service.fetch_attachments(
            user_id=user_id,
            message_id="msg_123",
            access_token="token_abc",
            attachments=attachments,
        )

        assert result.fetched_count == 1
        assert result.skipped_count == 1
        assert result.total_count == 2
        assert result.fetched[0].filename == "resume.pdf"
        # Should not have called get_attachment for the zip file
        gmail_adapter.get_attachment.assert_called_once_with(
            access_token="token_abc",
            message_id="msg_123",
            attachment_id="att_2",
        )

    @pytest.mark.asyncio
    async def test_skips_oversized_attachment(
        self,
        attachment_service: AttachmentService,
        gmail_adapter: AsyncMock,
    ) -> None:
        """Skips attachments exceeding 10MB size limit."""
        user_id = uuid4()
        attachments = [
            AttachmentMetadata(
                attachment_id="att_1",
                filename="huge.pdf",
                mime_type="application/pdf",
                size_bytes=10 * 1024 * 1024 + 1,
            ),
        ]

        result = await attachment_service.fetch_attachments(
            user_id=user_id,
            message_id="msg_123",
            access_token="token_abc",
            attachments=attachments,
        )

        assert result.fetched_count == 0
        assert result.skipped_count == 1
        assert result.total_count == 1
        gmail_adapter.get_attachment.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_on_fetch_failure(
        self,
        attachment_service: AttachmentService,
        gmail_adapter: AsyncMock,
    ) -> None:
        """Skips attachment and continues when fetch fails."""
        user_id = uuid4()
        attachments = [
            AttachmentMetadata(
                attachment_id="att_1",
                filename="resume.pdf",
                mime_type="application/pdf",
                size_bytes=1024,
            ),
            AttachmentMetadata(
                attachment_id="att_2",
                filename="photo.jpeg",
                mime_type="image/jpeg",
                size_bytes=2048,
            ),
        ]

        # First fetch fails, second succeeds
        gmail_adapter.get_attachment.side_effect = [
            GmailFetchError("API error"),
            b"photo_data",
        ]

        result = await attachment_service.fetch_attachments(
            user_id=user_id,
            message_id="msg_123",
            access_token="token_abc",
            attachments=attachments,
        )

        assert result.fetched_count == 1
        assert result.skipped_count == 1
        assert result.total_count == 2
        assert result.fetched[0].filename == "photo.jpeg"

    @pytest.mark.asyncio
    async def test_limits_to_20_attachments(
        self,
        attachment_service: AttachmentService,
        gmail_adapter: AsyncMock,
    ) -> None:
        """Processes at most 20 attachments per email."""
        user_id = uuid4()
        attachments = [
            AttachmentMetadata(
                attachment_id=f"att_{i}",
                filename=f"file_{i}.pdf",
                mime_type="application/pdf",
                size_bytes=1024,
            )
            for i in range(25)
        ]

        result = await attachment_service.fetch_attachments(
            user_id=user_id,
            message_id="msg_123",
            access_token="token_abc",
            attachments=attachments,
        )

        assert result.total_count == 20
        assert result.fetched_count == 20
        assert result.skipped_count == 0
        assert gmail_adapter.get_attachment.call_count == 20

    @pytest.mark.asyncio
    async def test_handles_empty_attachment_list(
        self,
        attachment_service: AttachmentService,
        gmail_adapter: AsyncMock,
    ) -> None:
        """Handles empty attachment list gracefully."""
        user_id = uuid4()

        result = await attachment_service.fetch_attachments(
            user_id=user_id,
            message_id="msg_123",
            access_token="token_abc",
            attachments=[],
        )

        assert result.fetched_count == 0
        assert result.skipped_count == 0
        assert result.total_count == 0
        gmail_adapter.get_attachment.assert_not_called()

    @pytest.mark.asyncio
    async def test_counts_sum_equals_total(
        self,
        attachment_service: AttachmentService,
        gmail_adapter: AsyncMock,
    ) -> None:
        """fetched_count + skipped_count always equals total_count."""
        user_id = uuid4()
        attachments = [
            AttachmentMetadata(
                attachment_id="att_1",
                filename="valid.pdf",
                mime_type="application/pdf",
                size_bytes=1024,
            ),
            AttachmentMetadata(
                attachment_id="att_2",
                filename="invalid.exe",
                mime_type="application/exe",
                size_bytes=1024,
            ),
            AttachmentMetadata(
                attachment_id="att_3",
                filename="fail.png",
                mime_type="image/png",
                size_bytes=2048,
            ),
        ]

        # Third attachment fetch fails
        gmail_adapter.get_attachment.side_effect = [
            b"pdf_data",
            GmailFetchError("API error"),
        ]

        result = await attachment_service.fetch_attachments(
            user_id=user_id,
            message_id="msg_123",
            access_token="token_abc",
            attachments=attachments,
        )

        assert result.fetched_count + result.skipped_count == result.total_count

    @pytest.mark.asyncio
    async def test_logs_audit_on_completion(
        self,
        attachment_service: AttachmentService,
        audit_logger: AsyncMock,
    ) -> None:
        """Logs audit entry after processing attachments."""
        user_id = uuid4()
        attachments = [
            AttachmentMetadata(
                attachment_id="att_1",
                filename="resume.pdf",
                mime_type="application/pdf",
                size_bytes=1024,
            ),
        ]

        await attachment_service.fetch_attachments(
            user_id=user_id,
            message_id="msg_123",
            access_token="token_abc",
            attachments=attachments,
        )

        audit_logger.log_operation.assert_called_once()
        call_kwargs = audit_logger.log_operation.call_args[1]
        assert call_kwargs["operation_type"] == "attachment_fetch"
        assert call_kwargs["user_id"] == user_id
        assert call_kwargs["message_count"] == 1
        assert call_kwargs["success"] is True
        assert call_kwargs["metadata"]["message_id"] == "msg_123"
        assert call_kwargs["metadata"]["fetched_count"] == 1
        assert call_kwargs["metadata"]["skipped_count"] == 0

    @pytest.mark.asyncio
    async def test_audit_logs_failure_when_skips_exist(
        self,
        attachment_service: AttachmentService,
        gmail_adapter: AsyncMock,
        audit_logger: AsyncMock,
    ) -> None:
        """Audit log success=False when any attachments are skipped."""
        user_id = uuid4()
        attachments = [
            AttachmentMetadata(
                attachment_id="att_1",
                filename="bad.zip",
                mime_type="application/zip",
                size_bytes=1024,
            ),
        ]

        await attachment_service.fetch_attachments(
            user_id=user_id,
            message_id="msg_123",
            access_token="token_abc",
            attachments=attachments,
        )

        call_kwargs = audit_logger.log_operation.call_args[1]
        assert call_kwargs["success"] is False
        assert call_kwargs["metadata"]["skipped_count"] == 1
