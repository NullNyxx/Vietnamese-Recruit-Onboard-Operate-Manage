"""Unit tests for GmailAdapter.

Tests retry logic, rate limiting integration, and Gmail API method behavior
using respx to mock HTTP responses.
"""

import asyncio
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import pytest
import respx

from src.modules.gmail.domain.exceptions import (
    GmailFetchError,
    GmailSendFailedException,
    RateLimitedException,
)
from src.modules.gmail.infrastructure.config import GmailSettings
from src.modules.gmail.infrastructure.gmail_adapter import (
    GMAIL_API_BASE,
    GmailAdapter,
    GmailLabel,
    GmailMessageMetadata,
    MessageBody,
    SentMessageInfo,
)
from src.modules.gmail.infrastructure.quota_tracker import QuotaTracker


@pytest.fixture
def settings():
    """Create GmailSettings with fast retry for testing."""
    return GmailSettings(
        max_retries=3,
        retry_backoff_base=0.01,  # Fast retries for tests
        max_retry_after_seconds=120,
        api_timeout_seconds=5,
        body_fetch_timeout_seconds=5,
        revocation_timeout_seconds=2,
    )


@pytest.fixture
def mock_quota_tracker():
    """Create a mock QuotaTracker that always allows consumption."""
    tracker = AsyncMock(spec=QuotaTracker)
    tracker.wait_if_needed = AsyncMock()
    tracker.consume = AsyncMock()
    return tracker


@pytest.fixture
def user_id():
    """Create a test user ID."""
    return uuid4()


@pytest.fixture
def adapter(settings, mock_quota_tracker, user_id):
    """Create a GmailAdapter with mocked dependencies."""
    client = httpx.AsyncClient()
    return GmailAdapter(
        settings=settings,
        quota_tracker=mock_quota_tracker,
        http_client=client,
        user_id=user_id,
    )


class TestRetryWithBackoff:
    """Tests for the retry_with_backoff method."""

    async def test_success_on_first_attempt(self, adapter):
        """Should return result on first successful call."""
        async def _func():
            return "success"

        result = await adapter.retry_with_backoff(_func)
        assert result == "success"

    async def test_retries_on_5xx(self, adapter, settings):
        """Should retry on 5xx errors and succeed on later attempt."""
        call_count = 0

        with respx.mock:
            route = respx.get(f"{GMAIL_API_BASE}test")
            route.side_effect = [
                httpx.Response(500, text="Server Error"),
                httpx.Response(500, text="Server Error"),
                httpx.Response(200, json={"result": "ok"}),
            ]

            async def _func():
                nonlocal call_count
                call_count += 1
                response = await adapter._http_client.get(
                    f"{GMAIL_API_BASE}test"
                )
                response.raise_for_status()
                return response.json()

            result = await adapter.retry_with_backoff(_func)
            assert result == {"result": "ok"}
            assert call_count == 3

    async def test_no_retry_on_4xx(self, adapter):
        """Should not retry on 4xx errors (except 429)."""
        with respx.mock:
            respx.get(f"{GMAIL_API_BASE}test").respond(400, text="Bad Request")

            async def _func():
                response = await adapter._http_client.get(
                    f"{GMAIL_API_BASE}test"
                )
                response.raise_for_status()
                return response.json()

            with pytest.raises(httpx.HTTPStatusError) as exc_info:
                await adapter.retry_with_backoff(_func)
            assert exc_info.value.response.status_code == 400

    async def test_429_with_retry_after_header(self, adapter):
        """Should wait Retry-After seconds on 429."""
        with respx.mock:
            route = respx.get(f"{GMAIL_API_BASE}test")
            route.side_effect = [
                httpx.Response(429, headers={"Retry-After": "1"}),
                httpx.Response(200, json={"ok": True}),
            ]

            async def _func():
                response = await adapter._http_client.get(
                    f"{GMAIL_API_BASE}test"
                )
                response.raise_for_status()
                return response.json()

            result = await adapter.retry_with_backoff(_func)
            assert result == {"ok": True}

    async def test_429_no_retry_after_header_waits_5s(self, adapter):
        """Should wait 5 seconds when no Retry-After header on 429."""
        with respx.mock:
            route = respx.get(f"{GMAIL_API_BASE}test")
            route.side_effect = [
                httpx.Response(429),
                httpx.Response(200, json={"ok": True}),
            ]

            async def _func():
                response = await adapter._http_client.get(
                    f"{GMAIL_API_BASE}test"
                )
                response.raise_for_status()
                return response.json()

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                result = await adapter.retry_with_backoff(_func)
                assert result == {"ok": True}
                # First call is for quota wait, second for retry-after
                mock_sleep.assert_called_with(5)

    async def test_429_retry_after_exceeds_max_aborts(self, adapter):
        """Should abort when Retry-After exceeds max allowed."""
        with respx.mock:
            respx.get(f"{GMAIL_API_BASE}test").respond(
                429, headers={"Retry-After": "200"}
            )

            async def _func():
                response = await adapter._http_client.get(
                    f"{GMAIL_API_BASE}test"
                )
                response.raise_for_status()
                return response.json()

            with pytest.raises(RateLimitedException) as exc_info:
                await adapter.retry_with_backoff(_func)
            assert "exceeds maximum" in exc_info.value.message

    async def test_3_consecutive_429s_aborts(self, adapter):
        """Should abort after 3 consecutive 429 responses."""
        with respx.mock:
            respx.get(f"{GMAIL_API_BASE}test").respond(
                429, headers={"Retry-After": "1"}
            )

            async def _func():
                response = await adapter._http_client.get(
                    f"{GMAIL_API_BASE}test"
                )
                response.raise_for_status()
                return response.json()

            with pytest.raises(RateLimitedException) as exc_info:
                await adapter.retry_with_backoff(_func)
            assert "3 consecutive" in exc_info.value.message

    async def test_quota_consumed_before_each_attempt(
        self, adapter, mock_quota_tracker
    ):
        """Should consume quota before each retry attempt."""
        async def _func():
            return "ok"

        await adapter.retry_with_backoff(_func, quota_units=10)
        mock_quota_tracker.wait_if_needed.assert_called_once()
        mock_quota_tracker.consume.assert_called_once()


