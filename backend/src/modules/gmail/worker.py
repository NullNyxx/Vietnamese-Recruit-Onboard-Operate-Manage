"""ARQ worker configuration for Gmail email polling.

Defines the cron job that periodically fetches new emails for all connected
Gmail users. Runs every GMAIL_POLL_INTERVAL_SECONDS (default 300 = 5 minutes).
The worker iterates over all users with valid Gmail OAuth grants, checks their
connection status, and calls EmailSyncService.poll_emails for each connected user.

Usage:
    arq src.modules.gmail.worker.WorkerSettings
"""

from __future__ import annotations

import logging
import traceback
from datetime import UTC, datetime

from dotenv import load_dotenv

# Load .env before any settings are instantiated (same pattern as main.py).
load_dotenv()

import httpx
import redis.asyncio as redis
from arq import cron
from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.modules.gmail.application.connection_service import GMAIL_SCOPES
from src.modules.gmail.application.email_sync_service import EmailSyncService
from src.modules.gmail.infrastructure.audit_logger import AuditLogger
from src.modules.gmail.infrastructure.config import GmailSettings
from src.modules.gmail.infrastructure.email_repository import EmailRepository
from src.modules.gmail.infrastructure.gmail_adapter import GmailAdapter
from src.modules.gmail.infrastructure.quota_tracker import QuotaTracker
from src.modules.gmail.infrastructure.sync_cursor_repository import SyncCursorRepository
from src.modules.identity.infrastructure.config import AuthSettings
from src.modules.identity.infrastructure.crypto_utils import CryptoUtils
from src.modules.identity.infrastructure.oauth_grant_repository import OAuthGrantRepository

logger = logging.getLogger(__name__)


async def startup(ctx: dict) -> None:
    """ARQ worker startup hook.

    Initializes shared resources (database engine, Redis client, HTTP client,
    settings) and stores them in the worker context dict for use by cron jobs.

    Args:
        ctx: The ARQ worker context dictionary.
    """
    auth_settings = AuthSettings()  # type: ignore[call-arg]
    gmail_settings = GmailSettings()  # type: ignore[call-arg]

    engine = create_async_engine(auth_settings.database_url, echo=False)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    redis_client = redis.from_url(auth_settings.redis_url, decode_responses=True)
    http_client = httpx.AsyncClient()
    crypto = CryptoUtils(auth_settings.oauth_token_encryption_key)
    quota_tracker = QuotaTracker(redis_client, gmail_settings)

    ctx["session_maker"] = session_maker
    ctx["redis_client"] = redis_client
    ctx["http_client"] = http_client
    ctx["crypto"] = crypto
    ctx["quota_tracker"] = quota_tracker
    ctx["auth_settings"] = auth_settings
    ctx["gmail_settings"] = gmail_settings

    logger.info("Gmail ARQ worker started successfully")


async def shutdown(ctx: dict) -> None:
    """ARQ worker shutdown hook.

    Cleans up shared resources (HTTP client, Redis connection).

    Args:
        ctx: The ARQ worker context dictionary.
    """
    http_client: httpx.AsyncClient | None = ctx.get("http_client")
    if http_client:
        await http_client.aclose()

    redis_client: redis.Redis | None = ctx.get("redis_client")
    if redis_client:
        await redis_client.aclose()

    logger.info("Gmail ARQ worker shut down")


