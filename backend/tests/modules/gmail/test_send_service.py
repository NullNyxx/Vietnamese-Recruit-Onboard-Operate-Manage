"""Unit tests for SendService."""

import email
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest

from src.modules.gmail.application.send_service import (
    AttachmentData,
    SendEmailParams,
    SendService,
    SentEmailResponse,
)
from src.modules.gmail.domain.exceptions import (
    GmailNotConnectedException,
    GmailSendFailedException,
)
from src.modules.gmail.infrastructure.config import GmailSettings
from src.modules.gmail.infrastructure.gmail_adapter import SentMessageInfo
from src.modules.identity.infrastructure.crypto_utils import CryptoUtils


@pytest.fixture
def settings() -> GmailSettings:
    """Create GmailSettings with defaults."""
    return GmailSettings()


@pytest.fixture
def gmail_adapter() -> AsyncMock:
    """Create a mocked GmailAdapter."""
    return AsyncMock()


@pytest.fixture
def email_repo() -> AsyncMock:
    """Create a mocked EmailRepository."""
    return AsyncMock()


@pytest.fixture
def oauth_grant_repo() -> AsyncMock:
    """Create a mocked OAuthGrantRepository."""
    return AsyncMock()


@pytest.fixture
def crypto() -> MagicMock:
    """Create a mocked CryptoUtils."""
    mock = MagicMock(spec=CryptoUtils)
    mock.encrypt.side_effect = lambda x: f"encrypted_{x}"
    mock.decrypt.side_effect = lambda x: x.replace("encrypted_", "")
    return mock


@pytest.fixture
def audit_logger() -> AsyncMock:
    """Create a mocked AuditLogger."""
    return AsyncMock()


@pytest.fixture
def send_service(
    settings: GmailSettings,
    gmail_adapter: AsyncMock,
    email_repo: AsyncMock,
    oauth_grant_repo: AsyncMock,
    crypto: MagicMock,
    audit_logger: AsyncMock,
) -> SendService:
    """Create a SendService with mocked dependencies."""
    return SendService(
        gmail_adapter=gmail_adapter,
        email_repo=email_repo,
        oauth_grant_repo=oauth_grant_repo,
        crypto=crypto,
        audit_logger=audit_logger,
        settings=settings,
        client_id="test-client-id",
        client_secret="test-client-secret",
    )


def _make_grant(
    *,
    is_valid: bool = True,
    token_expires_at: datetime | None = None,
    access_token_enc: str = "encrypted_test_access_token",
    refresh_token_enc: str = "encrypted_test_refresh_token",
    scopes: list[str] | None = None,
) -> MagicMock:
    """Create a mock OAuth grant with configurable fields."""
    grant = MagicMock()
    grant.is_valid = is_valid
    grant.token_expires_at = token_expires_at or (datetime.now(UTC) + timedelta(hours=1))
    grant.access_token_enc = access_token_enc
    grant.refresh_token_enc = refresh_token_enc
    grant.scopes = scopes or [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.send",
    ]
    return grant


def _make_send_params(
    *,
    to: list[str] | None = None,
    subject: str = "Test Subject",
    body_html: str | None = "<p>Hello</p>",
    body_text: str | None = "Hello",
    cc: list[str] | None = None,
    reply_to_message_id: str | None = None,
    attachments: list[AttachmentData] | None = None,
) -> SendEmailParams:
    """Create SendEmailParams with sensible defaults."""
    return SendEmailParams(
        to=to if to is not None else ["recipient@example.com"],
        subject=subject,
        body_html=body_html,
        body_text=body_text,
        cc=cc if cc is not None else [],
        reply_to_message_id=reply_to_message_id,
        attachments=attachments if attachments is not None else [],
    )


