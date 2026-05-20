"""Application service for composing and sending emails via Gmail API.

Handles email composition (MIME message construction), input validation,
sending via GmailAdapter with token refresh on 401, and persisting sent
message metadata to the EmailRepository for audit and tracking.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import TYPE_CHECKING
from uuid import UUID

import httpx

from src.modules.gmail.domain.exceptions import (
    GmailNotConnectedException,
    GmailSendFailedException,
)
from src.modules.gmail.infrastructure.config import GmailSettings

if TYPE_CHECKING:
    from src.modules.gmail.infrastructure.audit_logger import AuditLogger
    from src.modules.gmail.infrastructure.email_repository import EmailRepository
    from src.modules.gmail.infrastructure.gmail_adapter import GmailAdapter
    from src.modules.identity.infrastructure.crypto_utils import CryptoUtils
    from src.modules.identity.infrastructure.oauth_grant_repository import (
        OAuthGrantRepository,
    )

logger = logging.getLogger(__name__)


@dataclass
class AttachmentData:
    """Represents an email attachment to be sent.

    Attributes:
        filename: The original filename of the attachment.
        content: The raw binary content of the attachment.
        mime_type: The MIME type of the attachment (e.g., "application/pdf").
    """

    filename: str
    content: bytes
    mime_type: str


@dataclass
class SendEmailParams:
    """Parameters for sending an email.

    Attributes:
        to: List of recipient email addresses (1-50 required).
        subject: Email subject line (max 500 characters).
        body_html: HTML body content (optional if body_text provided).
        body_text: Plain text body content (optional if body_html provided).
        cc: List of CC recipient email addresses (optional, max 50).
        reply_to_message_id: Gmail message ID for threading (optional).
        attachments: List of attachments (optional, max 10, each ≤10MB).
    """

    to: list[str]
    subject: str
    body_html: str | None = None
    body_text: str | None = None
    cc: list[str] = field(default_factory=list)
    reply_to_message_id: str | None = None
    attachments: list[AttachmentData] = field(default_factory=list)


@dataclass
class SentEmailResponse:
    """Response after successfully sending an email.

    Attributes:
        message_id: The Gmail message ID of the sent email.
        thread_id: The Gmail thread ID of the sent email.
    """

    message_id: str
    thread_id: str


class SendService:
    """Composes and sends emails via Gmail API.

    Validates input parameters, constructs RFC 2822 MIME messages,
    sends via GmailAdapter (which handles retry with exponential backoff),
    handles 401 token refresh, and persists sent message metadata.

    Args:
        gmail_adapter: Gmail API adapter for sending messages.
        email_repo: Repository for persisting sent message metadata.
        oauth_grant_repo: Repository for OAuth grant lookup and token refresh.
        crypto: AES-256-GCM encryption utilities for token decryption.
        audit_logger: Structured audit logger for recording send operations.
        settings: Gmail module configuration.
        client_id: Google OAuth2 client ID for token refresh.
        client_secret: Google OAuth2 client secret for token refresh.
    """

    def __init__(
        self,
        gmail_adapter: GmailAdapter,
        email_repo: EmailRepository,
        oauth_grant_repo: OAuthGrantRepository,
        crypto: CryptoUtils,
        audit_logger: AuditLogger,
        settings: GmailSettings,
        client_id: str,
        client_secret: str,
    ) -> None:
        """Initialize SendService with dependencies.

        Args:
            gmail_adapter: Gmail API adapter instance.
            email_repo: Email message repository instance.
            oauth_grant_repo: OAuth grant repository instance.
            crypto: Encryption utilities instance.
            audit_logger: Audit logger instance.
            settings: Gmail module configuration.
            client_id: Google OAuth2 client ID.
            client_secret: Google OAuth2 client secret.
        """
        self._gmail_adapter = gmail_adapter
        self._email_repo = email_repo
        self._oauth_grant_repo = oauth_grant_repo
        self._crypto = crypto
        self._audit_logger = audit_logger
        self._settings = settings
        self._client_id = client_id
        self._client_secret = client_secret

    async def send_email(
        self, user_id: UUID, params: SendEmailParams
    ) -> SentEmailResponse:
        """Send an email via Gmail API on behalf of the user.

        Validates input parameters, verifies Gmail connection status,
        builds the MIME message, sends via GmailAdapter, handles token
        refresh on 401, stores sent message metadata, and logs the
        operation for audit.

        Args:
            user_id: The UUID of the user sending the email.
            params: The email parameters (recipients, subject, body, etc.).

        Returns:
            SentEmailResponse with the Gmail message_id and thread_id.

        Raises:
            GmailNotConnectedException: If the user's Gmail is not connected.
            GmailSendFailedException: If sending fails after retries.
            ValueError: If input parameters are invalid.
        """
        # Step 1: Validate input parameters
        self._validate_params(params)

        # Step 2: Get access token (verify connection)
        access_token = await self._get_access_token(user_id)

        # Step 3: Build MIME message
        mime_bytes = self._build_mime_message(params)

        # Step 4: Send via GmailAdapter with token refresh on 401
        try:
            sent_info = await self._gmail_adapter.send_message(
                access_token, mime_bytes
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                # Attempt token refresh and retry once
                refreshed_token = await self._handle_token_refresh(user_id)
                if refreshed_token is None:
                    raise GmailSendFailedException(
                        "Token refresh failed, Gmail connection expired"
                    ) from exc
                sent_info = await self._gmail_adapter.send_message(
                    refreshed_token, mime_bytes
                )
            else:
                raise

        # Step 5: Store sent message metadata
        await self._store_sent_metadata(user_id, params, sent_info)

        # Step 6: Audit log the send operation
        await self._audit_logger.log_send(
            user_id=user_id,
            recipient_emails=params.to + params.cc,
            subject=params.subject,
        )

        return SentEmailResponse(
            message_id=sent_info.message_id,
            thread_id=sent_info.thread_id,
        )

    def _validate_params(self, params: SendEmailParams) -> None:
        """Validate send email parameters.

        Checks:
        - to: 1-50 recipients required
        - cc: max 50 recipients
        - subject: max 500 characters
        - At least one of body_html or body_text must be provided
        - attachments: max 10, each ≤10MB

        Args:
            params: The email parameters to validate.

        Raises:
            ValueError: If any validation rule is violated.
        """
        # Validate recipients (to)
        if not params.to:
            raise ValueError("At least one recipient (to) is required")
        if len(params.to) > 50:
            raise ValueError(
                f"Maximum 50 recipients allowed in 'to', got {len(params.to)}"
            )

        # Validate CC
        if len(params.cc) > 50:
            raise ValueError(
                f"Maximum 50 recipients allowed in 'cc', got {len(params.cc)}"
            )

        # Validate subject
        if len(params.subject) > 500:
            raise ValueError(
                f"Subject must not exceed 500 characters, got {len(params.subject)}"
            )

        # Validate body
        if not params.body_html and not params.body_text:
            raise ValueError(
                "At least one of body_html or body_text must be provided"
            )

        # Validate attachments
        if len(params.attachments) > 10:
            raise ValueError(
                f"Maximum 10 attachments allowed, got {len(params.attachments)}"
            )

        max_size = self._settings.max_attachment_size_bytes
        for i, attachment in enumerate(params.attachments):
            if len(attachment.content) > max_size:
                raise ValueError(
                    f"Attachment '{attachment.filename}' (index {i}) exceeds "
                    f"maximum size of {max_size} bytes "
                    f"(got {len(attachment.content)} bytes)"
                )

    def _build_mime_message(self, params: SendEmailParams) -> bytes:
        """Build an RFC 2822 MIME message from send parameters.

        Constructs a multipart/mixed message containing:
        - A multipart/alternative section with text/plain and/or text/html
        - Attachment parts (if any)

        Sets In-Reply-To and References headers when reply_to_message_id
        is provided to maintain email thread continuity.

        Args:
            params: The email parameters to build the message from.

        Returns:
            The MIME message as bytes (RFC 2822 format).
        """
        # Create the top-level message
        if params.attachments:
            msg = MIMEMultipart("mixed")
            # Create alternative part for body
            body_part = MIMEMultipart("alternative")
            if params.body_text:
                body_part.attach(MIMEText(params.body_text, "plain", "utf-8"))
            if params.body_html:
                body_part.attach(MIMEText(params.body_html, "html", "utf-8"))
            msg.attach(body_part)

            # Attach files
            for attachment in params.attachments:
                att_part = MIMEApplication(
                    attachment.content, Name=attachment.filename
                )
                att_part.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=attachment.filename,
                )
                att_part.set_type(attachment.mime_type)
                msg.attach(att_part)
        else:
            # No attachments — use multipart/alternative for body
            if params.body_html and params.body_text:
                msg = MIMEMultipart("alternative")
                msg.attach(MIMEText(params.body_text, "plain", "utf-8"))
                msg.attach(MIMEText(params.body_html, "html", "utf-8"))
            elif params.body_html:
                msg = MIMEMultipart("alternative")
                msg.attach(MIMEText(params.body_html, "html", "utf-8"))
            else:
                msg = MIMEMultipart("alternative")
                msg.attach(MIMEText(params.body_text or "", "plain", "utf-8"))

        # Set headers
        msg["To"] = ", ".join(params.to)
        if params.cc:
            msg["Cc"] = ", ".join(params.cc)
        msg["Subject"] = params.subject

        # Set threading headers for replies
        if params.reply_to_message_id:
            msg["In-Reply-To"] = params.reply_to_message_id
            msg["References"] = params.reply_to_message_id

        return msg.as_bytes()

    async def _get_access_token(self, user_id: UUID) -> str:
        """Retrieve and decrypt the user's Gmail access token.

        Verifies that the user has a valid OAuth grant with Gmail scopes
        and a non-expired token.

        Args:
            user_id: The UUID of the user.

        Returns:
            The decrypted access token string.

        Raises:
            GmailNotConnectedException: If no valid grant exists or token expired.
        """
        grant = await self._oauth_grant_repo.get_by_user_id(user_id)

        if grant is None:
            raise GmailNotConnectedException(
                "Gmail is not connected for this user"
            )

        if not grant.is_valid:
            raise GmailNotConnectedException(
                "Gmail connection is invalid (token expired)"
            )

        if grant.token_expires_at <= datetime.now(UTC):
            # Token expired — attempt refresh
            refreshed_token = await self._handle_token_refresh(user_id)
            if refreshed_token is None:
                raise GmailNotConnectedException(
                    "Gmail access token expired and refresh failed"
                )
            return refreshed_token

        return self._crypto.decrypt(grant.access_token_enc)

    async def _handle_token_refresh(self, user_id: UUID) -> str | None:
        """Attempt to refresh the user's Gmail access token.

        Decrypts the refresh token, calls Google's token endpoint,
        encrypts and stores the new access token, and returns it.
        On failure, marks the OAuth grant as invalid.

        Args:
            user_id: The UUID of the user whose token to refresh.

        Returns:
            The new decrypted access token, or None if refresh failed.
        """
        try:
            grant = await self._oauth_grant_repo.get_by_user_id(user_id)
            if grant is None:
                return None

            refresh_token = self._crypto.decrypt(grant.refresh_token_enc)
            if not refresh_token:
                await self._oauth_grant_repo.mark_invalid(user_id)
                return None

            new_access_token, expires_at = (
                await self._gmail_adapter.refresh_access_token(
                    refresh_token=refresh_token,
                    client_id=self._client_id,
                    client_secret=self._client_secret,
                )
            )

            # Encrypt and store the new access token
            encrypted_access = self._crypto.encrypt(new_access_token)
            await self._oauth_grant_repo.upsert(
                user_id=user_id,
                access_token_enc=encrypted_access,
                refresh_token_enc=grant.refresh_token_enc,
                scopes=grant.scopes,
                token_expires_at=expires_at,
            )

            return new_access_token
        except Exception as exc:
            logger.error(
                "Token refresh failed for user %s: %s", user_id, exc
            )
            await self._oauth_grant_repo.mark_invalid(user_id)
            return None

    async def _store_sent_metadata(
        self,
        user_id: UUID,
        params: SendEmailParams,
        sent_info,
    ) -> None:
        """Store sent message metadata in the EmailRepository.

        Creates an EmailMessage record with the sent message details
        for tracking and audit purposes.

        Args:
            user_id: The UUID of the user who sent the email.
            params: The original send parameters.
            sent_info: The SentMessageInfo returned by GmailAdapter.
        """
        from src.modules.gmail.domain.entities import EmailMessage

        sent_message = EmailMessage(
            user_id=user_id,
            gmail_message_id=sent_info.message_id,
            gmail_thread_id=sent_info.thread_id,
            subject=params.subject[:998],
            sender_email="",  # Sender is the authenticated user
            sender_name="",
            recipient_emails=params.to[:50],
            cc_emails=params.cc[:50],
            received_at=datetime.now(UTC),
            snippet="",
            label_ids=["SENT"],
            has_attachments=len(params.attachments) > 0,
        )

        try:
            await self._email_repo.batch_upsert([sent_message])
        except Exception as exc:
            # Don't fail the send operation if metadata storage fails
            logger.error(
                "Failed to store sent message metadata for gmail_message_id=%s: %s",
                sent_info.message_id,
                exc,
            )
