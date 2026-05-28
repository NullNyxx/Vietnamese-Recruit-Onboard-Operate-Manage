"""EmailSyncService for periodic and manual email synchronization.

Orchestrates email fetching from Gmail via polling (ARQ cron) and manual
sync triggers. Handles first-poll logic (7-day lookback), incremental sync
(history_id-based), token refresh on 401, partial failure handling, and
manual sync rate limiting via Redis.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

import httpx
import redis.asyncio as redis

from src.modules.gmail.domain.entities import EmailMessage, SyncCursor
from src.modules.gmail.domain.exceptions import (
    GmailNotConnectedException,
    RateLimitedException,
)
from src.modules.gmail.infrastructure.config import GmailSettings
from src.modules.identity.infrastructure.crypto_utils import CryptoUtils

if TYPE_CHECKING:
    from src.modules.gmail.infrastructure.audit_logger import AuditLogger
    from src.modules.gmail.infrastructure.email_repository import EmailRepository
    from src.modules.gmail.infrastructure.gmail_adapter import (
        GmailAdapter,
        GmailMessageMetadata,
    )
    from src.modules.gmail.infrastructure.sync_cursor_repository import (
        SyncCursorRepository,
    )
    from src.modules.identity.infrastructure.oauth_grant_repository import (
        OAuthGrantRepository,
    )

logger = logging.getLogger(__name__)


class EmailSyncService:
    """Orchestrates email fetching from Gmail.

    Handles both scheduled polling (via ARQ cron) and manual sync triggers.
    Implements first-poll logic (fetch last 7 days), incremental sync
    (history_id-based), token refresh on 401, partial failure handling,
    and manual sync rate limiting.

    Args:
        gmail_adapter: Gmail API adapter for fetching messages.
        email_repo: Repository for persisting email messages.
        sync_cursor_repo: Repository for sync cursor management.
        oauth_grant_repo: Repository for OAuth grant token access.
        crypto: AES-256-GCM encryption utilities for token decryption.
        audit_logger: Structured audit logger for operation tracking.
        settings: Gmail module configuration.
        redis_client: Async Redis client for manual sync rate limiting.
        client_id: Google OAuth2 client ID for token refresh.
        client_secret: Google OAuth2 client secret for token refresh.
    """

    def __init__(
        self,
        gmail_adapter: GmailAdapter,
        email_repo: EmailRepository,
        sync_cursor_repo: SyncCursorRepository,
        oauth_grant_repo: OAuthGrantRepository,
        crypto: CryptoUtils,
        audit_logger: AuditLogger,
        settings: GmailSettings,
        redis_client: redis.Redis,
        client_id: str,
        client_secret: str,
    ) -> None:
        """Initialize EmailSyncService with dependencies.

        Args:
            gmail_adapter: Gmail API adapter for fetching messages.
            email_repo: Repository for persisting email messages.
            sync_cursor_repo: Repository for sync cursor management.
            oauth_grant_repo: Repository for OAuth grant token access.
            crypto: AES-256-GCM encryption utilities for token decryption.
            audit_logger: Structured audit logger for operation tracking.
            settings: Gmail module configuration.
            redis_client: Async Redis client for manual sync rate limiting.
            client_id: Google OAuth2 client ID for token refresh.
            client_secret: Google OAuth2 client secret for token refresh.
        """
        self._gmail_adapter = gmail_adapter
        self._email_repo = email_repo
        self._sync_cursor_repo = sync_cursor_repo
        self._oauth_grant_repo = oauth_grant_repo
        self._crypto = crypto
        self._audit_logger = audit_logger
        self._settings = settings
        self._redis = redis_client
        self._client_id = client_id
        self._client_secret = client_secret

    async def poll_emails(self, user_id: UUID) -> int:
        """Execute a poll cycle to fetch new emails from Gmail.

        Called by the ARQ cron job on schedule. Checks connection status,
        retrieves the access token, fetches emails (initial or incremental),
        and persists them. Handles 401 errors by attempting token refresh.

        Args:
            user_id: The UUID of the user whose emails to poll.

        Returns:
            The number of new emails successfully persisted.

        Raises:
            GmailNotConnectedException: If the user's Gmail is not connected.
        """
        # Get the OAuth grant to verify connection and get access token
        grant = await self._oauth_grant_repo.get_by_user_id(user_id)
        if grant is None or not grant.is_valid:
            raise GmailNotConnectedException()

        # Decrypt access token
        access_token = self._crypto.decrypt(grant.access_token_enc)

        # Get current sync cursor
        cursor = await self._sync_cursor_repo.get_cursor(user_id)

        try:
            count = await self._fetch_and_persist(user_id, access_token, cursor)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                # Attempt token refresh and retry once
                new_access_token = await self._handle_token_refresh(user_id)
                if new_access_token is None:
                    # Token refresh failed — grant already marked invalid
                    return 0
                # Retry with refreshed token
                count = await self._fetch_and_persist(user_id, new_access_token, cursor)
            else:
                raise

        # Log the sync operation
        await self._audit_logger.log_operation(
            operation_type="fetch",
            user_id=user_id,
            message_count=count,
            success=True,
            metadata={"sync_type": "poll"},
        )

        return count

    async def manual_sync(self, user_id: UUID) -> int:
        """Trigger an immediate email sync outside the regular schedule.

        Applies rate limiting (1 request per 30 seconds per user) via Redis.
        Uses the same fetch logic as poll_emails.

        Args:
            user_id: The UUID of the user requesting manual sync.

        Returns:
            The number of new emails successfully fetched.

        Raises:
            GmailNotConnectedException: If the user's Gmail is not connected.
            RateLimitedException: If called within 30 seconds of last manual sync.
        """
        # Check rate limit via Redis
        await self._check_manual_sync_rate_limit(user_id)

        # Get the OAuth grant to verify connection and get access token
        grant = await self._oauth_grant_repo.get_by_user_id(user_id)
        if grant is None or not grant.is_valid:
            raise GmailNotConnectedException()

        # Decrypt access token
        access_token = self._crypto.decrypt(grant.access_token_enc)

        # Get current sync cursor
        cursor = await self._sync_cursor_repo.get_cursor(user_id)

        try:
            count = await self._fetch_and_persist(user_id, access_token, cursor)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                # Attempt token refresh and retry once
                new_access_token = await self._handle_token_refresh(user_id)
                if new_access_token is None:
                    return 0
                count = await self._fetch_and_persist(user_id, new_access_token, cursor)
            else:
                raise

        # Record the manual sync timestamp in Redis
        await self._record_manual_sync_timestamp(user_id)

        # Log the sync operation
        await self._audit_logger.log_operation(
            operation_type="fetch",
            user_id=user_id,
            message_count=count,
            success=True,
            metadata={"sync_type": "manual"},
        )

        return count

    async def _fetch_and_persist(
        self, user_id: UUID, access_token: str, cursor: SyncCursor | None
    ) -> int:
        """Fetch emails from Gmail and persist them to the database.

        Implements two strategies:
        - First poll (no cursor): fetch emails from last 7 days using search query.
        - Incremental sync (cursor exists): fetch emails newer than stored history_id.

        Handles partial failures: saves successful messages, increments retry
        count for failed ones, and marks messages with 5+ failures as permanent.

        Args:
            user_id: The UUID of the user whose emails to fetch.
            access_token: Decrypted Gmail OAuth2 access token.
            cursor: The current sync cursor, or None for first poll.

        Returns:
            The number of emails successfully persisted.
        """

        latest_history_id: str | None = None

        if cursor is None:
            # First poll: fetch emails from last N days
            days_ago = datetime.now(UTC) - timedelta(days=self._settings.initial_sync_days)
            epoch_seconds = int(days_ago.timestamp())
            query = f"after:{epoch_seconds}"

            messages = await self._gmail_adapter.fetch_messages(
                access_token=access_token,
                query=query,
                max_results=self._settings.batch_size,
            )

            # Extract the latest history_id from fetched messages
            if messages:
                latest_history_id = max(
                    (m.history_id for m in messages if m.history_id),
                    default=None,
                )
        else:
            # Incremental sync: fetch since last history_id
            messages, new_history_id = await self._gmail_adapter.fetch_history(
                access_token=access_token,
                start_history_id=cursor.history_id,
                max_results=self._settings.batch_size,
            )
            latest_history_id = new_history_id

        if not messages:
            # No new emails — update cursor timestamp if we have a new history_id
            if latest_history_id and cursor is not None:
                await self._sync_cursor_repo.upsert_cursor(
                    user_id=user_id, history_id=latest_history_id
                )
            return 0

        # Convert metadata to EmailMessage entities and persist
        email_entities: list[EmailMessage] = []
        failed_message_ids: list[str] = []

        for msg_metadata in messages:
            try:
                entity = self._metadata_to_entity(user_id, msg_metadata)
                email_entities.append(entity)
            except Exception:
                logger.error(
                    "Failed to convert message metadata to entity: gmail_message_id=%s",
                    msg_metadata.id,
                    exc_info=True,
                )
                failed_message_ids.append(msg_metadata.id)

        # Batch upsert successful entities
        persisted_count = 0
        if email_entities:
            persisted_count = await self._email_repo.batch_upsert(email_entities)

        # Handle failed messages: increment retry count and check for permanent failure
        await self._handle_failed_messages(failed_message_ids)

        # Atomic cursor update: update cursor to latest history_id
        if latest_history_id:
            await self._sync_cursor_repo.upsert_cursor(
                user_id=user_id, history_id=latest_history_id
            )

        # Classify newly synced emails (async, non-blocking).
        # Re-query from DB to get session-attached instances, since
        # batch_upsert() uses Core INSERT and returns transient objects.
        if email_entities and self._settings.classification_enabled:
            await self._classify_new_emails(user_id, [e.gmail_message_id for e in email_entities])

        return persisted_count

    async def _handle_token_refresh(self, user_id: UUID) -> str | None:
        """Attempt to refresh the Gmail access token on 401 error.

        Decrypts the stored refresh token, calls Google's token refresh
        endpoint, encrypts the new access token, and updates the OAuth grant.
        If refresh fails, marks the grant as invalid.

        Args:
            user_id: The UUID of the user whose token to refresh.

        Returns:
            The new decrypted access token on success, or None on failure.
        """
        grant = await self._oauth_grant_repo.get_by_user_id(user_id)
        if grant is None:
            return None

        try:
            # Decrypt the refresh token
            refresh_token = self._crypto.decrypt(grant.refresh_token_enc)

            # Call Google token refresh endpoint
            new_access_token, expires_at = await self._gmail_adapter.refresh_access_token(
                refresh_token=refresh_token,
                client_id=self._client_id,
                client_secret=self._client_secret,
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

            logger.info("Successfully refreshed access token for user %s", user_id)
            return new_access_token

        except Exception as exc:
            logger.error("Token refresh failed for user %s: %s", user_id, exc)
            # Mark grant as invalid — connection status becomes token_expired
            await self._oauth_grant_repo.mark_invalid(user_id)

            await self._audit_logger.log_operation(
                operation_type="fetch",
                user_id=user_id,
                message_count=0,
                success=False,
                metadata={"error": "token_refresh_failed", "reason": str(exc)},
            )

            return None

    async def _check_manual_sync_rate_limit(self, user_id: UUID) -> None:
        """Check if the user is within the manual sync cooldown period.

        Uses Redis to track the last manual sync timestamp per user.
        Raises RateLimitedException if within the cooldown window.

        Args:
            user_id: The UUID of the user to check.

        Raises:
            RateLimitedException: If the cooldown period has not elapsed.
        """
        key = f"gmail:manual_sync:{user_id}"
        last_sync_str = await self._redis.get(key)

        if last_sync_str is not None:
            last_sync_time = float(last_sync_str)
            elapsed = time.time() - last_sync_time
            cooldown = self._settings.manual_sync_cooldown_seconds

            if elapsed < cooldown:
                remaining = int(cooldown - elapsed)
                raise RateLimitedException(retry_after=max(remaining, 1))

    async def _record_manual_sync_timestamp(self, user_id: UUID) -> None:
        """Record the current timestamp as the last manual sync time in Redis.

        Sets the key with a TTL equal to the cooldown period to auto-expire.

        Args:
            user_id: The UUID of the user who performed the manual sync.
        """
        key = f"gmail:manual_sync:{user_id}"
        await self._redis.set(
            key,
            str(time.time()),
            ex=self._settings.manual_sync_cooldown_seconds,
        )

    async def _handle_failed_messages(self, failed_message_ids: list[str]) -> None:
        """Handle messages that failed during fetch/conversion.

        Increments the retry count for each failed message. If a message
        reaches the permanent failure threshold (5 consecutive failures),
        marks it as permanently failed.

        Args:
            failed_message_ids: List of Gmail message IDs that failed processing.
        """
        for gmail_message_id in failed_message_ids:
            try:
                updated = await self._email_repo.increment_retry_count(gmail_message_id)
                if updated and updated.retry_count >= self._settings.permanent_failure_threshold:
                    await self._email_repo.mark_permanently_failed(gmail_message_id)
                    logger.warning(
                        "Message %s marked as permanently failed after %d consecutive failures",
                        gmail_message_id,
                        updated.retry_count,
                    )
            except Exception:
                logger.error(
                    "Failed to update retry count for message %s",
                    gmail_message_id,
                    exc_info=True,
                )

    def _metadata_to_entity(self, user_id: UUID, metadata: GmailMessageMetadata) -> EmailMessage:
        """Convert GmailMessageMetadata to an EmailMessage domain entity.

        Maps adapter response fields to the EmailMessage entity fields,
        applying defaults for missing values.

        Args:
            user_id: The UUID of the user who owns this email.
            metadata: The Gmail message metadata from the adapter.

        Returns:
            An EmailMessage entity ready for persistence.
        """
        return EmailMessage(
            user_id=user_id,
            gmail_message_id=metadata.id,
            gmail_thread_id=metadata.thread_id,
            subject=metadata.subject[:998] if metadata.subject else "",
            sender_email=metadata.sender_email or "",
            sender_name=metadata.sender_name or "",
            recipient_emails=metadata.recipient_emails[:50],
            cc_emails=metadata.cc_emails[:50],
            received_at=metadata.received_at or datetime.now(UTC),
            snippet=metadata.snippet[:200] if metadata.snippet else "",
            label_ids=metadata.label_ids or [],
            has_attachments=metadata.has_attachments,
        )

    async def _classify_new_emails(self, user_id: UUID, gmail_message_ids: list[str]) -> None:
        """Classify newly synced emails using the two-tier classification pipeline.

        Re-queries emails from the database to get session-attached instances,
        avoiding integrity errors from transient objects returned by batch_upsert.

        Args:
            user_id: The UUID of the user who owns the emails.
            gmail_message_ids: List of Gmail message IDs to classify.
        """
        try:
            from sqlmodel import select

            from src.modules.gmail.application.classification_service import (
                ClassificationService,
            )
            from src.modules.gmail.application.rules_classifier import RulesClassifier
            from src.modules.gmail.domain.entities import EmailMessage as EmailMessageEntity
            from src.modules.gmail.infrastructure.ai_classifier import AIClassifier

            # Re-query persisted emails from DB to get session-attached instances
            statement = (
                select(EmailMessageEntity)
                .where(EmailMessageEntity.user_id == user_id)
                .where(EmailMessageEntity.gmail_message_id.in_(gmail_message_ids))
                .where(EmailMessageEntity.processing_status == "unprocessed")
            )
            result = await self._email_repo.session.execute(statement)
            emails = list(result.scalars().all())

            if not emails:
                return

            rules_classifier = RulesClassifier()
            ai_classifier = AIClassifier(self._settings)

            classification_service = ClassificationService(
                rules_classifier=rules_classifier,
                ai_classifier=ai_classifier,
                email_repo=self._email_repo,
                audit_logger=self._audit_logger,
                settings=self._settings,
                session=self._email_repo.session,
            )

            classified_count = await classification_service.classify_batch(
                user_id=user_id, emails=emails
            )
            logger.info(
                "Classified %d/%d new emails for user %s",
                classified_count,
                len(emails),
                user_id,
            )
        except Exception as exc:
            # Classification failure should never break the sync pipeline
            logger.error(
                "Email classification failed for user %s: %s",
                user_id,
                exc,
                exc_info=True,
            )
