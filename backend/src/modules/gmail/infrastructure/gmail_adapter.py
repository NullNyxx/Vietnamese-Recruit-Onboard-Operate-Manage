"""Gmail API adapter with rate limiting, retry logic, and quota tracking.

Encapsulates all Gmail API interactions using httpx for async HTTP calls.
Integrates QuotaTracker for per-user rate limiting and implements exponential
backoff retry for transient failures (5xx, 429).
"""

import asyncio
import base64
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx

from src.modules.gmail.domain.exceptions import (
    GmailFetchError,
    GmailSendFailedException,
    RateLimitedException,
)
from src.modules.gmail.infrastructure.config import GmailSettings
from src.modules.gmail.infrastructure.quota_tracker import QuotaTracker

logger = logging.getLogger(__name__)

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me/"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"


@dataclass
class GmailMessageMetadata:
    """Metadata for a Gmail message returned by messages.list."""

    id: str
    thread_id: str
    subject: str = ""
    sender_email: str = ""
    sender_name: str = ""
    recipient_emails: list[str] = field(default_factory=list)
    cc_emails: list[str] = field(default_factory=list)
    received_at: datetime | None = None
    snippet: str = ""
    label_ids: list[str] = field(default_factory=list)
    has_attachments: bool = False
    history_id: str = ""


@dataclass
class MessageBody:
    """Decoded email body content."""

    plain_text: str | None = None
    html: str | None = None


@dataclass
class SentMessageInfo:
    """Information about a successfully sent message."""

    message_id: str
    thread_id: str


@dataclass
class GmailLabel:
    """A Gmail label."""

    id: str
    name: str
    type: str = "user"