class TestValidateParams:
    """Tests for SendService._validate_params."""

    def test_valid_params_pass(self, send_service: SendService) -> None:
        """Valid parameters pass validation without error."""
        params = _make_send_params()
        send_service._validate_params(params)  # Should not raise

    def test_empty_to_raises(self, send_service: SendService) -> None:
        """Raises ValueError when to list is empty."""
        params = _make_send_params(to=[])
        with pytest.raises(ValueError, match="At least one recipient"):
            send_service._validate_params(params)

    def test_too_many_to_raises(self, send_service: SendService) -> None:
        """Raises ValueError when to list exceeds 50."""
        params = _make_send_params(to=[f"user{i}@example.com" for i in range(51)])
        with pytest.raises(ValueError, match="Maximum 50 recipients.*'to'"):
            send_service._validate_params(params)

    def test_too_many_cc_raises(self, send_service: SendService) -> None:
        """Raises ValueError when cc list exceeds 50."""
        params = _make_send_params(cc=[f"cc{i}@example.com" for i in range(51)])
        with pytest.raises(ValueError, match="Maximum 50 recipients.*'cc'"):
            send_service._validate_params(params)

    def test_subject_too_long_raises(self, send_service: SendService) -> None:
        """Raises ValueError when subject exceeds 500 characters."""
        params = _make_send_params(subject="x" * 501)
        with pytest.raises(ValueError, match="Subject must not exceed 500"):
            send_service._validate_params(params)

    def test_no_body_raises(self, send_service: SendService) -> None:
        """Raises ValueError when neither body_html nor body_text provided."""
        params = _make_send_params(body_html=None, body_text=None)
        with pytest.raises(ValueError, match="At least one of body_html or body_text"):
            send_service._validate_params(params)

    def test_too_many_attachments_raises(self, send_service: SendService) -> None:
        """Raises ValueError when more than 10 attachments."""
        attachments = [
            AttachmentData(filename=f"file{i}.pdf", content=b"data", mime_type="application/pdf")
            for i in range(11)
        ]
        params = _make_send_params(attachments=attachments)
        with pytest.raises(ValueError, match="Maximum 10 attachments"):
            send_service._validate_params(params)

    def test_attachment_too_large_raises(self, send_service: SendService) -> None:
        """Raises ValueError when an attachment exceeds 10MB."""
        large_content = b"x" * (10 * 1024 * 1024 + 1)
        attachments = [
            AttachmentData(filename="big.pdf", content=large_content, mime_type="application/pdf")
        ]
        params = _make_send_params(attachments=attachments)
        with pytest.raises(ValueError, match="exceeds maximum size"):
            send_service._validate_params(params)

    def test_exactly_50_to_passes(self, send_service: SendService) -> None:
        """Exactly 50 recipients in to passes validation."""
        params = _make_send_params(to=[f"user{i}@example.com" for i in range(50)])
        send_service._validate_params(params)  # Should not raise

    def test_exactly_10_attachments_passes(self, send_service: SendService) -> None:
        """Exactly 10 attachments passes validation."""
        attachments = [
            AttachmentData(filename=f"file{i}.pdf", content=b"data", mime_type="application/pdf")
            for i in range(10)
        ]
        params = _make_send_params(attachments=attachments)
        send_service._validate_params(params)  # Should not raise

    def test_subject_exactly_500_passes(self, send_service: SendService) -> None:
        """Subject of exactly 500 characters passes validation."""
        params = _make_send_params(subject="x" * 500)
        send_service._validate_params(params)  # Should not raise


