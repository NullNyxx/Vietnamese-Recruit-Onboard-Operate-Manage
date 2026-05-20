"""Dependency injection container for the Gmail Integration module.

Provides FastAPI dependency functions that wire together all services,
repositories, and infrastructure components using the shared async
database session and Redis client from the identity module.
"""

from __future__ import annotations

from functools import lru_cache

import httpx
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.gmail.application.attachment_service import AttachmentService
from src.modules.gmail.application.connection_service import ConnectionService
from src.modules.gmail.application.email_sync_service import EmailSyncService
from src.modules.gmail.application.label_service import LabelService
from src.modules.gmail.application.send_service import SendService
from src.modules.gmail.infrastructure.audit_logger import AuditLogger
from src.modules.gmail.infrastructure.config import GmailSettings
from src.modules.gmail.infrastructure.email_repository import EmailRepository
from src.modules.gmail.infrastructure.gmail_adapter import GmailAdapter
from src.modules.gmail.infrastructure.label_repository import LabelRepository
from src.modules.gmail.infrastructure.quota_tracker import QuotaTracker
from src.modules.gmail.infrastructure.sync_cursor_repository import SyncCursorRepository
from src.modules.identity.container import (
    get_crypto_utils,
    get_db_session,
    get_redis_client,
    get_settings as get_auth_settings,
)
from src.modules.identity.infrastructure.oauth_grant_repository import OAuthGrantRepository


# ---------------------------------------------------------------------------
# Singleton infrastructure components
# ---------------------------------------------------------------------------


@lru_cache
def get_gmail_settings() -> GmailSettings:
    """Load and cache GmailSettings from environment variables.

    Returns:
        The GmailSettings singleton loaded from GMAIL_* env vars.
    """
    return GmailSettings()  # type: ignore[call-arg]


@lru_cache
def get_quota_tracker() -> QuotaTracker:
    """Create and cache the QuotaTracker singleton.

    Returns:
        A QuotaTracker configured with the Redis client and settings.
    """
    redis_client = get_redis_client()
    return QuotaTracker(redis_client, get_gmail_settings())


@lru_cache
def get_http_client() -> httpx.AsyncClient:
    """Create and cache the shared httpx AsyncClient.

    Returns:
        An httpx.AsyncClient for Gmail API calls.
    """
    return httpx.AsyncClient()


# ---------------------------------------------------------------------------
# Repository dependency functions
# ---------------------------------------------------------------------------


async def get_oauth_grant_repository(
    session: AsyncSession = Depends(get_db_session),
) -> OAuthGrantRepository:
    """Provide an OAuthGrantRepository instance.

    Args:
        session: The async database session from DI.

    Returns:
        An OAuthGrantRepository bound to the current session.
    """
    return OAuthGrantRepository(session)


async def get_email_repository(
    session: AsyncSession = Depends(get_db_session),
) -> EmailRepository:
    """Provide an EmailRepository instance.

    Args:
        session: The async database session from DI.

    Returns:
        An EmailRepository bound to the current session.
    """
    return EmailRepository(session)


async def get_sync_cursor_repository(
    session: AsyncSession = Depends(get_db_session),
) -> SyncCursorRepository:
    """Provide a SyncCursorRepository instance.

    Args:
        session: The async database session from DI.

    Returns:
        A SyncCursorRepository bound to the current session.
    """
    return SyncCursorRepository(session)


async def get_label_repository(
    session: AsyncSession = Depends(get_db_session),
) -> LabelRepository:
    """Provide a LabelRepository instance.

    Args:
        session: The async database session from DI.

    Returns:
        A LabelRepository bound to the current session.
    """
    return LabelRepository(session)


async def get_audit_logger(
    session: AsyncSession = Depends(get_db_session),
) -> AuditLogger:
    """Provide an AuditLogger instance.

    Args:
        session: The async database session from DI.

    Returns:
        An AuditLogger bound to the current session.
    """
    return AuditLogger(session, get_gmail_settings())


# ---------------------------------------------------------------------------
# Service dependency functions
# ---------------------------------------------------------------------------


