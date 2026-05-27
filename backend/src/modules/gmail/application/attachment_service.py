"""Application service for email attachment fetching and validation.

Handles downloading attachments from Gmail API, validating MIME types
and file sizes against configured limits, and tracking fetch/skip counts
for audit and reporting purposes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID

from src.modules.gmail.infrastructure.config import GmailSettings

if TYPE_CHECKING:
    from src.modules.gmail.infrastructure.audit_logger import AuditLogger
    from src.modules.gmail.infrastructure.gmail_adapter import GmailAdapter

logger = logging.getLogger(__name__)


@dataclass
class AttachmentMetadata:
    """Input metadata for an attachment to be fetched.

    Attributes:
        attachment_id: Gmail attachment ID.
        filename: Original filename of the attachment.
        mime_type: MIME type of the attachment.
        size_bytes: Size of the attachment in bytes.
    """

    attachment_id: str
    filename: str
    mime_type: str
    size_bytes: int


@dataclass
class FetchedAttachment:
    """A successfully fetched attachment with its binary data.

    Attributes:
        attachment_id: Gmail attachment ID.
        filename: Original filename of the attachment.
        mime_type: MIME type of the attachment.
        size_bytes: Size of the attachment in bytes.
        data: Raw binary data of the attachment.
    """

    attachment_id: str
    filename: str
    mime_type: str
    size_bytes: int
    data: bytes


@dataclass
class AttachmentResult:
    """Result of processing attachments for an email.

    Attributes:
        fetched: List of successfully fetched attachments.
        fetched_count: Number of attachments successfully fetched.
        skipped_count: Number of attachments skipped (invalid or fetch failed).
        total_count: Total number of attachments attempted.
    """

    fetched: list[FetchedAttachment] = field(default_factory=list)
    fetched_count: int = 0
    skipped_count: int = 0
    total_count: int = 0


class AttachmentService:
    """Fetches and validates email attachments.

    Validates attachments against configured MIME type allowlist and
    maximum file size, then fetches valid attachments via the Gmail
    adapter. Skips invalid or failed attachments gracefully, logging
    warnings without failing the overall operation.

    Args:
        gmail_adapter: Gmail API adapter for fetching attachment data.
        settings: Gmail module configuration (attachment limits, allowed types).
        audit_logger: Structured audit logger for recording operations.
    """

    def __init__(
        self,
        gmail_adapter: GmailAdapter,
        settings: GmailSettings,
        audit_logger: AuditLogger,
    ) -> None:
        """Initialize AttachmentService with dependencies.

        Args:
            gmail_adapter: Gmail API adapter instance.
            settings: Gmail module configuration.
            audit_logger: Audit logger instance.
        """
        self._gmail_adapter = gmail_adapter
        self._settings = settings
        self._audit_logger = audit_logger

    def validate_attachment(self, mime_type: str, size_bytes: int) -> bool:
        """Validate an attachment against allowed MIME types and size limit.

        Checks that the MIME type is in the configured allowed list and
        that the file size does not exceed the configured maximum.

        Args:
            mime_type: The MIME type of the attachment.
            size_bytes: The size of the attachment in bytes.

        Returns:
            True if the attachment passes both MIME type and size validation,
            False otherwise.
        """
        if mime_type not in self._settings.allowed_mime_types:
            return False
        if size_bytes > self._settings.max_attachment_size_bytes:
            return False
        return True

    async def fetch_attachments(
        self,
        user_id: UUID,
        message_id: str,
        access_token: str,
        attachments: list[AttachmentMetadata],
    ) -> AttachmentResult:
        """Fetch and validate attachments for an email message.

        Processes up to 20 attachments per email. Each attachment is
        validated for MIME type and size before fetching. Invalid
        attachments are skipped with a warning log. Fetch failures
        are also skipped gracefully.

        Args:
            user_id: The UUID of the user who owns the email.
            message_id: The Gmail message ID containing the attachments.
            access_token: OAuth2 access token for Gmail API calls.
            attachments: List of attachment metadata to process.

        Returns:
            AttachmentResult with fetched attachments and counts.
        """
        max_attachments = self._settings.max_attachments_per_email
        limited_attachments = attachments[:max_attachments]

        result = AttachmentResult(total_count=len(limited_attachments))
        fetched_count = 0
        skipped_count = 0

        for attachment in limited_attachments:
            # Validate MIME type and size
            if not self.validate_attachment(attachment.mime_type, attachment.size_bytes):
                skipped_count += 1
                if attachment.mime_type not in self._settings.allowed_mime_types:
                    logger.warning(
                        "Skipping attachment '%s' for message %s: "
                        "MIME type '%s' not in allowed list",
                        attachment.filename,
                        message_id,
                        attachment.mime_type,
                    )
                else:
                    logger.warning(
                        "Skipping attachment '%s' for message %s: "
                        "size %d bytes exceeds maximum %d bytes",
                        attachment.filename,
                        message_id,
                        attachment.size_bytes,
                        self._settings.max_attachment_size_bytes,
                    )
                continue

            # Fetch attachment data via Gmail adapter (retry is built into adapter)
            try:
                data = await self._gmail_adapter.get_attachment(
                    access_token=access_token,
                    message_id=message_id,
                    attachment_id=attachment.attachment_id,
                )
                result.fetched.append(
                    FetchedAttachment(
                        attachment_id=attachment.attachment_id,
                        filename=attachment.filename,
                        mime_type=attachment.mime_type,
                        size_bytes=attachment.size_bytes,
                        data=data,
                    )
                )
                fetched_count += 1
            except Exception as exc:
                skipped_count += 1
                logger.error(
                    "Failed to fetch attachment '%s' (ID: %s) for message %s after retries: %s",
                    attachment.filename,
                    attachment.attachment_id,
                    message_id,
                    exc,
                )

        result.fetched_count = fetched_count
        result.skipped_count = skipped_count

        # Log the operation
        await self._audit_logger.log_operation(
            operation_type="attachment_fetch",
            user_id=user_id,
            message_count=fetched_count,
            success=skipped_count == 0,
            metadata={
                "message_id": message_id,
                "fetched_count": fetched_count,
                "skipped_count": skipped_count,
                "total_count": result.total_count,
            },
        )

        return result