class TestBuildMimeMessage:
    """Tests for SendService._build_mime_message."""

    def test_basic_html_and_text(self, send_service: SendService) -> None:
        """Builds MIME message with both HTML and text body."""
        params = _make_send_params(
            to=["alice@example.com"],
            subject="Hello",
            body_html="<p>Hi</p>",
            body_text="Hi",
        )
        mime_bytes = send_service._build_mime_message(params)
        msg = email.message_from_bytes(mime_bytes)

        assert msg["To"] == "alice@example.com"
        assert msg["Subject"] == "Hello"
        assert msg.get_content_type() == "multipart/alternative"

        parts = list(msg.walk())
        content_types = [p.get_content_type() for p in parts]
        assert "text/plain" in content_types
        assert "text/html" in content_types

    def test_html_only(self, send_service: SendService) -> None:
        """Builds MIME message with HTML body only."""
        params = _make_send_params(body_html="<p>Hi</p>", body_text=None)
        mime_bytes = send_service._build_mime_message(params)
        msg = email.message_from_bytes(mime_bytes)

        parts = list(msg.walk())
        content_types = [p.get_content_type() for p in parts]
        assert "text/html" in content_types

    def test_text_only(self, send_service: SendService) -> None:
        """Builds MIME message with plain text body only."""
        params = _make_send_params(body_html=None, body_text="Hello plain")
        mime_bytes = send_service._build_mime_message(params)
        msg = email.message_from_bytes(mime_bytes)

        parts = list(msg.walk())
        content_types = [p.get_content_type() for p in parts]
        assert "text/plain" in content_types

    def test_multiple_recipients(self, send_service: SendService) -> None:
        """Sets To header with multiple recipients."""
        params = _make_send_params(to=["a@x.com", "b@x.com", "c@x.com"])
        mime_bytes = send_service._build_mime_message(params)
        msg = email.message_from_bytes(mime_bytes)

        assert "a@x.com" in msg["To"]
        assert "b@x.com" in msg["To"]
        assert "c@x.com" in msg["To"]

    def test_cc_header(self, send_service: SendService) -> None:
        """Sets Cc header when cc recipients provided."""
        params = _make_send_params(cc=["cc1@x.com", "cc2@x.com"])
        mime_bytes = send_service._build_mime_message(params)
        msg = email.message_from_bytes(mime_bytes)

        assert msg["Cc"] is not None
        assert "cc1@x.com" in msg["Cc"]
        assert "cc2@x.com" in msg["Cc"]

    def test_no_cc_header_when_empty(self, send_service: SendService) -> None:
        """Does not set Cc header when cc list is empty."""
        params = _make_send_params(cc=[])
        mime_bytes = send_service._build_mime_message(params)
        msg = email.message_from_bytes(mime_bytes)

        assert msg["Cc"] is None

    def test_reply_to_headers(self, send_service: SendService) -> None:
        """Sets In-Reply-To and References headers for replies."""
        params = _make_send_params(reply_to_message_id="<original-msg-id@gmail.com>")
        mime_bytes = send_service._build_mime_message(params)
        msg = email.message_from_bytes(mime_bytes)

        assert msg["In-Reply-To"] == "<original-msg-id@gmail.com>"
        assert msg["References"] == "<original-msg-id@gmail.com>"

    def test_no_reply_headers_when_not_reply(self, send_service: SendService) -> None:
        """Does not set In-Reply-To/References when not a reply."""
        params = _make_send_params(reply_to_message_id=None)
        mime_bytes = send_service._build_mime_message(params)
        msg = email.message_from_bytes(mime_bytes)

        assert msg["In-Reply-To"] is None
        assert msg["References"] is None

    def test_with_attachments(self, send_service: SendService) -> None:
        """Builds multipart/mixed message with attachments."""
        attachments = [
            AttachmentData(
                filename="doc.pdf",
                content=b"PDF content here",
                mime_type="application/pdf",
            )
        ]
        params = _make_send_params(attachments=attachments)
        mime_bytes = send_service._build_mime_message(params)
        msg = email.message_from_bytes(mime_bytes)

        assert msg.get_content_type() == "multipart/mixed"

        parts = list(msg.walk())
        content_types = [p.get_content_type() for p in parts]
        assert "application/pdf" in content_types

    def test_attachment_filename_in_disposition(self, send_service: SendService) -> None:
        """Attachment has correct Content-Disposition with filename."""
        attachments = [
            AttachmentData(
                filename="resume.pdf",
                content=b"data",
                mime_type="application/pdf",
            )
        ]
        params = _make_send_params(attachments=attachments)
        mime_bytes = send_service._build_mime_message(params)
        msg = email.message_from_bytes(mime_bytes)

        for part in msg.walk():
            if part.get_content_type() == "application/pdf":
                disposition = part.get("Content-Disposition", "")
                assert "resume.pdf" in disposition