class GmailAdapter:
    """Gmail API client wrapper with rate limiting and retry.

    All Gmail API interactions go through this adapter. It integrates
    QuotaTracker for per-user rate limiting and implements exponential
    backoff retry for transient failures.

    Args:
        settings: GmailSettings with retry, timeout, and quota config.
        quota_tracker: Redis-based quota tracker for rate limiting.
        http_client: httpx.AsyncClient for making HTTP requests.
        user_id: The UUID of the user (for quota tracking).
    """

    def __init__(
        self,
        settings: GmailSettings,
        quota_tracker: QuotaTracker,
        http_client: httpx.AsyncClient,
        user_id: UUID,
    ) -> None:
        """Initialize the Gmail adapter.

        Args:
            settings: Gmail module configuration.
            quota_tracker: Redis-based quota tracker instance.
            http_client: Async HTTP client for API calls.
            user_id: User ID for quota tracking.
        """
        self._settings = settings
        self._quota_tracker = quota_tracker
        self._http_client = http_client
        self._user_id = user_id

    async def _consume_quota(self, units: int = 5) -> None:
        """Wait for quota availability and consume units.

        Args:
            units: Number of quota units to consume for this API call.
        """
        await self._quota_tracker.wait_if_needed(self._user_id, units)
        await self._quota_tracker.consume(self._user_id, units)

    async def retry_with_backoff(
        self,
        func,
        *,
        max_retries: int | None = None,
        base_delay: float | None = None,
        timeout: float | None = None,
        quota_units: int = 5,
    ):
        """Execute an async function with exponential backoff retry.

        Retries on 5xx errors and 429 (with Retry-After handling).
        Does not retry on 4xx errors (except 429).

        Delays: base_delay * 2^attempt (default 1s, 2s, 4s).
        Individual request timeout: 30 seconds (configurable).

        Args:
            func: Async callable that makes the HTTP request.
            max_retries: Maximum retry attempts (default from settings).
            base_delay: Base delay in seconds (default from settings).
            timeout: Per-request timeout in seconds (default from settings).
            quota_units: Quota units to consume before each attempt.

        Returns:
            The result of the successful function call.

        Raises:
            httpx.HTTPStatusError: If all retries exhausted or non-retryable.
            asyncio.TimeoutError: If request times out on final attempt.
            RateLimitedException: If 429 with Retry-After > max allowed.
        """
        if max_retries is None:
            max_retries = self._settings.max_retries
        if base_delay is None:
            base_delay = self._settings.retry_backoff_base
        if timeout is None:
            timeout = float(self._settings.api_timeout_seconds)

        consecutive_429s = 0

        for attempt in range(max_retries + 1):
            await self._consume_quota(quota_units)

            try:
                result = await asyncio.wait_for(func(), timeout=timeout)
                return result
            except TimeoutError:
                if attempt == max_retries:
                    raise
                logger.warning(
                    "Request timed out (attempt %d/%d)",
                    attempt + 1,
                    max_retries + 1,
                )
                await asyncio.sleep(base_delay * (2**attempt))
            except (httpx.ConnectError, httpx.ConnectTimeout, OSError) as exc:
                # Network/DNS errors are transient and retryable
                if attempt == max_retries:
                    raise GmailFetchError(
                        f"Connection failed after {max_retries + 1} attempts: {exc}"
                    ) from exc
                logger.warning(
                    "Connection error (attempt %d/%d): %s",
                    attempt + 1,
                    max_retries + 1,
                    str(exc),
                )
                await asyncio.sleep(base_delay * (2**attempt))
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code

                # Handle 429 with Retry-After logic
                if status_code == 429:
                    consecutive_429s += 1
                    if consecutive_429s >= 3:
                        logger.warning(
                            "3 consecutive 429s in poll cycle, aborting"
                        )
                        raise RateLimitedException(
                            "Rate limit exceeded: 3 consecutive 429 responses"
                        )

                    retry_after = self._parse_retry_after(exc.response)
                    max_wait = self._settings.max_retry_after_seconds

                    if retry_after > max_wait:
                        logger.error(
                            "Retry-After %ds exceeds max %ds, aborting",
                            retry_after,
                            max_wait,
                        )
                        raise RateLimitedException(
                            f"Retry-After {retry_after}s exceeds maximum "
                            f"allowed wait time of {max_wait}s",
                            retry_after=retry_after,
                        )

                    if attempt == max_retries:
                        raise

                    logger.info(
                        "Rate limited, waiting %ds (attempt %d/%d)",
                        retry_after,
                        attempt + 1,
                        max_retries + 1,
                    )
                    await asyncio.sleep(retry_after)
                    continue

                # 5xx errors are retryable
                if 500 <= status_code < 600:
                    if attempt == max_retries:
                        raise
                    logger.warning(
                        "Server error %d (attempt %d/%d)",
                        status_code,
                        attempt + 1,
                        max_retries + 1,
                    )
                    await asyncio.sleep(base_delay * (2**attempt))
                    continue

                # 4xx errors (except 429) are not retryable
                raise

    def _parse_retry_after(self, response: httpx.Response) -> int:
        """Parse the Retry-After header from a 429 response.

        Args:
            response: The HTTP response with status 429.

        Returns:
            Number of seconds to wait. Defaults to 5 if header missing.
        """
        retry_after_header = response.headers.get("Retry-After")
        if retry_after_header is None:
            return 5

        try:
            return int(retry_after_header)
        except (ValueError, TypeError):
            return 5

    def _auth_headers(self, access_token: str) -> dict[str, str]:
        """Build authorization headers for Gmail API requests.

        Args:
            access_token: OAuth2 access token.

        Returns:
            Dictionary with Authorization header.
        """
        return {"Authorization": f"Bearer {access_token}"}

    async def fetch_messages(
        self,
        access_token: str,
        query: str | None = None,
        max_results: int = 100,
    ) -> list[GmailMessageMetadata]:
        """Fetch message metadata from Gmail using messages.list + get.

        Fetches message IDs via messages.list, then retrieves metadata
        for each message. Returns up to max_results messages.

        Args:
            access_token: OAuth2 access token.
            query: Optional Gmail search query (e.g., "after:2024/01/01").
            max_results: Maximum number of messages to fetch (default 100).

        Returns:
            List of GmailMessageMetadata objects.

        Raises:
            GmailFetchError: If the API call fails after retries.
        """
        try:
            messages = await self._list_message_ids(
                access_token, query=query, max_results=max_results
            )
            if not messages:
                return []

            results: list[GmailMessageMetadata] = []
            for msg_stub in messages[:max_results]:
                metadata = await self._get_message_metadata(
                    access_token, msg_stub["id"]
                )
                if metadata:
                    results.append(metadata)
            return results
        except (RateLimitedException, httpx.HTTPStatusError) as exc:
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 401:
                raise
            raise GmailFetchError(f"Failed to fetch messages: {exc}") from exc

    async def _list_message_ids(
        self,
        access_token: str,
        query: str | None = None,
        max_results: int = 100,
    ) -> list[dict]:
        """List message IDs from Gmail API messages.list.

        Args:
            access_token: OAuth2 access token.
            query: Optional Gmail search query.
            max_results: Maximum results to return.

        Returns:
            List of message stubs with 'id' and 'threadId' keys.
        """
        params: dict[str, str | int] = {"maxResults": max_results}
        if query:
            params["q"] = query

        async def _request():
            response = await self._http_client.get(
                f"{GMAIL_API_BASE}messages",
                headers=self._auth_headers(access_token),
                params=params,
            )
            response.raise_for_status()
            return response.json()

        data = await self.retry_with_backoff(_request, quota_units=5)
        return data.get("messages", [])

    async def _get_message_metadata(
        self, access_token: str, message_id: str
    ) -> GmailMessageMetadata | None:
        """Fetch metadata for a single message.

        Args:
            access_token: OAuth2 access token.
            message_id: Gmail message ID.

        Returns:
            GmailMessageMetadata or None if fetch fails.
        """
        async def _request():
            response = await self._http_client.get(
                f"{GMAIL_API_BASE}messages/{message_id}",
                headers=self._auth_headers(access_token),
                params={"format": "metadata"},
            )
            response.raise_for_status()
            return response.json()

        try:
            data = await self.retry_with_backoff(_request, quota_units=5)
            return self._parse_message_metadata(data)
        except Exception as exc:
            logger.warning(
                "Failed to fetch metadata for message %s: %s",
                message_id,
                exc,
            )
            return None

    def _parse_message_metadata(self, data: dict) -> GmailMessageMetadata:
        """Parse Gmail API message response into GmailMessageMetadata.

        Args:
            data: Raw JSON response from messages.get.

        Returns:
            Parsed GmailMessageMetadata object.
        """
        headers = {}
        for header in data.get("payload", {}).get("headers", []):
            name = header.get("name", "").lower()
            headers[name] = header.get("value", "")

        # Parse sender
        from_header = headers.get("from", "")
        sender_name, sender_email = self._parse_email_address(from_header)

        # Parse recipients
        to_header = headers.get("to", "")
        recipient_emails = self._parse_email_list(to_header)

        # Parse CC
        cc_header = headers.get("cc", "")
        cc_emails = self._parse_email_list(cc_header)

        # Parse date
        received_at = None
        internal_date = data.get("internalDate")
        if internal_date:
            try:
                received_at = datetime.fromtimestamp(
                    int(internal_date) / 1000, tz=UTC
                )
            except (ValueError, TypeError, OSError):
                received_at = None

        # Check for attachments
        has_attachments = self._check_has_attachments(data.get("payload", {}))

        return GmailMessageMetadata(
            id=data.get("id", ""),
            thread_id=data.get("threadId", ""),
            subject=headers.get("subject", ""),
            sender_email=sender_email,
            sender_name=sender_name,
            recipient_emails=recipient_emails[:50],
            cc_emails=cc_emails[:50],
            received_at=received_at,
            snippet=data.get("snippet", "")[:200],
            label_ids=data.get("labelIds", []),
            has_attachments=has_attachments,
            history_id=data.get("historyId", ""),
        )

    def _parse_email_address(self, address: str) -> tuple[str, str]:
        """Parse a From header into (name, email).

        Handles formats like:
        - "John Doe <john@example.com>"
        - "john@example.com"
        - "<john@example.com>"

        Args:
            address: Raw email address string.

        Returns:
            Tuple of (display_name, email_address).
        """
        if not address:
            return ("", "")

        if "<" in address and ">" in address:
            name_part = address[: address.index("<")].strip().strip('"')
            email_part = address[address.index("<") + 1 : address.index(">")]
            return (name_part, email_part)

        return ("", address.strip())

    def _parse_email_list(self, header: str) -> list[str]:
        """Parse a comma-separated email list header into email addresses.

        Args:
            header: Raw To or CC header value.

        Returns:
            List of email address strings.
        """
        if not header:
            return []

        addresses = []
        for part in header.split(","):
            part = part.strip()
            if not part:
                continue
            _, email = self._parse_email_address(part)
            if email:
                addresses.append(email)
        return addresses

    def _check_has_attachments(self, payload: dict) -> bool:
        """Check if a message payload contains attachments.

        Args:
            payload: The message payload from Gmail API.

        Returns:
            True if the message has attachments.
        """
        parts = payload.get("parts", [])
        for part in parts:
            if part.get("filename"):
                return True
            # Check nested parts (multipart messages)
            if part.get("parts"):
                if self._check_has_attachments(part):
                    return True
        return False

    async def fetch_history(
        self,
        access_token: str,
        start_history_id: str,
        max_results: int = 100,
    ) -> tuple[list[GmailMessageMetadata], str]:
        """Fetch message changes since a history ID using history.list.

        Args:
            access_token: OAuth2 access token.
            start_history_id: The history ID to start from.
            max_results: Maximum number of messages to return.

        Returns:
            Tuple of (list of message metadata, latest history_id).

        Raises:
            GmailFetchError: If the API call fails after retries.
        """
        try:
            params: dict[str, str | int] = {
                "startHistoryId": start_history_id,
                "maxResults": max_results,
                "historyTypes": "messageAdded",
            }

            async def _request():
                response = await self._http_client.get(
                    f"{GMAIL_API_BASE}history",
                    headers=self._auth_headers(access_token),
                    params=params,
                )
                response.raise_for_status()
                return response.json()

            data = await self.retry_with_backoff(_request, quota_units=5)

            latest_history_id = data.get("historyId", start_history_id)
            history_records = data.get("history", [])

            # Collect unique message IDs from history
            seen_ids: set[str] = set()
            message_ids: list[str] = []
            for record in history_records:
                for msg in record.get("messagesAdded", []):
                    msg_id = msg.get("message", {}).get("id")
                    if msg_id and msg_id not in seen_ids:
                        seen_ids.add(msg_id)
                        message_ids.append(msg_id)

            # Fetch metadata for each new message
            results: list[GmailMessageMetadata] = []
            for msg_id in message_ids[:max_results]:
                metadata = await self._get_message_metadata(
                    access_token, msg_id
                )
                if metadata:
                    results.append(metadata)

            return results, latest_history_id
        except (RateLimitedException, httpx.HTTPStatusError) as exc:
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 401:
                raise
            if isinstance(exc, RateLimitedException):
                raise
            raise GmailFetchError(
                f"Failed to fetch history: {exc}"
            ) from exc

    async def get_message_body(
        self, access_token: str, message_id: str
    ) -> MessageBody:
        """Fetch the full message body (text/plain and text/html parts).

        Args:
            access_token: OAuth2 access token.
            message_id: Gmail message ID.

        Returns:
            MessageBody with plain_text and/or html content.

        Raises:
            GmailFetchError: If the API call fails after retries.
            httpx.HTTPStatusError: If message not found (404) or auth (401).
        """
        async def _request():
            response = await self._http_client.get(
                f"{GMAIL_API_BASE}messages/{message_id}",
                headers=self._auth_headers(access_token),
                params={"format": "full"},
            )
            response.raise_for_status()
            return response.json()

        try:
            data = await self.retry_with_backoff(
                _request,
                timeout=float(self._settings.body_fetch_timeout_seconds),
                quota_units=5,
            )
            return self._extract_body(data.get("payload", {}))
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (401, 404):
                raise
            raise GmailFetchError(
                f"Failed to fetch message body: {exc}"
            ) from exc

    def _extract_body(self, payload: dict) -> MessageBody:
        """Extract text/plain and text/html body parts from message payload.

        Recursively searches multipart message structure for body content.

        Args:
            payload: The message payload from Gmail API.

        Returns:
            MessageBody with decoded plain_text and/or html content.
        """
        plain_text: str | None = None
        html: str | None = None

        mime_type = payload.get("mimeType", "")

        if mime_type == "text/plain":
            body_data = payload.get("body", {}).get("data", "")
            if body_data:
                plain_text = self._decode_base64url(body_data)
        elif mime_type == "text/html":
            body_data = payload.get("body", {}).get("data", "")
            if body_data:
                html = self._decode_base64url(body_data)
        elif mime_type.startswith("multipart/"):
            for part in payload.get("parts", []):
                part_body = self._extract_body(part)
                if part_body.plain_text and not plain_text:
                    plain_text = part_body.plain_text
                if part_body.html and not html:
                    html = part_body.html

        return MessageBody(plain_text=plain_text, html=html)

    def _decode_base64url(self, data: str) -> str:
        """Decode base64url-encoded string (Gmail API format).

        Args:
            data: Base64url-encoded string.

        Returns:
            Decoded UTF-8 string.
        """
        # Gmail uses URL-safe base64 without padding
        padded = data + "=" * (4 - len(data) % 4) if len(data) % 4 else data
        decoded_bytes = base64.urlsafe_b64decode(padded)
        return decoded_bytes.decode("utf-8", errors="replace")

    async def send_message(
        self, access_token: str, mime_message: bytes
    ) -> SentMessageInfo:
        """Send an email via Gmail API messages.send.

        Args:
            access_token: OAuth2 access token.
            mime_message: RFC 2822 MIME message as bytes.

        Returns:
            SentMessageInfo with message_id and thread_id.

        Raises:
            GmailSendFailedException: If send fails after retries.
            httpx.HTTPStatusError: If 401 (for token refresh handling).
        """
        # Encode the MIME message as base64url for the Gmail API
        encoded_message = base64.urlsafe_b64encode(mime_message).decode("ascii")

        async def _request():
            response = await self._http_client.post(
                f"{GMAIL_API_BASE}messages/send",
                headers=self._auth_headers(access_token),
                json={"raw": encoded_message},
            )
            response.raise_for_status()
            return response.json()

        try:
            data = await self.retry_with_backoff(_request, quota_units=100)
            return SentMessageInfo(
                message_id=data.get("id", ""),
                thread_id=data.get("threadId", ""),
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise
            raise GmailSendFailedException(
                f"Failed to send email: {exc.response.status_code} "
                f"{exc.response.text}"
            ) from exc

    async def get_attachment(
        self, access_token: str, message_id: str, attachment_id: str
    ) -> bytes:
        """Fetch attachment data from Gmail API.

        Args:
            access_token: OAuth2 access token.
            message_id: Gmail message ID containing the attachment.
            attachment_id: Gmail attachment ID.

        Returns:
            Raw attachment bytes.

        Raises:
            GmailFetchError: If the API call fails after retries.
            httpx.HTTPStatusError: If 401 (for token refresh handling).
        """
        async def _request():
            response = await self._http_client.get(
                f"{GMAIL_API_BASE}messages/{message_id}/attachments/{attachment_id}",
                headers=self._auth_headers(access_token),
            )
            response.raise_for_status()
            return response.json()

        try:
            data = await self.retry_with_backoff(_request, quota_units=5)
            # Gmail returns attachment data as base64url-encoded
            encoded_data = data.get("data", "")
            padded = (
                encoded_data + "=" * (4 - len(encoded_data) % 4)
                if len(encoded_data) % 4
                else encoded_data
            )
            return base64.urlsafe_b64decode(padded)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise
            raise GmailFetchError(
                f"Failed to fetch attachment: {exc}"
            ) from exc

    async def modify_labels(
        self,
        access_token: str,
        message_ids: list[str],
        add_labels: list[str] | None = None,
        remove_labels: list[str] | None = None,
    ) -> None:
        """Modify labels on individual messages via messages.modify.

        For single messages, uses messages.modify. For multiple messages,
        use batch_modify_labels instead.

        Args:
            access_token: OAuth2 access token.
            message_ids: List of Gmail message IDs to modify.
            add_labels: Label IDs to add.
            remove_labels: Label IDs to remove.

        Raises:
            GmailFetchError: If the API call fails after retries.
            httpx.HTTPStatusError: If 401 (for token refresh handling).
        """
        add_labels = add_labels or []
        remove_labels = remove_labels or []

        for message_id in message_ids:
            async def _request(msg_id=message_id):
                response = await self._http_client.post(
                    f"{GMAIL_API_BASE}messages/{msg_id}/modify",
                    headers=self._auth_headers(access_token),
                    json={
                        "addLabelIds": add_labels,
                        "removeLabelIds": remove_labels,
                    },
                )
                response.raise_for_status()
                return response.json()

            try:
                await self.retry_with_backoff(_request, quota_units=5)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 401:
                    raise
                raise GmailFetchError(
                    f"Failed to modify labels for message {message_id}: {exc}"
                ) from exc

    async def batch_modify_labels(
        self,
        access_token: str,
        message_ids: list[str],
        add_labels: list[str] | None = None,
        remove_labels: list[str] | None = None,
    ) -> None:
        """Batch modify labels on multiple messages.

        Uses Gmail API messages.batchModify with a maximum of 100
        messages per batch call to minimize API quota usage.

        Args:
            access_token: OAuth2 access token.
            message_ids: List of Gmail message IDs to modify.
            add_labels: Label IDs to add.
            remove_labels: Label IDs to remove.

        Raises:
            GmailFetchError: If the API call fails after retries.
            httpx.HTTPStatusError: If 401 (for token refresh handling).
        """
        add_labels = add_labels or []
        remove_labels = remove_labels or []

        # Split into batches of 100
        batch_size = 100
        for i in range(0, len(message_ids), batch_size):
            batch = message_ids[i : i + batch_size]

            async def _request(batch_ids=batch):
                response = await self._http_client.post(
                    f"{GMAIL_API_BASE}messages/batchModify",
                    headers=self._auth_headers(access_token),
                    json={
                        "ids": batch_ids,
                        "addLabelIds": add_labels,
                        "removeLabelIds": remove_labels,
                    },
                )
                response.raise_for_status()
                return None

            try:
                await self.retry_with_backoff(_request, quota_units=50)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 401:
                    raise
                raise GmailFetchError(
                    f"Failed to batch modify labels: {exc}"
                ) from exc

    async def create_label(
        self, access_token: str, label_name: str
    ) -> str:
        """Create a new Gmail label.

        Args:
            access_token: OAuth2 access token.
            label_name: The display name for the label (e.g., "VroomHR/processed").

        Returns:
            The Gmail label ID of the created label.

        Raises:
            GmailFetchError: If the API call fails after retries.
            httpx.HTTPStatusError: If 401 (for token refresh handling).
        """
        async def _request():
            response = await self._http_client.post(
                f"{GMAIL_API_BASE}labels",
                headers=self._auth_headers(access_token),
                json={
                    "name": label_name,
                    "labelListVisibility": "labelShow",
                    "messageListVisibility": "show",
                },
            )
            response.raise_for_status()
            return response.json()

        try:
            data = await self.retry_with_backoff(_request, quota_units=5)
            return data.get("id", "")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise
            raise GmailFetchError(
                f"Failed to create label '{label_name}': {exc}"
            ) from exc

    async def list_labels(self, access_token: str) -> list[GmailLabel]:
        """List all Gmail labels for the authenticated user.

        Args:
            access_token: OAuth2 access token.

        Returns:
            List of GmailLabel objects.

        Raises:
            GmailFetchError: If the API call fails after retries.
            httpx.HTTPStatusError: If 401 (for token refresh handling).
        """
        async def _request():
            response = await self._http_client.get(
                f"{GMAIL_API_BASE}labels",
                headers=self._auth_headers(access_token),
            )
            response.raise_for_status()
            return response.json()

        try:
            data = await self.retry_with_backoff(_request, quota_units=5)
            labels = []
            for label_data in data.get("labels", []):
                labels.append(
                    GmailLabel(
                        id=label_data.get("id", ""),
                        name=label_data.get("name", ""),
                        type=label_data.get("type", "user"),
                    )
                )
            return labels
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise
            raise GmailFetchError(
                f"Failed to list labels: {exc}"
            ) from exc

    async def revoke_token(self, token: str) -> bool:
        """Revoke a Gmail OAuth2 token via Google's revocation endpoint.

        Args:
            token: The access or refresh token to revoke.

        Returns:
            True if revocation succeeded, False if it failed or timed out.
        """
        try:
            response = await asyncio.wait_for(
                self._http_client.post(
                    GOOGLE_REVOKE_URL,
                    params={"token": token},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                ),
                timeout=float(self._settings.revocation_timeout_seconds),
            )
            return response.status_code == 200
        except (TimeoutError, httpx.HTTPError) as exc:
            logger.warning("Token revocation failed or timed out: %s", exc)
            return False

    async def refresh_access_token(
        self, refresh_token: str, client_id: str, client_secret: str
    ) -> tuple[str, datetime]:
        """Refresh a Gmail OAuth2 access token using the refresh token.

        Args:
            refresh_token: The OAuth2 refresh token.
            client_id: Google OAuth2 client ID.
            client_secret: Google OAuth2 client secret.

        Returns:
            Tuple of (new_access_token, expires_at_datetime).

        Raises:
            GmailFetchError: If the refresh request fails.
        """
        try:
            response = await asyncio.wait_for(
                self._http_client.post(
                    GOOGLE_TOKEN_URL,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": client_id,
                        "client_secret": client_secret,
                    },
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded"
                    },
                ),
                timeout=float(self._settings.api_timeout_seconds),
            )
            response.raise_for_status()
            data = response.json()

            access_token = data["access_token"]
            expires_in = data.get("expires_in", 3600)
            expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
            return (access_token, expires_at)
        except (
            TimeoutError,
            httpx.HTTPError,
            KeyError,
        ) as exc:
            raise GmailFetchError(
                f"Failed to refresh access token: {exc}"
            ) from exc
