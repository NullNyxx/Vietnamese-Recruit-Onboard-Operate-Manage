"""Dependency injection container for the Recruitment CV Pipeline module.

Provides FastAPI dependency functions that wire together all services,
repositories, and infrastructure components using the shared async
database session from the identity module.

Also registers ARQ task functions for background processing:
- process_cv_from_email: CV processing pipeline triggered by intent classification
- retention_cleanup: Scheduled cleanup of expired rejected candidates

Requirements: 1.4, 2.7, 15.4, 16.2
"""

from __future__ import annotations

from functools import lru_cache
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.container import get_current_user, get_db_session
from src.modules.identity.domain.entities import User
from src.modules.recruitment.application.candidate_service import CandidateService
from src.modules.recruitment.application.cv_processor import CVProcessorService
from src.modules.recruitment.application.intent_classifier import IntentClassifierService
from src.modules.recruitment.application.review_service import ReviewService
from src.modules.recruitment.infrastructure.config import RecruitmentSettings
from src.modules.recruitment.infrastructure.llm_adapter import LLMAdapter
from src.modules.recruitment.infrastructure.minio_client import RecruitmentMinIOClient
from src.modules.recruitment.infrastructure.ocr_adapter import OCRAdapter
from src.modules.recruitment.infrastructure.pii_redactor import PIIRedactor
from src.modules.recruitment.infrastructure.repositories import (
    CandidateRepository,
    CVDocumentRepository,
)

# ---------------------------------------------------------------------------
# Singleton infrastructure components
# ---------------------------------------------------------------------------


@lru_cache
def get_recruitment_settings() -> RecruitmentSettings:
    """Load and cache RecruitmentSettings from environment variables.

    Returns:
        The RecruitmentSettings singleton loaded from RECRUITMENT_* env vars.
    """
    return RecruitmentSettings()  # type: ignore[call-arg]


@lru_cache
def get_minio_client() -> RecruitmentMinIOClient:
    """Create and cache the RecruitmentMinIOClient singleton.

    Returns:
        A RecruitmentMinIOClient configured with recruitment settings.
    """
    settings = get_recruitment_settings()
    return RecruitmentMinIOClient(settings)


@lru_cache
def get_llm_adapter() -> LLMAdapter:
    """Create and cache the LLMAdapter singleton.

    Returns:
        An LLMAdapter configured with recruitment LLM settings.
    """
    settings = get_recruitment_settings()
    return LLMAdapter(settings)


@lru_cache
def get_ocr_adapter() -> OCRAdapter:
    """Create and cache the OCRAdapter singleton.

    Returns:
        An OCRAdapter configured with recruitment olmOCR settings.
    """
    settings = get_recruitment_settings()
    return OCRAdapter(settings)


@lru_cache
def get_pii_redactor() -> PIIRedactor:
    """Create and cache the PIIRedactor singleton.

    Returns:
        A PIIRedactor instance for sanitizing text before LLM calls.
    """
    return PIIRedactor()


# ---------------------------------------------------------------------------
# FastAPI dependency functions for services
# ---------------------------------------------------------------------------


