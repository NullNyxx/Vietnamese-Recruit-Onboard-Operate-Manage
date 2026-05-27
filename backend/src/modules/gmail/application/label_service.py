"""Application service for Gmail label management.

Manages VroomHR label lifecycle on Gmail: initialization, assignment,
removal, and namespace validation. All label operations are restricted
to the "VroomHR/" namespace to prevent accidental modification of
user-created Gmail labels.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING
from uuid import UUID

from src.modules.gmail.domain.exceptions import (
    GmailFetchError,
    LabelNamespaceViolationException,
)
from src.modules.gmail.infrastructure.config import GmailSettings

if TYPE_CHECKING:
    from src.modules.gmail.infrastructure.audit_logger import AuditLogger
    from src.modules.gmail.infrastructure.gmail_adapter import GmailAdapter
    from src.modules.gmail.infrastructure.label_repository import LabelRepository

logger = logging.getLogger(__name__)


class LabelService:
    """Manages VroomHR Gmail labels.

    Handles label initialization (creating required labels on Gmail),
    adding/removing labels from messages, and enforcing the VroomHR/
    namespace constraint on all label operations.

    Args:
        gmail_adapter: Gmail API adapter for label CRUD and modification.
        label_repo: Repository for persisting label name-to-ID mappings.
        settings: Gmail module configuration (label_prefix, required_labels, retry settings).
        audit_logger: Structured audit logger for recording label operations.
    """

    def __init__(
        self,
        gmail_adapter: GmailAdapter,
        label_repo: LabelRepository,
        settings: GmailSettings,
        audit_logger: AuditLogger,
    ) -> None:
        """Initialize LabelService with dependencies.

        Args:
            gmail_adapter: Gmail API adapter instance.
            label_repo: Label mapping repository instance.
            settings: Gmail module configuration.
            audit_logger: Audit logger instance.
        """
        self._gmail_adapter = gmail_adapter
        self._label_repo = label_repo
        self._settings = settings
        self._audit_logger = audit_logger

    async def initialize_labels(self, user_id: UUID, access_token: str) -> None:
        """Create required VroomHR labels on Gmail if they do not exist.

        Lists existing Gmail labels, checks which required labels already
        exist (reusing their IDs), and creates any missing labels with
        retry logic (3 retries, exponential backoff: 1s, 2s, 4s).
        Stores all label name-to-ID mappings in the database.

        Args:
            user_id: The UUID of the user whose Gmail labels to initialize.
            access_token: OAuth2 access token for Gmail API calls.

        Raises:
            GmailFetchError: If listing labels fails after retries.
        """
        prefix = self._settings.label_prefix
        required_labels = self._settings.required_labels

        # Step 1: List existing Gmail labels
        existing_labels = await self._gmail_adapter.list_labels(access_token)
        existing_label_map = {label.name: label.id for label in existing_labels}

        # Step 2: For each required label, check existence or create
        mappings: list[dict[str, str]] = []
        all_succeeded = True

        for label_suffix in required_labels:
            full_label_name = f"{prefix}{label_suffix}"

            if full_label_name in existing_label_map:
                # Reuse existing label ID
                gmail_label_id = existing_label_map[full_label_name]
                logger.info(
                    "Reusing existing label '%s' (ID: %s) for user %s",
                    full_label_name,
                    gmail_label_id,
                    user_id,
                )
            else:
                # Create label with retry logic
                gmail_label_id = await self._create_label_with_retry(access_token, full_label_name)
                if gmail_label_id is None:
                    all_succeeded = False
                    logger.error(
                        "Failed to create label '%s' for user %s after retries",
                        full_label_name,
                        user_id,
                    )
                    continue

                logger.info(
                    "Created label '%s' (ID: %s) for user %s",
                    full_label_name,
                    gmail_label_id,
                    user_id,
                )

            mappings.append({"label_name": full_label_name, "gmail_label_id": gmail_label_id})

        # Step 3: Store mappings in the database
        if mappings:
            await self._label_repo.upsert_mappings(user_id, mappings)

        # Log the operation
        await self._audit_logger.log_operation(
            operation_type="label_initialize",
            user_id=user_id,
            message_count=len(mappings),
            success=all_succeeded,
            metadata={
                "labels_initialized": [m["label_name"] for m in mappings],
                "labels_failed": [
                    f"{prefix}{s}"
                    for s in required_labels
                    if f"{prefix}{s}" not in {m["label_name"] for m in mappings}
                ],
            },
        )

    async def _create_label_with_retry(self, access_token: str, label_name: str) -> str | None:
        """Create a Gmail label with exponential backoff retry.

        Retries up to 3 times with delays of 1s, 2s, 4s on failure.

        Args:
            access_token: OAuth2 access token for Gmail API calls.
            label_name: The full label name to create (e.g., "VroomHR/processed").

        Returns:
            The Gmail label ID if creation succeeded, None if all retries failed.
        """
        max_retries = self._settings.max_retries
        base_delay = self._settings.retry_backoff_base

        for attempt in range(max_retries):
            try:
                gmail_label_id = await self._gmail_adapter.create_label(access_token, label_name)
                return gmail_label_id
            except Exception as exc:
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    logger.warning(
                        "Label creation failed for '%s' (attempt %d/%d), retrying in %.1fs: %s",
                        label_name,
                        attempt + 1,
                        max_retries,
                        delay,
                        exc,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "Label creation failed for '%s' after %d attempts: %s",
                        label_name,
                        max_retries,
                        exc,
                    )

        return None

    async def add_label(
        self,
        user_id: UUID,
        message_id: str,
        label_name: str,
        access_token: str,
    ) -> None:
        """Add a VroomHR label to a Gmail message.

        Validates the label namespace, resolves the label name to a Gmail
        label ID, and applies it to the specified message.

        Args:
            user_id: The UUID of the user who owns the message.
            message_id: The Gmail message ID to label.
            label_name: The full label name (must start with "VroomHR/").
            access_token: OAuth2 access token for Gmail API calls.

        Raises:
            LabelNamespaceViolationException: If label_name is outside VroomHR/ namespace.
            GmailFetchError: If the Gmail API call fails after retries.
        """
        if not self.validate_namespace(label_name):
            raise LabelNamespaceViolationException(
                f"Label '{label_name}' is not within the VroomHR/ namespace"
            )

        gmail_label_id = await self._label_repo.get_label_id_by_name(user_id, label_name)
        if gmail_label_id is None:
            raise GmailFetchError(f"Label '{label_name}' not found in mappings for user {user_id}")

        await self._gmail_adapter.modify_labels(
            access_token=access_token,
            message_ids=[message_id],
            add_labels=[gmail_label_id],
            remove_labels=None,
        )

        await self._audit_logger.log_operation(
            operation_type="label_modify",
            user_id=user_id,
            message_count=1,
            success=True,
            metadata={
                "action": "add",
                "label_name": label_name,
                "message_id": message_id,
            },
        )

    async def remove_label(
        self,
        user_id: UUID,
        message_id: str,
        label_name: str,
        access_token: str,
    ) -> None:
        """Remove a VroomHR label from a Gmail message.

        Validates the label namespace, resolves the label name to a Gmail
        label ID, and removes it from the specified message.

        Args:
            user_id: The UUID of the user who owns the message.
            message_id: The Gmail message ID to unlabel.
            label_name: The full label name (must start with "VroomHR/").
            access_token: OAuth2 access token for Gmail API calls.

        Raises:
            LabelNamespaceViolationException: If label_name is outside VroomHR/ namespace.
            GmailFetchError: If the Gmail API call fails after retries.
        """
        if not self.validate_namespace(label_name):
            raise LabelNamespaceViolationException(
                f"Label '{label_name}' is not within the VroomHR/ namespace"
            )

        gmail_label_id = await self._label_repo.get_label_id_by_name(user_id, label_name)
        if gmail_label_id is None:
            raise GmailFetchError(f"Label '{label_name}' not found in mappings for user {user_id}")

        await self._gmail_adapter.modify_labels(
            access_token=access_token,
            message_ids=[message_id],
            add_labels=None,
            remove_labels=[gmail_label_id],
        )

        await self._audit_logger.log_operation(
            operation_type="label_modify",
            user_id=user_id,
            message_count=1,
            success=True,
            metadata={
                "action": "remove",
                "label_name": label_name,
                "message_id": message_id,
            },
        )

    async def batch_add_label(
        self,
        user_id: UUID,
        message_ids: list[str],
        label_name: str,
        access_token: str,
    ) -> None:
        """Add a VroomHR label to multiple Gmail messages in batch.

        Uses Gmail API batchModify to efficiently label up to 100 messages
        per API call. For lists exceeding 100 messages, the adapter
        automatically splits into multiple batch calls.

        Args:
            user_id: The UUID of the user who owns the messages.
            message_ids: List of Gmail message IDs to label.
            label_name: The full label name (must start with "VroomHR/").
            access_token: OAuth2 access token for Gmail API calls.

        Raises:
            LabelNamespaceViolationException: If label_name is outside VroomHR/ namespace.
            GmailFetchError: If the Gmail API call fails after retries.
        """
        if not self.validate_namespace(label_name):
            raise LabelNamespaceViolationException(
                f"Label '{label_name}' is not within the VroomHR/ namespace"
            )

        if not message_ids:
            return

        gmail_label_id = await self._label_repo.get_label_id_by_name(user_id, label_name)
        if gmail_label_id is None:
            raise GmailFetchError(f"Label '{label_name}' not found in mappings for user {user_id}")

        await self._gmail_adapter.batch_modify_labels(
            access_token=access_token,
            message_ids=message_ids,
            add_labels=[gmail_label_id],
            remove_labels=None,
        )

        await self._audit_logger.log_operation(
            operation_type="label_modify",
            user_id=user_id,
            message_count=len(message_ids),
            success=True,
            metadata={
                "action": "batch_add",
                "label_name": label_name,
                "message_count": len(message_ids),
            },
        )

    def validate_namespace(self, label_name: str) -> bool:
        """Validate that a label name is within the VroomHR/ namespace.

        All label operations must target labels starting with the configured
        label prefix (default "VroomHR/") to prevent accidental modification
        of user-created Gmail labels.

        Args:
            label_name: The label name to validate.

        Returns:
            True if the label name starts with the VroomHR/ prefix, False otherwise.
        """
        return label_name.startswith(self._settings.label_prefix)