class TestSendEmail:
    """Tests for SendService.send_email."""

    async def test_successful_send(
        self,
        send_service: SendService,
        oauth_grant_repo: AsyncMock,
        gmail_adapter: AsyncMock,
        email_repo: AsyncMock,
        audit_logger: AsyncMock,
    ) -> None:
        """Successfully sends email and returns response."""
        user_id = uuid4()
        grant = _make_grant()
        oauth_grant_repo.get_by_user_id.return_value = grant
        gmail_adapter.send_message.return_value = SentMessageInfo(
            message_id="sent_msg_123", thread_id="thread_456"
        )

        params = _make_send_params()
        result = await send_service.send_email(user_id, params)

        assert isinstance(result, SentEmailResponse)
        assert result.message_id == "sent_msg_123"
        assert result.thread_id == "thread_456"
        gmail_adapter.send_message.assert_called_once()

    async def test_stores_sent_metadata(
        self,
        send_service: SendService,
        oauth_grant_repo: AsyncMock,
        gmail_adapter: AsyncMock,
        email_repo: AsyncMock,
    ) -> None:
        """Stores sent message metadata in EmailRepository."""
        user_id = uuid4()
        grant = _make_grant()
        oauth_grant_repo.get_by_user_id.return_value = grant
        gmail_adapter.send_message.return_value = SentMessageInfo(
            message_id="sent_msg_123", thread_id="thread_456"
        )

        params = _make_send_params(to=["bob@example.com"])
        await send_service.send_email(user_id, params)

        email_repo.batch_upsert.assert_called_once()
        stored_messages = email_repo.batch_upsert.call_args[0][0]
        assert len(stored_messages) == 1
        assert stored_messages[0].gmail_message_id == "sent_msg_123"
        assert stored_messages[0].gmail_thread_id == "thread_456"
        assert stored_messages[0].recipient_emails == ["bob@example.com"]

    async def test_logs_audit_on_send(
        self,
        send_service: SendService,
        oauth_grant_repo: AsyncMock,
        gmail_adapter: AsyncMock,
        audit_logger: AsyncMock,
    ) -> None:
        """Logs send operation to audit logger."""
        user_id = uuid4()
        grant = _make_grant()
        oauth_grant_repo.get_by_user_id.return_value = grant
        gmail_adapter.send_message.return_value = SentMessageInfo(
            message_id="msg_1", thread_id="thread_1"
        )

        params = _make_send_params(
            to=["alice@example.com"],
            cc=["bob@example.com"],
            subject="Test Subject",
        )
        await send_service.send_email(user_id, params)

        audit_logger.log_send.assert_called_once_with(
            user_id=user_id,
            recipient_emails=["alice@example.com", "bob@example.com"],
            subject="Test Subject",
        )

    async def test_raises_not_connected_when_no_grant(
        self,
        send_service: SendService,
        oauth_grant_repo: AsyncMock,
    ) -> None:
        """Raises GmailNotConnectedException when no OAuth grant exists."""
        user_id = uuid4()
        oauth_grant_repo.get_by_user_id.return_value = None

        params = _make_send_params()
        with pytest.raises(GmailNotConnectedException):
            await send_service.send_email(user_id, params)

    async def test_raises_not_connected_when_grant_invalid(
        self,
        send_service: SendService,
        oauth_grant_repo: AsyncMock,
    ) -> None:
        """Raises GmailNotConnectedException when grant is invalid."""
        user_id = uuid4()
        grant = _make_grant(is_valid=False)
        oauth_grant_repo.get_by_user_id.return_value = grant

        params = _make_send_params()
        with pytest.raises(GmailNotConnectedException):
            await send_service.send_email(user_id, params)

    async def test_refreshes_token_on_401(
        self,
        send_service: SendService,
        oauth_grant_repo: AsyncMock,
        gmail_adapter: AsyncMock,
        crypto: MagicMock,
    ) -> None:
        """Refreshes token and retries on 401 from send_message."""
        user_id = uuid4()
        grant = _make_grant()
        oauth_grant_repo.get_by_user_id.return_value = grant

        # First call raises 401, second succeeds
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        http_error = httpx.HTTPStatusError(
            "401", request=MagicMock(), response=mock_response
        )
        gmail_adapter.send_message.side_effect = [
            http_error,
            SentMessageInfo(message_id="msg_retry", thread_id="thread_retry"),
        ]
        gmail_adapter.refresh_access_token.return_value = (
            "new_access_token",
            datetime.now(UTC) + timedelta(hours=1),
        )

        params = _make_send_params()
        result = await send_service.send_email(user_id, params)

        assert result.message_id == "msg_retry"
        assert gmail_adapter.send_message.call_count == 2
        gmail_adapter.refresh_access_token.assert_called_once()

    async def test_raises_send_failed_when_refresh_fails(
        self,
        send_service: SendService,
        oauth_grant_repo: AsyncMock,
        gmail_adapter: AsyncMock,
    ) -> None:
        """Raises GmailSendFailedException when token refresh fails on 401."""
        user_id = uuid4()
        grant = _make_grant()
        oauth_grant_repo.get_by_user_id.return_value = grant

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        http_error = httpx.HTTPStatusError(
            "401", request=MagicMock(), response=mock_response
        )
        gmail_adapter.send_message.side_effect = http_error
        gmail_adapter.refresh_access_token.side_effect = Exception("Refresh failed")

        params = _make_send_params()
        with pytest.raises(GmailSendFailedException):
            await send_service.send_email(user_id, params)

    async def test_raises_validation_error_for_invalid_params(
        self,
        send_service: SendService,
        oauth_grant_repo: AsyncMock,
    ) -> None:
        """Raises ValueError for invalid parameters before calling adapter."""
        user_id = uuid4()
        grant = _make_grant()
        oauth_grant_repo.get_by_user_id.return_value = grant

        params = _make_send_params(to=[])
        with pytest.raises(ValueError):
            await send_service.send_email(user_id, params)

    async def test_send_succeeds_even_if_metadata_storage_fails(
        self,
        send_service: SendService,
        oauth_grant_repo: AsyncMock,
        gmail_adapter: AsyncMock,
        email_repo: AsyncMock,
    ) -> None:
        """Send succeeds even if storing metadata fails."""
        user_id = uuid4()
        grant = _make_grant()
        oauth_grant_repo.get_by_user_id.return_value = grant
        gmail_adapter.send_message.return_value = SentMessageInfo(
            message_id="msg_1", thread_id="thread_1"
        )
        email_repo.batch_upsert.side_effect = Exception("DB error")

        params = _make_send_params()
        result = await send_service.send_email(user_id, params)

        # Send still succeeds
        assert result.message_id == "msg_1"

    async def test_refreshes_token_when_expired(
        self,
        send_service: SendService,
        oauth_grant_repo: AsyncMock,
        gmail_adapter: AsyncMock,
    ) -> None:
        """Refreshes token when token_expires_at is in the past."""
        user_id = uuid4()
        grant = _make_grant(
            token_expires_at=datetime.now(UTC) - timedelta(minutes=5)
        )
        oauth_grant_repo.get_by_user_id.return_value = grant
        gmail_adapter.refresh_access_token.return_value = (
            "refreshed_token",
            datetime.now(UTC) + timedelta(hours=1),
        )
        gmail_adapter.send_message.return_value = SentMessageInfo(
            message_id="msg_1", thread_id="thread_1"
        )

        params = _make_send_params()
        result = await send_service.send_email(user_id, params)

        assert result.message_id == "msg_1"
        gmail_adapter.refresh_access_token.assert_called_once()
