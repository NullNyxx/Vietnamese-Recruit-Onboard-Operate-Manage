"""Structured audit logging for Gmail operations.

Persists GmailAuditLog records to the database for compliance and
debugging. Ensures no email body content, snippets, or attachment
binary data is ever logged. Handles logging failures gracefully so
that Gmail operations are never blocked by audit failures.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.gmail.domain.entities import GmailAuditLog
from src.modules.gmail.infrastructure.config import GmailSettings

logger = logging.getLogger(__name__)

# Fields that must NEVER appear in audit log metadata
_FORBIDDEN_METADATA_KEYS = frozenset(
    {
        "body",
        "body_html",
        "body_text",
        "snippet",
        "preview",
        "raw_payload",
        "raw_payload_enc",
        "attachment_data",
        "attachment_binary",
        "content",
    }
)


class AuditLogger:
    """Logs Gmail operations for audit trail.

    Persists structured audit entries to the gmail_audit_logs table.
    All methods are designed to never raise exceptions — if logging
    fails, the error is recorded via Python's standard logging and
    the calling operation proceeds uninterrupted.

    Attributes:
        session: Async SQLAlchemy session for database persistence.
        settings: Gmail module configuration (audit_subject_max_length, etc.).
    """

    def __init__(self, session: AsyncSession, settings: GmailSettings) -> None:
        """Initialize the audit logger.

        Args:
            session: An async SQLAlchemy session for persisting audit records.
            settings: Gmail module settings for audit configuration.
        """
        self.session = session
        self.settings = settings

    async def log_operation(
        self,
        operation_type: str,
        user_id: UUID,
        message_count: int = 0,
        success: bool = True,
        metadata: dict | None = None,
    ) -> None:
        """Log a Gmail API operation to the audit trail.

        Records operation details including type, user, message count,
        and success status. Any provided metadata is sanitized to remove
        forbidden fields (body, snippet, attachment data).

        Args:
            operation_type: The type of operation (fetch, send, label_modify,
                connect, disconnect).
            user_id: The UUID of the user performing the operation.
            message_count: Number of messages affected (0 for single-message ops).
            success: Whether the operation succeeded.
            metadata: Optional additional context. Forbidden keys are stripped.
        """
        try:
            sanitized_metadata = self._sanitize_metadata(metadata)

            audit_entry = GmailAuditLog(
                user_id=user_id,
                operation_type=operation_type,
                message_count=message_count,
                success=success,
                metadata_=sanitized_metadata,
                created_at=datetime.now(UTC),
            )

            self.session.add(audit_entry)
            await self.session.flush()
        except Exception as exc:
            logger.error(
                "Audit logging failed for operation_type=%s user_id=%s timestamp=%s reason=%s",
                operation_type,
                user_id,
                datetime.now(UTC).isoformat(),
                str(exc),
            )

    async def log_send(
        self,
        user_id: UUID,
        recipient_emails: list[str],
        subject: str,
        template_name: str | None = None,
    ) -> None:
        """Log an email send operation to the audit trail.

        Records send-specific details: recipients (truncated to 50),
        subject (truncated to configured max length), template name,
        and sent timestamp.

        Args:
            user_id: The UUID of the user sending the email.
            recipient_emails: List of recipient email addresses.
            subject: The email subject line.
            template_name: Optional template name used for the email.
        """
        try:
            # Truncate recipients to max 50
            truncated_recipients = recipient_emails[:50]
            recipient_count = len(recipient_emails)

            # Truncate subject to configured max length
            max_subject_len = self.settings.audit_subject_max_length
            truncated_subject = subject[:max_subject_len] if subject else ""

            send_metadata: dict = {
                "recipient_emails": truncated_recipients,
                "subject": truncated_subject,
                "sent_at": datetime.now(UTC).isoformat(),
            }

            if recipient_count > 50:
                send_metadata["recipient_count"] = recipient_count
                send_metadata["recipients_truncated"] = True

            if template_name is not None:
                send_metadata["template_name"] = template_name

            audit_entry = GmailAuditLog(
                user_id=user_id,
                operation_type="send",
                message_count=1,
                success=True,
                metadata_=send_metadata,
                created_at=datetime.now(UTC),
            )

            self.session.add(audit_entry)
            await self.session.flush()
        except Exception as exc:
            logger.error(
                "Audit logging failed for operation_type=send user_id=%s timestamp=%s reason=%s",
                user_id,
                datetime.now(UTC).isoformat(),
                str(exc),
            )

    def _sanitize_metadata(self, metadata: dict | None) -> dict | None:
        """Remove forbidden fields from metadata to protect privacy.

        Strips any keys that could contain email body content, snippets,
        or attachment binary data.

        Args:
            metadata: The raw metadata dictionary to sanitize.

        Returns:
            A sanitized copy of the metadata, or None if input is None.
        """
        if metadata is None:
            return None

        return {
            key: value
            for key, value in metadata.items()
            if key.lower() not in _FORBIDDEN_METADATA_KEYS
        }