class TestFetchMessages:
    """Tests for the fetch_messages method."""

    async def test_fetch_messages_empty(self, adapter):
        """Should return empty list when no messages."""
        with respx.mock:
            respx.get(f"{GMAIL_API_BASE}messages").respond(
                200, json={"resultSizeEstimate": 0}
            )

            result = await adapter.fetch_messages("token123")
            assert result == []

    async def test_fetch_messages_with_results(self, adapter):
        """Should fetch and parse message metadata."""
        with respx.mock:
            respx.get(f"{GMAIL_API_BASE}messages").respond(
                200,
                json={
                    "messages": [{"id": "msg1", "threadId": "thread1"}],
                    "resultSizeEstimate": 1,
                },
            )
            respx.get(f"{GMAIL_API_BASE}messages/msg1").respond(
                200,
                json={
                    "id": "msg1",
                    "threadId": "thread1",
                    "internalDate": "1700000000000",
                    "snippet": "Hello world",
                    "labelIds": ["INBOX"],
                    "historyId": "12345",
                    "payload": {
                        "headers": [
                            {"name": "From", "value": "John <john@test.com>"},
                            {"name": "To", "value": "jane@test.com"},
                            {"name": "Subject", "value": "Test Email"},
                        ],
                        "parts": [],
                    },
                },
            )

            result = await adapter.fetch_messages("token123")
            assert len(result) == 1
            msg = result[0]
            assert msg.id == "msg1"
            assert msg.thread_id == "thread1"
            assert msg.subject == "Test Email"
            assert msg.sender_email == "john@test.com"
            assert msg.sender_name == "John"
            assert msg.recipient_emails == ["jane@test.com"]
            assert msg.snippet == "Hello world"

    async def test_fetch_messages_401_raises(self, adapter):
        """Should re-raise 401 for token refresh handling."""
        with respx.mock:
            respx.get(f"{GMAIL_API_BASE}messages").respond(401)

            with pytest.raises(httpx.HTTPStatusError) as exc_info:
                await adapter.fetch_messages("bad_token")
            assert exc_info.value.response.status_code == 401


class TestGetMessageBody:
    """Tests for the get_message_body method."""

    async def test_get_plain_text_body(self, adapter):
        """Should decode plain text body."""
        import base64

        plain_content = base64.urlsafe_b64encode(b"Hello plain").decode()
        with respx.mock:
            respx.get(f"{GMAIL_API_BASE}messages/msg1").respond(
                200,
                json={
                    "id": "msg1",
                    "payload": {
                        "mimeType": "text/plain",
                        "body": {"data": plain_content},
                    },
                },
            )

            result = await adapter.get_message_body("token", "msg1")
            assert result.plain_text == "Hello plain"
            assert result.html is None

    async def test_get_multipart_body(self, adapter):
        """Should decode both plain and HTML from multipart."""
        import base64

        plain = base64.urlsafe_b64encode(b"Plain text").decode()
        html = base64.urlsafe_b64encode(b"<p>HTML</p>").decode()
        with respx.mock:
            respx.get(f"{GMAIL_API_BASE}messages/msg1").respond(
                200,
                json={
                    "id": "msg1",
                    "payload": {
                        "mimeType": "multipart/alternative",
                        "parts": [
                            {
                                "mimeType": "text/plain",
                                "body": {"data": plain},
                            },
                            {
                                "mimeType": "text/html",
                                "body": {"data": html},
                            },
                        ],
                    },
                },
            )

            result = await adapter.get_message_body("token", "msg1")
            assert result.plain_text == "Plain text"
            assert result.html == "<p>HTML</p>"

    async def test_get_message_body_404_raises(self, adapter):
        """Should re-raise 404 for message not found."""
        with respx.mock:
            respx.get(f"{GMAIL_API_BASE}messages/missing").respond(404)

            with pytest.raises(httpx.HTTPStatusError) as exc_info:
                await adapter.get_message_body("token", "missing")
            assert exc_info.value.response.status_code == 404