async def get_gmail_adapter() -> GmailAdapter:
    """Provide a GmailAdapter instance.

    Note: The GmailAdapter requires a user_id for quota tracking.
    This provides a base adapter; endpoints should pass user_id context.

    Returns:
        A GmailAdapter configured with settings, quota tracker, and HTTP client.
    """
    from uuid import UUID

    # The adapter needs a user_id for quota tracking; we use a placeholder
    # that will be overridden per-request in the router endpoints.
    # For DI purposes, we create with a nil UUID; actual usage passes user context.
    return GmailAdapter(
        settings=get_gmail_settings(),
        quota_tracker=get_quota_tracker(),
        http_client=get_http_client(),
        user_id=UUID("00000000-0000-0000-0000-000000000000"),
    )


async def get_label_service(
    label_repo: LabelRepository = Depends(get_label_repository),
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> LabelService:
    """Provide a LabelService instance.

    Args:
        label_repo: The label repository from DI.
        audit_logger: The audit logger from DI.

    Returns:
        A LabelService configured with all dependencies.
    """
    gmail_adapter = await get_gmail_adapter()
    return LabelService(
        gmail_adapter=gmail_adapter,
        label_repo=label_repo,
        settings=get_gmail_settings(),
        audit_logger=audit_logger,
    )


async def get_connection_service(
    oauth_grant_repo: OAuthGrantRepository = Depends(get_oauth_grant_repository),
    label_service: LabelService = Depends(get_label_service),
) -> ConnectionService:
    """Provide a ConnectionService instance.

    Args:
        oauth_grant_repo: The OAuth grant repository from DI.
        label_service: The label service from DI.

    Returns:
        A ConnectionService configured with all dependencies.
    """
    auth_settings = get_auth_settings()
    gmail_settings = get_gmail_settings()
    gmail_adapter = await get_gmail_adapter()

    return ConnectionService(
        settings=gmail_settings,
        auth_settings_client_id=auth_settings.google_client_id,
        auth_settings_client_secret=auth_settings.google_client_secret,
        gmail_redirect_uri=auth_settings.google_redirect_uri,
        oauth_grant_repo=oauth_grant_repo,
        gmail_adapter=gmail_adapter,
        crypto=get_crypto_utils(),
        label_service=label_service,
    )


async def get_email_sync_service(
    email_repo: EmailRepository = Depends(get_email_repository),
    sync_cursor_repo: SyncCursorRepository = Depends(get_sync_cursor_repository),
    oauth_grant_repo: OAuthGrantRepository = Depends(get_oauth_grant_repository),
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> EmailSyncService:
    """Provide an EmailSyncService instance.

    Args:
        email_repo: The email repository from DI.
        sync_cursor_repo: The sync cursor repository from DI.
        oauth_grant_repo: The OAuth grant repository from DI.
        audit_logger: The audit logger from DI.

    Returns:
        An EmailSyncService configured with all dependencies.
    """
    auth_settings = get_auth_settings()
    gmail_adapter = await get_gmail_adapter()

    return EmailSyncService(
        gmail_adapter=gmail_adapter,
        email_repo=email_repo,
        sync_cursor_repo=sync_cursor_repo,
        oauth_grant_repo=oauth_grant_repo,
        crypto=get_crypto_utils(),
        audit_logger=audit_logger,
        settings=get_gmail_settings(),
        redis_client=get_redis_client(),
        client_id=auth_settings.google_client_id,
        client_secret=auth_settings.google_client_secret,
    )


async def get_send_service(
    email_repo: EmailRepository = Depends(get_email_repository),
    oauth_grant_repo: OAuthGrantRepository = Depends(get_oauth_grant_repository),
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> SendService:
    """Provide a SendService instance.

    Args:
        email_repo: The email repository from DI.
        oauth_grant_repo: The OAuth grant repository from DI.
        audit_logger: The audit logger from DI.

    Returns:
        A SendService configured with all dependencies.
    """
    auth_settings = get_auth_settings()
    gmail_adapter = await get_gmail_adapter()

    return SendService(
        gmail_adapter=gmail_adapter,
        email_repo=email_repo,
        oauth_grant_repo=oauth_grant_repo,
        crypto=get_crypto_utils(),
        audit_logger=audit_logger,
        settings=get_gmail_settings(),
        client_id=auth_settings.google_client_id,
        client_secret=auth_settings.google_client_secret,
    )


async def get_attachment_service(
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> AttachmentService:
    """Provide an AttachmentService instance.

    Args:
        audit_logger: The audit logger from DI.

    Returns:
        An AttachmentService configured with all dependencies.
    """
    gmail_adapter = await get_gmail_adapter()

    return AttachmentService(
        gmail_adapter=gmail_adapter,
        settings=get_gmail_settings(),
        audit_logger=audit_logger,
    )
