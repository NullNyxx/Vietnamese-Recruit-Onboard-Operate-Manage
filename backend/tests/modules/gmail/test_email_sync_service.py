"""Unit tests for EmailSyncService."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from src.modules.gmail.application.email_sync_service import EmailSyncService
from src.modules.gmail.domain.entities import EmailMessage, SyncCursor
from src.modules.gmail.domain.exceptions import (
    GmailNotConnectedException,
    RateLimitedException,
)
from src.modules.gmail.infrastructure.config import GmailSettings
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
def sync_cursor_repo() -> AsyncMock:
    """Create a mocked SyncCursorRepository."""
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
def mock_redis() -> AsyncMock:
    """Create a mock async Redis client."""
    return AsyncMock()


@pytest.fixture
def user_id():
    """Create a test user ID."""
    return uuid4()


@pytest.fixture
def sync_service(
    gmail_adapter: AsyncMock,
    email_repo: AsyncMock,
    sync_cursor_repo: AsyncMock,
    oauth_grant_repo: AsyncMock,
    crypto: MagicMock,
    audit_logger: AsyncMock,
    settings: GmailSettings,
    mock_redis: AsyncMock,
) -> EmailSyncService:
    """Create an EmailSyncService with mocked dependencies."""
    return EmailSyncService(
        gmail_adapter=gmail_adapter,
        email_repo=email_repo,
        sync_cursor_repo=sync_cursor_repo,
        oauth_grant_repo=oauth_grant_repo,
        crypto=crypto,
        audit_logger=audit_logger,
        settings=settings,
        redis_client=mock_redis,
        client_id="test-client-id",
        client_secret="test-client-secret",
    )


def _make_grant(
    *,
    is_valid: bool = True,
    access_token_enc: str = "encrypted_test_access_token",
    refresh_token_enc: str = "encrypted_test_refresh_token",
    scopes: list[str] | None = None,
    token_expires_at: datetime | None = None,
):
    """Create a mock OAuth grant."""
    grant = MagicMock()
    grant.is_valid = is_valid
    grant.access_token_enc = access_token_enc
    grant.refresh_token_enc = refresh_token_enc
    grant.scopes = scopes or [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.send",
    ]
    grant.token_expires_at = token_expires_at or (
        datetime.now(UTC) + timedelta(hours=1)
    )
    return grant


def _make_message_metadata(
    msg_id: str = "msg_001",
    thread_id: str = "thread_001",
    history_id: str = "12345",
):
    """Create a mock GmailMessageMetadata."""
    metadata = MagicMock()
    metadata.id = msg_id
    metadata.thread_id = thread_id
    metadata.subject = "Test Subject"
    metadata.sender_email = "sender@example.com"
    metadata.sender_name = "Sender Name"
    metadata.recipient_emails = ["recipient@example.com"]
    metadata.cc_emails = []
    metadata.received_at = datetime.now(UTC)
    metadata.snippet = "Test snippet"
    metadata.label_ids = ["INBOX"]
    metadata.has_attachments = False
    metadata.history_id = history_id
    return metadata


class TestPollEmails:
    """Tests for poll_emails method."""

    async def test_raises_when_no_grant(
        self, sync_service: EmailSyncService, oauth_grant_repo: AsyncMock, user_id
    ) -> None:
        """Should raise GmailNotConnectedException when no grant exists."""
        oauth_grant_repo.get_by_user_id.return_value = None

        with pytest.raises(GmailNotConnectedException):
            await sync_service.poll_emails(user_id)

    async def test_raises_when_grant_invalid(
        self, sync_service: EmailSyncService, oauth_grant_repo: AsyncMock, user_id
    ) -> None:
        """Should raise GmailNotConnectedException when grant is invalid."""
        oauth_grant_repo.get_by_user_id.return_value = _make_grant(is_valid=False)

        with pytest.raises(GmailNotConnectedException):
            await sync_service.poll_emails(user_id)

    async def test_first_poll_fetches_last_7_days(
        self,
        sync_service: EmailSyncService,
        oauth_grant_repo: AsyncMock,
        sync_cursor_repo: AsyncMock,
        gmail_adapter: AsyncMock,
        email_repo: AsyncMock,
        user_id,
    ) -> None:
        """First poll (no cursor) should fetch emails from last 7 days."""
        oauth_grant_repo.get_by_user_id.return_value = _make_grant()
        sync_cursor_repo.get_cursor.return_value = None
        gmail_adapter.fetch_messages.return_value = [_make_message_metadata()]
        email_repo.batch_upsert.return_value = 1

        result = await sync_service.poll_emails(user_id)

        assert result == 1
        # Verify fetch_messages was called with an "after:" query
        call_args = gmail_adapter.fetch_messages.call_args
        assert "after:" in call_args.kwargs["query"]

    async def test_incremental_sync_uses_history(
        self,
        sync_service: EmailSyncService,
        oauth_grant_repo: AsyncMock,
        sync_cursor_repo: AsyncMock,
        gmail_adapter: AsyncMock,
        email_repo: AsyncMock,
        user_id,
    ) -> None:
        """Incremental sync (cursor exists) should use fetch_history."""
        oauth_grant_repo.get_by_user_id.return_value = _make_grant()
        cursor = MagicMock(spec=SyncCursor)
        cursor.history_id = "99999"
        sync_cursor_repo.get_cursor.return_value = cursor
        gmail_adapter.fetch_history.return_value = (
            [_make_message_metadata()],
            "100000",
        )
        email_repo.batch_upsert.return_value = 1

        result = await sync_service.poll_emails(user_id)

        assert result == 1
        gmail_adapter.fetch_history.assert_called_once_with(
            access_token="test_access_token",
            start_history_id="99999",
            max_results=100,
        )

    async def test_updates_cursor_after_successful_fetch(
        self,
        sync_service: EmailSyncService,
        oauth_grant_repo: AsyncMock,
        sync_cursor_repo: AsyncMock,
        gmail_adapter: AsyncMock,
        email_repo: AsyncMock,
        user_id,
    ) -> None:
        """Should update sync cursor after successful fetch."""
        oauth_grant_repo.get_by_user_id.return_value = _make_grant()
        sync_cursor_repo.get_cursor.return_value = None
        gmail_adapter.fetch_messages.return_value = [
            _make_message_metadata(history_id="55555")
        ]
        email_repo.batch_upsert.return_value = 1

        await sync_service.poll_emails(user_id)

        sync_cursor_repo.upsert_cursor.assert_called_once_with(
            user_id=user_id, history_id="55555"
        )

    async def test_no_new_emails_returns_zero(
        self,
        sync_service: EmailSyncService,
        oauth_grant_repo: AsyncMock,
        sync_cursor_repo: AsyncMock,
        gmail_adapter: AsyncMock,
        email_repo: AsyncMock,
        user_id,
    ) -> None:
        """Should return 0 when no new emails are found."""
        oauth_grant_repo.get_by_user_id.return_value = _make_grant()
        sync_cursor_repo.get_cursor.return_value = None
        gmail_adapter.fetch_messages.return_value = []

        result = await sync_service.poll_emails(user_id)

        assert result == 0
        email_repo.batch_upsert.assert_not_called()

    async def test_token_refresh_on_401(
        self,
        sync_service: EmailSyncService,
        oauth_grant_repo: AsyncMock,
        sync_cursor_repo: AsyncMock,
        gmail_adapter: AsyncMock,
        email_repo: AsyncMock,
        user_id,
    ) -> None:
        """Should attempt token refresh on 401 and retry."""
        grant = _make_grant()
        oauth_grant_repo.get_by_user_id.return_value = grant
        sync_cursor_repo.get_cursor.return_value = None

        # First call raises 401, second call succeeds
        response_401 = MagicMock()
        response_401.status_code = 401
        gmail_adapter.fetch_messages.side_effect = [
            httpx.HTTPStatusError("401", request=MagicMock(), response=response_401),
            [_make_message_metadata()],
        ]
        gmail_adapter.refresh_access_token.return_value = (
            "new_access_token",
            datetime.now(UTC) + timedelta(hours=1),
        )
        email_repo.batch_upsert.return_value = 1

        result = await sync_service.poll_emails(user_id)

        assert result == 1
        gmail_adapter.refresh_access_token.assert_called_once()

    async def test_token_refresh_failure_marks_invalid(
        self,
        sync_service: EmailSyncService,
        oauth_grant_repo: AsyncMock,
        sync_cursor_repo: AsyncMock,
        gmail_adapter: AsyncMock,
        audit_logger: AsyncMock,
        user_id,
    ) -> None:
        """Should mark grant invalid when token refresh fails."""
        grant = _make_grant()
        oauth_grant_repo.get_by_user_id.return_value = grant
        sync_cursor_repo.get_cursor.return_value = None

        response_401 = MagicMock()
        response_401.status_code = 401
        gmail_adapter.fetch_messages.side_effect = httpx.HTTPStatusError(
            "401", request=MagicMock(), response=response_401
        )
        gmail_adapter.refresh_access_token.side_effect = Exception("Refresh failed")

        result = await sync_service.poll_emails(user_id)

        assert result == 0
        oauth_grant_repo.mark_invalid.assert_called_once_with(user_id)

    async def test_logs_audit_on_success(
        self,
        sync_service: EmailSyncService,
        oauth_grant_repo: AsyncMock,
        sync_cursor_repo: AsyncMock,
        gmail_adapter: AsyncMock,
        email_repo: AsyncMock,
        audit_logger: AsyncMock,
        user_id,
    ) -> None:
        """Should log audit entry on successful poll."""
        oauth_grant_repo.get_by_user_id.return_value = _make_grant()
        sync_cursor_repo.get_cursor.return_value = None
        gmail_adapter.fetch_messages.return_value = [_make_message_metadata()]
        email_repo.batch_upsert.return_value = 1

        await sync_service.poll_emails(user_id)

        audit_logger.log_operation.assert_called_once_with(
            operation_type="fetch",
            user_id=user_id,
            message_count=1,
            success=True,
            metadata={"sync_type": "poll"},
        )


class TestManualSync:
    """Tests for manual_sync method."""

    async def test_raises_rate_limited_within_cooldown(
        self,
        sync_service: EmailSyncService,
        mock_redis: AsyncMock,
        user_id,
    ) -> None:
        """Should raise RateLimitedException within cooldown period."""
        import time

        # Simulate a recent manual sync (5 seconds ago)
        mock_redis.get.return_value = str(time.time() - 5).encode()

        with pytest.raises(RateLimitedException):
            await sync_service.manual_sync(user_id)

    async def test_allows_sync_after_cooldown(
        self,
        sync_service: EmailSyncService,
        oauth_grant_repo: AsyncMock,
        sync_cursor_repo: AsyncMock,
        gmail_adapter: AsyncMock,
        email_repo: AsyncMock,
        mock_redis: AsyncMock,
        user_id,
    ) -> None:
        """Should allow manual sync after cooldown period."""
        import time

        # Simulate last sync was 60 seconds ago (beyond 30s cooldown)
        mock_redis.get.return_value = str(time.time() - 60).encode()
        oauth_grant_repo.get_by_user_id.return_value = _make_grant()
        sync_cursor_repo.get_cursor.return_value = None
        gmail_adapter.fetch_messages.return_value = [_make_message_metadata()]
        email_repo.batch_upsert.return_value = 1

        result = await sync_service.manual_sync(user_id)

        assert result == 1

    async def test_allows_first_manual_sync(
        self,
        sync_service: EmailSyncService,
        oauth_grant_repo: AsyncMock,
        sync_cursor_repo: AsyncMock,
        gmail_adapter: AsyncMock,
        email_repo: AsyncMock,
        mock_redis: AsyncMock,
        user_id,
    ) -> None:
        """Should allow manual sync when no previous sync recorded."""
        mock_redis.get.return_value = None
        oauth_grant_repo.get_by_user_id.return_value = _make_grant()
        sync_cursor_repo.get_cursor.return_value = None
        gmail_adapter.fetch_messages.return_value = [_make_message_metadata()]
        email_repo.batch_upsert.return_value = 1

        result = await sync_service.manual_sync(user_id)

        assert result == 1

    async def test_records_timestamp_after_sync(
        self,
        sync_service: EmailSyncService,
        oauth_grant_repo: AsyncMock,
        sync_cursor_repo: AsyncMock,
        gmail_adapter: AsyncMock,
        email_repo: AsyncMock,
        mock_redis: AsyncMock,
        user_id,
    ) -> None:
        """Should record manual sync timestamp in Redis after success."""
        mock_redis.get.return_value = None
        oauth_grant_repo.get_by_user_id.return_value = _make_grant()
        sync_cursor_repo.get_cursor.return_value = None
        gmail_adapter.fetch_messages.return_value = []

        await sync_service.manual_sync(user_id)

        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert f"gmail:manual_sync:{user_id}" == call_args.args[0]
        assert call_args.kwargs["ex"] == 30

    async def test_raises_not_connected(
        self,
        sync_service: EmailSyncService,
        oauth_grant_repo: AsyncMock,
        mock_redis: AsyncMock,
        user_id,
    ) -> None:
        """Should raise GmailNotConnectedException when not connected."""
        mock_redis.get.return_value = None
        oauth_grant_repo.get_by_user_id.return_value = None

        with pytest.raises(GmailNotConnectedException):
            await sync_service.manual_sync(user_id)

    async def test_logs_audit_with_manual_type(
        self,
        sync_service: EmailSyncService,
        oauth_grant_repo: AsyncMock,
        sync_cursor_repo: AsyncMock,
        gmail_adapter: AsyncMock,
        email_repo: AsyncMock,
        mock_redis: AsyncMock,
        audit_logger: AsyncMock,
        user_id,
    ) -> None:
        """Should log audit entry with sync_type=manual."""
        mock_redis.get.return_value = None
        oauth_grant_repo.get_by_user_id.return_value = _make_grant()
        sync_cursor_repo.get_cursor.return_value = None
        gmail_adapter.fetch_messages.return_value = [_make_message_metadata()]
        email_repo.batch_upsert.return_value = 1

        await sync_service.manual_sync(user_id)

        audit_logger.log_operation.assert_called_once_with(
            operation_type="fetch",
            user_id=user_id,
            message_count=1,
            success=True,
            metadata={"sync_type": "manual"},
        )


class TestFetchAndPersist:
    """Tests for _fetch_and_persist method."""

    async def test_first_poll_uses_after_query(
        self,
        sync_service: EmailSyncService,
        gmail_adapter: AsyncMock,
        email_repo: AsyncMock,
        sync_cursor_repo: AsyncMock,
        user_id,
    ) -> None:
        """First poll should use 'after:' query with epoch timestamp."""
        gmail_adapter.fetch_messages.return_value = []

        await sync_service._fetch_and_persist(user_id, "token", None)

        call_args = gmail_adapter.fetch_messages.call_args
        query = call_args.kwargs["query"]
        assert query.startswith("after:")
        # Verify the epoch is roughly 7 days ago
        epoch = int(query.split(":")[1])
        seven_days_ago = int((datetime.now(UTC) - timedelta(days=7)).timestamp())
        assert abs(epoch - seven_days_ago) < 10  # within 10 seconds

    async def test_incremental_sync_uses_fetch_history(
        self,
        sync_service: EmailSyncService,
        gmail_adapter: AsyncMock,
        email_repo: AsyncMock,
        sync_cursor_repo: AsyncMock,
        user_id,
    ) -> None:
        """Incremental sync should use fetch_history with stored history_id."""
        cursor = MagicMock(spec=SyncCursor)
        cursor.history_id = "12345"
        gmail_adapter.fetch_history.return_value = ([], "12345")

        await sync_service._fetch_and_persist(user_id, "token", cursor)

        gmail_adapter.fetch_history.assert_called_once_with(
            access_token="token",
            start_history_id="12345",
            max_results=100,
        )

    async def test_persists_converted_entities(
        self,
        sync_service: EmailSyncService,
        gmail_adapter: AsyncMock,
        email_repo: AsyncMock,
        sync_cursor_repo: AsyncMock,
        user_id,
    ) -> None:
        """Should convert metadata to entities and batch upsert."""
        gmail_adapter.fetch_messages.return_value = [
            _make_message_metadata("msg_1", history_id="100"),
            _make_message_metadata("msg_2", history_id="101"),
        ]
        email_repo.batch_upsert.return_value = 2

        result = await sync_service._fetch_and_persist(user_id, "token", None)

        assert result == 2
        # Verify batch_upsert was called with 2 entities
        call_args = email_repo.batch_upsert.call_args
        entities = call_args.args[0]
        assert len(entities) == 2
        assert entities[0].gmail_message_id == "msg_1"
        assert entities[1].gmail_message_id == "msg_2"


class TestHandleTokenRefresh:
    """Tests for _handle_token_refresh method."""

    async def test_successful_refresh(
        self,
        sync_service: EmailSyncService,
        oauth_grant_repo: AsyncMock,
        gmail_adapter: AsyncMock,
        crypto: MagicMock,
        user_id,
    ) -> None:
        """Should return new access token on successful refresh."""
        grant = _make_grant()
        oauth_grant_repo.get_by_user_id.return_value = grant
        new_expires = datetime.now(UTC) + timedelta(hours=1)
        gmail_adapter.refresh_access_token.return_value = (
            "new_token",
            new_expires,
        )

        result = await sync_service._handle_token_refresh(user_id)

        assert result == "new_token"
        oauth_grant_repo.upsert.assert_called_once()

    async def test_refresh_failure_marks_invalid(
        self,
        sync_service: EmailSyncService,
        oauth_grant_repo: AsyncMock,
        gmail_adapter: AsyncMock,
        audit_logger: AsyncMock,
        user_id,
    ) -> None:
        """Should mark grant invalid and return None on refresh failure."""
        grant = _make_grant()
        oauth_grant_repo.get_by_user_id.return_value = grant
        gmail_adapter.refresh_access_token.side_effect = Exception("Failed")

        result = await sync_service._handle_token_refresh(user_id)

        assert result is None
        oauth_grant_repo.mark_invalid.assert_called_once_with(user_id)

    async def test_returns_none_when_no_grant(
        self,
        sync_service: EmailSyncService,
        oauth_grant_repo: AsyncMock,
        user_id,
    ) -> None:
        """Should return None when no grant exists."""
        oauth_grant_repo.get_by_user_id.return_value = None

        result = await sync_service._handle_token_refresh(user_id)

        assert result is None


class TestPartialFailureHandling:
    """Tests for partial failure and permanent failure handling."""

    async def test_increments_retry_count_for_failed_messages(
        self,
        sync_service: EmailSyncService,
        email_repo: AsyncMock,
    ) -> None:
        """Should increment retry count for each failed message."""
        email_repo.increment_retry_count.return_value = MagicMock(retry_count=1)

        await sync_service._handle_failed_messages(["msg_1", "msg_2"])

        assert email_repo.increment_retry_count.call_count == 2

    async def test_marks_permanently_failed_at_threshold(
        self,
        sync_service: EmailSyncService,
        email_repo: AsyncMock,
    ) -> None:
        """Should mark message as permanently failed at 5 retries."""
        updated_msg = MagicMock()
        updated_msg.retry_count = 5
        email_repo.increment_retry_count.return_value = updated_msg

        await sync_service._handle_failed_messages(["msg_1"])

        email_repo.mark_permanently_failed.assert_called_once_with("msg_1")

    async def test_does_not_mark_permanent_below_threshold(
        self,
        sync_service: EmailSyncService,
        email_repo: AsyncMock,
    ) -> None:
        """Should not mark as permanently failed below threshold."""
        updated_msg = MagicMock()
        updated_msg.retry_count = 4
        email_repo.increment_retry_count.return_value = updated_msg

        await sync_service._handle_failed_messages(["msg_1"])

        email_repo.mark_permanently_failed.assert_not_called()

    async def test_continues_on_individual_failure(
        self,
        sync_service: EmailSyncService,
        email_repo: AsyncMock,
    ) -> None:
        """Should continue processing other messages if one fails."""
        email_repo.increment_retry_count.side_effect = [
            Exception("DB error"),
            MagicMock(retry_count=1),
        ]

        # Should not raise
        await sync_service._handle_failed_messages(["msg_1", "msg_2"])

        assert email_repo.increment_retry_count.call_count == 2


class TestMetadataToEntity:
    """Tests for _metadata_to_entity conversion."""

    def test_converts_metadata_to_entity(self, sync_service: EmailSyncService) -> None:
        """Should correctly map metadata fields to entity."""
        user_id = uuid4()
        metadata = _make_message_metadata("msg_123", "thread_456")

        entity = sync_service._metadata_to_entity(user_id, metadata)

        assert entity.user_id == user_id
        assert entity.gmail_message_id == "msg_123"
        assert entity.gmail_thread_id == "thread_456"
        assert entity.subject == "Test Subject"
        assert entity.sender_email == "sender@example.com"
        assert entity.sender_name == "Sender Name"
        assert entity.recipient_emails == ["recipient@example.com"]
        assert entity.has_attachments is False

    def test_truncates_subject_to_998_chars(
        self, sync_service: EmailSyncService
    ) -> None:
        """Should truncate subject to 998 characters."""
        user_id = uuid4()
        metadata = _make_message_metadata()
        metadata.subject = "x" * 2000

        entity = sync_service._metadata_to_entity(user_id, metadata)

        assert len(entity.subject) == 998

    def test_defaults_empty_string_for_missing_fields(
        self, sync_service: EmailSyncService
    ) -> None:
        """Should use empty string for None/empty fields."""
        user_id = uuid4()
        metadata = _make_message_metadata()
        metadata.subject = None
        metadata.sender_email = None
        metadata.sender_name = None
        metadata.snippet = None

        entity = sync_service._metadata_to_entity(user_id, metadata)

        assert entity.subject == ""
        assert entity.sender_email == ""
        assert entity.sender_name == ""
        assert entity.snippet == ""

    def test_limits_recipients_to_50(self, sync_service: EmailSyncService) -> None:
        """Should limit recipient_emails to 50 entries."""
        user_id = uuid4()
        metadata = _make_message_metadata()
        metadata.recipient_emails = [f"user{i}@example.com" for i in range(100)]

        entity = sync_service._metadata_to_entity(user_id, metadata)

        assert len(entity.recipient_emails) == 50