class TestSendMessage:
    """Tests for the send_message method."""

    async def test_send_message_success(self, adapter):
        """Should send message and return SentMessageInfo."""
        with respx.mock:
            respx.post(f"{GMAIL_API_BASE}messages/send").respond(
                200, json={"id": "sent1", "threadId": "thread1"}
            )

            result = await adapter.send_message("token", b"MIME content")
            assert isinstance(result, SentMessageInfo)
            assert result.message_id == "sent1"
            assert result.thread_id == "thread1"

    async def test_send_message_4xx_raises(self, adapter):
        """Should raise GmailSendFailedException on 4xx."""
        with respx.mock:
            respx.post(f"{GMAIL_API_BASE}messages/send").respond(
                400, text="Bad Request"
            )

            with pytest.raises(GmailSendFailedException):
                await adapter.send_message("token", b"bad")


class TestBatchModifyLabels:
    """Tests for the batch_modify_labels method."""

    async def test_batch_splits_at_100(self, adapter):
        """Should split message IDs into batches of 100."""
        call_count = 0

        with respx.mock:
            route = respx.post(f"{GMAIL_API_BASE}messages/batchModify")

            def handler(request):
                nonlocal call_count
                call_count += 1
                return httpx.Response(204)

            route.side_effect = handler

            # 150 messages should result in 2 batch calls
            message_ids = [f"msg{i}" for i in range(150)]
            await adapter.batch_modify_labels(
                "token", message_ids, add_labels=["label1"]
            )
            assert call_count == 2


class TestListLabels:
    """Tests for the list_labels method."""

    async def test_list_labels_success(self, adapter):
        """Should return list of GmailLabel objects."""
        with respx.mock:
            respx.get(f"{GMAIL_API_BASE}labels").respond(
                200,
                json={
                    "labels": [
                        {"id": "Label_1", "name": "VroomHR/processed", "type": "user"},
                        {"id": "INBOX", "name": "INBOX", "type": "system"},
                    ]
                },
            )

            result = await adapter.list_labels("token")
            assert len(result) == 2
            assert result[0].id == "Label_1"
            assert result[0].name == "VroomHR/processed"
            assert result[1].type == "system"


class TestCreateLabel:
    """Tests for the create_label method."""

    async def test_create_label_success(self, adapter):
        """Should create label and return label ID."""
        with respx.mock:
            respx.post(f"{GMAIL_API_BASE}labels").respond(
                200, json={"id": "Label_new", "name": "VroomHR/test"}
            )

            result = await adapter.create_label("token", "VroomHR/test")
            assert result == "Label_new"


class TestRevokeToken:
    """Tests for the revoke_token method."""

    async def test_revoke_success(self, adapter):
        """Should return True on successful revocation."""
        with respx.mock:
            respx.post("https://oauth2.googleapis.com/revoke").respond(200)

            result = await adapter.revoke_token("some_token")
            assert result is True

    async def test_revoke_failure(self, adapter):
        """Should return False on revocation failure."""
        with respx.mock:
            respx.post("https://oauth2.googleapis.com/revoke").respond(400)

            result = await adapter.revoke_token("bad_token")
            assert result is False


class TestRefreshAccessToken:
    """Tests for the refresh_access_token method."""

    async def test_refresh_success(self, adapter):
        """Should return new access token and expiry."""
        with respx.mock:
            respx.post("https://oauth2.googleapis.com/token").respond(
                200,
                json={
                    "access_token": "new_token",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                },
            )

            token, expires_at = await adapter.refresh_access_token(
                "refresh_tok", "client_id", "client_secret"
            )
            assert token == "new_token"
            assert expires_at is not None

    async def test_refresh_failure_raises(self, adapter):
        """Should raise GmailFetchError on refresh failure."""
        with respx.mock:
            respx.post("https://oauth2.googleapis.com/token").respond(
                401, text="Invalid"
            )

            with pytest.raises(GmailFetchError):
                await adapter.refresh_access_token(
                    "bad_refresh", "client_id", "client_secret"
                )