async def poll_gmail_emails(ctx: dict) -> None:
    """ARQ cron job: fetch new emails for all connected Gmail users.

    Iterates over all users with valid Gmail OAuth grants, checks their
    connection status (skips non-connected users), and calls
    EmailSyncService.poll_emails for each connected user.

    Exceptions for individual users are caught and logged with stack traces.
    A single user's failure does not prevent polling for other users.
    ARQ automatically retries the job at the next scheduled interval.

    Args:
        ctx: The ARQ worker context dictionary containing shared resources.
    """
    session_maker: async_sessionmaker[AsyncSession] = ctx["session_maker"]
    redis_client: redis.Redis = ctx["redis_client"]
    http_client: httpx.AsyncClient = ctx["http_client"]
    crypto: CryptoUtils = ctx["crypto"]
    quota_tracker: QuotaTracker = ctx["quota_tracker"]
    auth_settings: AuthSettings = ctx["auth_settings"]
    gmail_settings: GmailSettings = ctx["gmail_settings"]

    gmail_scopes_list = list(GMAIL_SCOPES)

    async with session_maker() as session:
        try:
            # Get all users with valid Gmail OAuth grants
            oauth_grant_repo = OAuthGrantRepository(session)
            grants = await oauth_grant_repo.get_all_valid_with_scopes(gmail_scopes_list)

            if not grants:
                logger.debug("No users with active Gmail connections found")
                return

            logger.info("Starting Gmail poll cycle for %d user(s)", len(grants))

            for grant in grants:
                user_id = grant.user_id

                try:
                    # Check connection status: skip if token expired
                    if not grant.is_valid:
                        logger.debug("Skipping user %s: grant is invalid", user_id)
                        continue

                    if grant.token_expires_at <= datetime.now(UTC):
                        logger.debug("Skipping user %s: token expired", user_id)
                        continue

                    # Build per-user service dependencies
                    gmail_adapter = GmailAdapter(
                        settings=gmail_settings,
                        quota_tracker=quota_tracker,
                        http_client=http_client,
                        user_id=user_id,
                    )
                    email_repo = EmailRepository(session)
                    sync_cursor_repo = SyncCursorRepository(session)
                    audit_logger = AuditLogger(session, gmail_settings)

                    email_sync_service = EmailSyncService(
                        gmail_adapter=gmail_adapter,
                        email_repo=email_repo,
                        sync_cursor_repo=sync_cursor_repo,
                        oauth_grant_repo=oauth_grant_repo,
                        crypto=crypto,
                        audit_logger=audit_logger,
                        settings=gmail_settings,
                        redis_client=redis_client,
                        client_id=auth_settings.google_client_id,
                        client_secret=auth_settings.google_client_secret,
                    )

                    count = await email_sync_service.poll_emails(user_id)
                    logger.info("Polled %d new email(s) for user %s", count, user_id)

                except Exception:
                    logger.error(
                        "Unhandled exception polling emails for user %s:\n%s",
                        user_id,
                        traceback.format_exc(),
                    )
                    # Continue to next user — don't let one failure stop others

            await session.commit()

        except Exception:
            logger.error(
                "Unhandled exception in poll_gmail_emails cron job:\n%s",
                traceback.format_exc(),
            )
            await session.rollback()
            raise  # Let ARQ handle the retry at next interval


def _build_cron_schedule(poll_interval_seconds: int) -> set[int]:
    """Build the set of minute marks for the ARQ cron schedule.

    Converts the poll interval (in seconds) to a set of minutes within
    the hour at which the job should run.

    Args:
        poll_interval_seconds: The polling interval in seconds (60-3600).

    Returns:
        A set of minute values (0-59) for the cron schedule.
    """
    interval_minutes = max(1, poll_interval_seconds // 60)
    return set(range(0, 60, interval_minutes))


# Load settings for cron schedule configuration.
_gmail_settings = GmailSettings()  # type: ignore[call-arg]
_auth_settings = AuthSettings()  # type: ignore[call-arg]


class WorkerSettings:
    """ARQ worker settings for Gmail polling.

    Configures the cron job schedule, Redis connection, and worker
    lifecycle hooks (startup/shutdown).

    The cron schedule is derived from GMAIL_POLL_INTERVAL_SECONDS:
    - Default 300s (5 min) → runs at minutes 0, 5, 10, 15, ..., 55
    - 60s (1 min) → runs every minute
    - 600s (10 min) → runs at minutes 0, 10, 20, 30, 40, 50
    """

    on_startup = startup
    on_shutdown = shutdown

    cron_jobs = [
        cron(
            poll_gmail_emails,
            minute=_build_cron_schedule(_gmail_settings.poll_interval_seconds),
            second={0},
        ),
    ]

    redis_settings = RedisSettings.from_dsn(_auth_settings.redis_url)
