"""Unit tests for AuditLogger."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.modules.gmail.infrastructure.audit_logger import AuditLogger
from src.modules.gmail.infrastructure.config import GmailSettings


@pytest.fixture
def session() -> AsyncMock:
    """Create a mocked AsyncSession."""
    mock = AsyncMock()
    # session.add is synchronous on AsyncSession
    mock.add = MagicMock()
    return mock


@pytest.fixture
def settings() -> GmailSettings:
    """Create GmailSettings with defaults."""
    return GmailSettings()


@pytest.fixture
def audit_logger(session: AsyncMock, settings: GmailSettings) -> AuditLogger:
    """Create an AuditLogger with mocked session."""
    return AuditLogger(session=session, settings=settings)


class TestLogOperation:
    """Tests for AuditLogger.log_operation."""

    @pytest.mark.asyncio
    async def test_logs_basic_operation(
        self, audit_logger: AuditLogger, session: AsyncMock
    ) -> None:
        """Logs a basic operation with required fields."""
        user_id = uuid4()

        await audit_logger.log_operation(
            operation_type="fetch",
            user_id=user_id,
            message_count=10,
            success=True,
        )

        session.add.assert_called_once()
        session.flush.assert_called_once()

        audit_entry = session.add.call_args[0][0]
        assert audit_entry.user_id == user_id
        assert audit_entry.operation_type == "fetch"
        assert audit_entry.message_count == 10
        assert audit_entry.success is True
        assert audit_entry.metadata_ is None

    @pytest.mark.asyncio
    async def test_logs_operation_with_metadata(
        self, audit_logger: AuditLogger, session: AsyncMock
    ) -> None:
        """Logs an operation with additional metadata."""
        user_id = uuid4()
        metadata = {"label_name": "VroomHR/processed", "gmail_message_id": "abc123"}

        await audit_logger.log_operation(
            operation_type="label_modify",
            user_id=user_id,
            success=True,
            metadata=metadata,
        )

        audit_entry = session.add.call_args[0][0]
        assert audit_entry.metadata_ == metadata

    @pytest.mark.asyncio
    async def test_sanitizes_forbidden_metadata_keys(
        self, audit_logger: AuditLogger, session: AsyncMock
    ) -> None:
        """Strips body, snippet, and attachment data from metadata."""
        user_id = uuid4()
        metadata = {
            "gmail_message_id": "msg123",
            "body": "This is the email body - SHOULD BE STRIPPED",
            "body_html": "<p>HTML body - SHOULD BE STRIPPED</p>",
            "body_text": "Plain text body - SHOULD BE STRIPPED",
            "snippet": "Preview text - SHOULD BE STRIPPED",
            "preview": "Preview - SHOULD BE STRIPPED",
            "raw_payload": "raw data - SHOULD BE STRIPPED",
            "raw_payload_enc": "encrypted data - SHOULD BE STRIPPED",
            "attachment_data": b"binary - SHOULD BE STRIPPED",
            "attachment_binary": b"binary - SHOULD BE STRIPPED",
            "content": "content - SHOULD BE STRIPPED",
            "label_name": "VroomHR/processed",
        }

        await audit_logger.log_operation(
            operation_type="fetch",
            user_id=user_id,
            success=True,
            metadata=metadata,
        )

        audit_entry = session.add.call_args[0][0]
        assert audit_entry.metadata_ == {"gmail_message_id": "msg123", "label_name": "VroomHR/processed"}

    @pytest.mark.asyncio
    async def test_sanitizes_case_insensitive(
        self, audit_logger: AuditLogger, session: AsyncMock
    ) -> None:
        """Forbidden key matching is case-insensitive."""
        user_id = uuid4()
        metadata = {
            "Body": "should be stripped",
            "SNIPPET": "should be stripped",
            "safe_key": "kept",
        }

        await audit_logger.log_operation(
            operation_type="fetch",
            user_id=user_id,
            success=True,
            metadata=metadata,
        )

        audit_entry = session.add.call_args[0][0]
        assert audit_entry.metadata_ == {"safe_key": "kept"}

    @pytest.mark.asyncio
    async def test_handles_none_metadata(
        self, audit_logger: AuditLogger, session: AsyncMock
    ) -> None:
        """None metadata is passed through as None."""
        user_id = uuid4()

        await audit_logger.log_operation(
            operation_type="connect",
            user_id=user_id,
            success=True,
            metadata=None,
        )

        audit_entry = session.add.call_args[0][0]
        assert audit_entry.metadata_ is None

    @pytest.mark.asyncio
    async def test_defaults_message_count_to_zero(
        self, audit_logger: AuditLogger, session: AsyncMock
    ) -> None:
        """message_count defaults to 0 when not provided."""
        user_id = uuid4()

        await audit_logger.log_operation(
            operation_type="connect",
            user_id=user_id,
            success=True,
        )

        audit_entry = session.add.call_args[0][0]
        assert audit_entry.message_count == 0

    @pytest.mark.asyncio
    async def test_logs_failed_operation(
        self, audit_logger: AuditLogger, session: AsyncMock
    ) -> None:
        """Logs an operation with success=False."""
        user_id = uuid4()

        await audit_logger.log_operation(
            operation_type="fetch",
            user_id=user_id,
            message_count=0,
            success=False,
            metadata={"error": "Gmail API timeout"},
        )

        audit_entry = session.add.call_args[0][0]
        assert audit_entry.success is False
        assert audit_entry.metadata_ == {"error": "Gmail API timeout"}

    @pytest.mark.asyncio
    async def test_graceful_failure_on_db_error(
        self, audit_logger: AuditLogger, session: AsyncMock
    ) -> None:
        """Does not raise when database flush fails."""
        user_id = uuid4()
        session.flush.side_effect = Exception("DB connection lost")

        # Should NOT raise
        await audit_logger.log_operation(
            operation_type="fetch",
            user_id=user_id,
            success=True,
        )

    @pytest.mark.asyncio
    async def test_logs_error_on_db_failure(
        self, audit_logger: AuditLogger, session: AsyncMock
    ) -> None:
        """Logs error to application logger when DB fails."""
        user_id = uuid4()
        session.flush.side_effect = Exception("DB connection lost")

        with patch("src.modules.gmail.infrastructure.audit_logger.logger") as mock_logger:
            await audit_logger.log_operation(
                operation_type="fetch",
                user_id=user_id,
                success=True,
            )

            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args[0]
            assert "fetch" in call_args[0] or "fetch" in str(call_args)


class TestLogSend:
    """Tests for AuditLogger.log_send."""

    @pytest.mark.asyncio
    async def test_logs_send_operation(
        self, audit_logger: AuditLogger, session: AsyncMock
    ) -> None:
        """Logs a send operation with recipients and subject."""
        user_id = uuid4()

        await audit_logger.log_send(
            user_id=user_id,
            recipient_emails=["hr@example.com"],
            subject="Interview Invitation",
        )

        session.add.assert_called_once()
        session.flush.assert_called_once()

        audit_entry = session.add.call_args[0][0]
        assert audit_entry.user_id == user_id
        assert audit_entry.operation_type == "send"
        assert audit_entry.message_count == 1
        assert audit_entry.success is True
        assert audit_entry.metadata_["recipient_emails"] == ["hr@example.com"]
        assert audit_entry.metadata_["subject"] == "Interview Invitation"
        assert "sent_at" in audit_entry.metadata_

    @pytest.mark.asyncio
    async def test_truncates_subject_to_max_length(
        self, audit_logger: AuditLogger, session: AsyncMock
    ) -> None:
        """Subject is truncated to audit_subject_max_length (default 100)."""
        user_id = uuid4()
        long_subject = "A" * 200

        await audit_logger.log_send(
            user_id=user_id,
            recipient_emails=["test@example.com"],
            subject=long_subject,
        )

        audit_entry = session.add.call_args[0][0]
        assert len(audit_entry.metadata_["subject"]) == 100

    @pytest.mark.asyncio
    async def test_truncates_recipients_to_50(
        self, audit_logger: AuditLogger, session: AsyncMock
    ) -> None:
        """Recipients list is truncated to 50 entries."""
        user_id = uuid4()
        many_recipients = [f"user{i}@example.com" for i in range(75)]

        await audit_logger.log_send(
            user_id=user_id,
            recipient_emails=many_recipients,
            subject="Bulk email",
        )

        audit_entry = session.add.call_args[0][0]
        assert len(audit_entry.metadata_["recipient_emails"]) == 50
        assert audit_entry.metadata_["recipient_count"] == 75
        assert audit_entry.metadata_["recipients_truncated"] is True

    @pytest.mark.asyncio
    async def test_no_truncation_indicator_when_under_50(
        self, audit_logger: AuditLogger, session: AsyncMock
    ) -> None:
        """No truncation metadata when recipients are 50 or fewer."""
        user_id = uuid4()

        await audit_logger.log_send(
            user_id=user_id,
            recipient_emails=["a@b.com", "c@d.com"],
            subject="Test",
        )

        audit_entry = session.add.call_args[0][0]
        assert "recipient_count" not in audit_entry.metadata_
        assert "recipients_truncated" not in audit_entry.metadata_

    @pytest.mark.asyncio
    async def test_includes_template_name_when_provided(
        self, audit_logger: AuditLogger, session: AsyncMock
    ) -> None:
        """Includes template_name in metadata when provided."""
        user_id = uuid4()

        await audit_logger.log_send(
            user_id=user_id,
            recipient_emails=["test@example.com"],
            subject="Welcome",
            template_name="onboarding_welcome",
        )

        audit_entry = session.add.call_args[0][0]
        assert audit_entry.metadata_["template_name"] == "onboarding_welcome"

    @pytest.mark.asyncio
    async def test_omits_template_name_when_none(
        self, audit_logger: AuditLogger, session: AsyncMock
    ) -> None:
        """Does not include template_name key when it is None."""
        user_id = uuid4()

        await audit_logger.log_send(
            user_id=user_id,
            recipient_emails=["test@example.com"],
            subject="Manual email",
            template_name=None,
        )

        audit_entry = session.add.call_args[0][0]
        assert "template_name" not in audit_entry.metadata_

    @pytest.mark.asyncio
    async def test_handles_empty_subject(
        self, audit_logger: AuditLogger, session: AsyncMock
    ) -> None:
        """Handles empty string subject gracefully."""
        user_id = uuid4()

        await audit_logger.log_send(
            user_id=user_id,
            recipient_emails=["test@example.com"],
            subject="",
        )

        audit_entry = session.add.call_args[0][0]
        assert audit_entry.metadata_["subject"] == ""

    @pytest.mark.asyncio
    async def test_graceful_failure_on_db_error(
        self, audit_logger: AuditLogger, session: AsyncMock
    ) -> None:
        """Does not raise when database flush fails."""
        user_id = uuid4()
        session.flush.side_effect = Exception("DB connection lost")

        # Should NOT raise
        await audit_logger.log_send(
            user_id=user_id,
            recipient_emails=["test@example.com"],
            subject="Test",
        )

    @pytest.mark.asyncio
    async def test_logs_error_on_db_failure(
        self, audit_logger: AuditLogger, session: AsyncMock
    ) -> None:
        """Logs error to application logger when DB fails."""
        user_id = uuid4()
        session.flush.side_effect = Exception("DB connection lost")

        with patch("src.modules.gmail.infrastructure.audit_logger.logger") as mock_logger:
            await audit_logger.log_send(
                user_id=user_id,
                recipient_emails=["test@example.com"],
                subject="Test",
            )

            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args[0]
            assert "send" in call_args[0] or "send" in str(call_args)