async def get_candidate_service(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> CandidateService:
    """Provide a CandidateService instance with all dependencies.

    Args:
        session: The async database session from DI.
        current_user: The authenticated user.

    Returns:
        A fully configured CandidateService.
    """
    candidate_repo = CandidateRepository(session)
    cv_document_repo = CVDocumentRepository(session)
    minio_client = get_minio_client()

    return CandidateService(
        candidate_repo=candidate_repo,
        cv_document_repo=cv_document_repo,
        minio_client=minio_client,
        session=session,
        user_id=current_user.id,
    )


async def get_review_service(
    session: AsyncSession = Depends(get_db_session),
) -> ReviewService:
    """Provide a ReviewService instance with all dependencies.

    Args:
        session: The async database session from DI.

    Returns:
        A fully configured ReviewService.
    """
    cv_document_repo = CVDocumentRepository(session)
    candidate_repo = CandidateRepository(session)
    minio_client = get_minio_client()

    # CandidateService acts as the CandidateCreatorProtocol
    candidate_service = CandidateService(
        candidate_repo=candidate_repo,
        cv_document_repo=cv_document_repo,
        minio_client=minio_client,
        session=session,
    )

    # CVProcessorService acts as the CVRetryParserProtocol
    settings = get_recruitment_settings()
    cv_processor = CVProcessorService(
        minio_client=minio_client,
        ocr_adapter=get_ocr_adapter(),
        llm_adapter=get_llm_adapter(),
        pii_redactor=get_pii_redactor(),
        candidate_repo=candidate_repo,
        cv_document_repo=cv_document_repo,
        settings=settings,
        session=session,
        candidate_creator=candidate_service,
    )

    return ReviewService(
        cv_document_repo=cv_document_repo,
        candidate_creator=candidate_service,
        cv_retry_parser=cv_processor,
        session=session,
    )


async def get_cv_processor_service(
    session: AsyncSession = Depends(get_db_session),
) -> CVProcessorService:
    """Provide a CVProcessorService instance with all dependencies.

    Args:
        session: The async database session from DI.

    Returns:
        A fully configured CVProcessorService.
    """
    settings = get_recruitment_settings()
    candidate_repo = CandidateRepository(session)
    cv_document_repo = CVDocumentRepository(session)
    minio_client = get_minio_client()

    # CandidateService acts as the CandidateCreator protocol
    candidate_service = CandidateService(
        candidate_repo=candidate_repo,
        cv_document_repo=cv_document_repo,
        minio_client=minio_client,
        session=session,
    )

    return CVProcessorService(
        minio_client=minio_client,
        ocr_adapter=get_ocr_adapter(),
        llm_adapter=get_llm_adapter(),
        pii_redactor=get_pii_redactor(),
        candidate_repo=candidate_repo,
        cv_document_repo=cv_document_repo,
        settings=settings,
        session=session,
        candidate_creator=candidate_service,
    )


async def get_intent_classifier_service(
    session: AsyncSession = Depends(get_db_session),
) -> IntentClassifierService:
    """Provide an IntentClassifierService instance with all dependencies.

    Args:
        session: The async database session from DI.

    Returns:
        A fully configured IntentClassifierService.
    """
    return IntentClassifierService(
        llm_adapter=get_llm_adapter(),
        pii_redactor=get_pii_redactor(),
        session=session,
    )


# ---------------------------------------------------------------------------
# ARQ task functions
# ---------------------------------------------------------------------------


async def arq_process_cv_from_email(ctx: dict, email_message_id: UUID) -> None:
    """ARQ task: process CV attachments from a classified email.

    This task is enqueued by the IntentClassifierService when an email
    is classified as CV intent. It downloads attachments, runs OCR,
    parses with LLM, and creates candidate records.

    Args:
        ctx: ARQ job context dict with shared resources.
        email_message_id: UUID of the email message to process.
    """
    import logging

    logger = logging.getLogger(__name__)
    logger.info("ARQ task: processing CV from email %s", email_message_id)

    session_maker = ctx["session_maker"]

    async with session_maker() as session:
        try:
            settings = get_recruitment_settings()
            candidate_repo = CandidateRepository(session)
            cv_document_repo = CVDocumentRepository(session)
            minio_client = get_minio_client()

            candidate_service = CandidateService(
                candidate_repo=candidate_repo,
                cv_document_repo=cv_document_repo,
                minio_client=minio_client,
                session=session,
            )

            cv_processor = CVProcessorService(
                minio_client=minio_client,
                ocr_adapter=get_ocr_adapter(),
                llm_adapter=get_llm_adapter(),
                pii_redactor=get_pii_redactor(),
                candidate_repo=candidate_repo,
                cv_document_repo=cv_document_repo,
                settings=settings,
                session=session,
                candidate_creator=candidate_service,
            )

            # Fetch email message to get gmail_message_id and user_id
            import httpx
            import redis.asyncio as redis
            from sqlmodel import select

            from src.modules.gmail.application.attachment_service import (
                AttachmentMetadata,
                AttachmentService,
            )
            from src.modules.gmail.domain.entities import EmailAttachment, EmailMessage
            from src.modules.gmail.infrastructure.audit_logger import AuditLogger
            from src.modules.gmail.infrastructure.config import GmailSettings
            from src.modules.gmail.infrastructure.gmail_adapter import GmailAdapter
            from src.modules.gmail.infrastructure.quota_tracker import QuotaTracker
            from src.modules.identity.infrastructure.config import AuthSettings
            from src.modules.identity.infrastructure.crypto_utils import CryptoUtils
            from src.modules.identity.infrastructure.oauth_grant_repository import (
                OAuthGrantRepository,
            )
            from src.modules.recruitment.application.cv_processor import AttachmentInput

            # Get email message record
            stmt = select(EmailMessage).where(EmailMessage.id == email_message_id)
            result = await session.execute(stmt)
            email_msg = result.scalars().first()

            if email_msg is None:
                logger.error("Email message not found for ARQ task: %s", email_message_id)
                return

            gmail_message_id = email_msg.gmail_message_id
            user_id = email_msg.user_id

            # Get attachment metadata from database
            att_stmt = select(EmailAttachment).where(
                EmailAttachment.email_message_id == email_message_id
            )
            att_result = await session.execute(att_stmt)
            db_attachments = list(att_result.scalars().all())

            if not db_attachments:
                logger.info(
                    "No attachments found for email %s, skipping CV processing",
                    email_message_id,
                )
                return

            # Get OAuth grant for the user to access Gmail API
            auth_settings = AuthSettings()  # type: ignore[call-arg]
            gmail_settings = GmailSettings()  # type: ignore[call-arg]
            crypto = CryptoUtils(auth_settings.oauth_token_encryption_key)
            oauth_grant_repo = OAuthGrantRepository(session)

            grant = await oauth_grant_repo.get_by_user_id(user_id)

            if grant is None or not grant.is_valid:
                logger.error("No valid Gmail grant for user %s, cannot process CV", user_id)
                return

            # Decrypt access token
            access_token = crypto.decrypt(grant.access_token_enc)

            # Build Gmail adapter and AttachmentService to fetch binary data
            redis_client = ctx.get("redis_client")
            if redis_client is None:
                redis_client = redis.from_url(auth_settings.redis_url, decode_responses=True)

            quota_tracker = QuotaTracker(redis_client, gmail_settings)

            async with httpx.AsyncClient() as http_client:
                gmail_adapter = GmailAdapter(
                    settings=gmail_settings,
                    quota_tracker=quota_tracker,
                    http_client=http_client,
                    user_id=user_id,
                )
                audit_logger = AuditLogger(session, gmail_settings)

                attachment_service = AttachmentService(
                    gmail_adapter=gmail_adapter,
                    settings=gmail_settings,
                    audit_logger=audit_logger,
                )

                # Build AttachmentMetadata list from DB records
                attachment_metadata_list = [
                    AttachmentMetadata(
                        attachment_id=att.gmail_attachment_id,
                        filename=att.filename,
                        mime_type=att.mime_type,
                        size_bytes=att.size_bytes,
                    )
                    for att in db_attachments
                ]

                # Fetch attachment binary data via AttachmentService
                fetch_result = await attachment_service.fetch_attachments(
                    user_id=user_id,
                    message_id=gmail_message_id,
                    access_token=access_token,
                    attachments=attachment_metadata_list,
                )

                # Convert fetched attachments to CVProcessor input format
                attachments_data: list[AttachmentInput] = [
                    AttachmentInput(
                        filename=att.filename,
                        mime_type=att.mime_type,
                        size_bytes=att.size_bytes,
                        data=att.data,
                    )
                    for att in fetch_result.fetched
                ]

                if not attachments_data:
                    logger.info(
                        "No valid attachments fetched for email %s, skipping",
                        email_message_id,
                    )
                    return

                # Process all attachments through the CV pipeline
                await cv_processor.process_cv_from_email(
                    email_message_id=email_message_id,
                    attachments=attachments_data,
                    gmail_message_id=gmail_message_id,
                )

            await session.commit()
            logger.info("ARQ task completed: CV processing for email %s", email_message_id)

        except Exception:
            await session.rollback()
            logger.error(
                "ARQ task failed: CV processing for email %s",
                email_message_id,
                exc_info=True,
            )
            raise


async def arq_retention_cleanup(ctx: dict) -> int:
    """ARQ task: retention cleanup of expired rejected candidates.

    Delegates to the retention_cleanup function which handles the full
    cleanup logic including MinIO file deletion and audit logging.

    Args:
        ctx: ARQ job context dict with shared resources.

    Returns:
        Number of candidates successfully deleted.
    """
    import logging

    from src.modules.recruitment.application.retention_job import retention_cleanup

    logger = logging.getLogger(__name__)
    logger.info("ARQ task: starting retention cleanup")

    session_maker = ctx["session_maker"]

    async with session_maker() as session:
        # Build the context expected by retention_cleanup
        retention_ctx: dict = {
            "session": session,
            "minio_client": get_minio_client(),
            "settings": get_recruitment_settings(),
        }

        deleted_count = await retention_cleanup(retention_ctx)
        logger.info("ARQ task completed: retention cleanup deleted %d candidates", deleted_count)
        return deleted_count


def get_arq_tasks() -> list:
    """Return the list of ARQ task functions for the recruitment module.

    These tasks should be registered in the ARQ worker settings alongside
    the Gmail module's cron jobs.

    Returns:
        List of ARQ-compatible async task functions.
    """
    return [arq_process_cv_from_email, arq_retention_cleanup]
