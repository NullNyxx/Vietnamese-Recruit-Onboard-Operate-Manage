"""Retention cleanup job for rejected candidate data deletion.

Implements the ARQ scheduled task that hard-deletes rejected candidates
and their associated CV documents/files after the configured retention
period, in compliance with Vietnamese data protection regulations
(NĐ 13/2023/NĐ-CP).

Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6
"""

import hashlib
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.modules.recruitment.domain.entities import Candidate
from src.modules.recruitment.domain.enums import CandidateStatus
from src.modules.recruitment.infrastructure.audit_repository import log_audit
from src.modules.recruitment.infrastructure.config import RecruitmentSettings
from src.modules.recruitment.infrastructure.minio_client import RecruitmentMinIOClient
from src.modules.recruitment.infrastructure.repositories import (
    CandidateRepository,
    CVDocumentRepository,
)

logger = logging.getLogger(__name__)

# Maximum candidates to process per job run
DEFAULT_BATCH_SIZE = 500


def _anonymize_candidate_id(candidate_id: UUID) -> str:
    """Create a SHA-256 hash of the candidate UUID for audit logging.

    Args:
        candidate_id: The UUID of the candidate to anonymize.

    Returns:
        A hex-encoded SHA-256 hash string.
    """
    return hashlib.sha256(str(candidate_id).encode()).hexdigest()


async def _get_expired_candidates(
    session: AsyncSession,
    retention_days: int,
    batch_size: int,
) -> list[Candidate]:
    """Query candidates eligible for retention deletion.

    Selects candidates with status="rejected" whose rejected_at timestamp
    is older than the configured retention period.

    Args:
        session: The async database session.
        retention_days: Number of days after rejection before deletion.
        batch_size: Maximum number of candidates to return.

    Returns:
        A list of Candidate entities eligible for deletion.
    """
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)

    statement = (
        select(Candidate)
        .where(
            Candidate.status == CandidateStatus.REJECTED,
            Candidate.rejected_at < cutoff,  # type: ignore[operator]
        )
        .limit(batch_size)
    )

    result = await session.execute(statement)
    return list(result.scalars().all())


async def _delete_candidate_data(
    candidate: Candidate,
    session: AsyncSession,
    minio_client: RecruitmentMinIOClient,
    cv_doc_repo: CVDocumentRepository,
    candidate_repo: CandidateRepository,
) -> None:
    """Delete a single candidate and all associated data.

    Performs the following in order:
    1. Get all associated CVDocuments
    2. Delete each CV file from MinIO (best-effort, raises on failure)
    3. Delete CVDocument records from DB
    4. Delete Candidate record from DB

    Args:
        candidate: The Candidate entity to delete.
        session: The async database session.
        minio_client: MinIO client for file deletion.
        cv_doc_repo: Repository for CV document operations.
        candidate_repo: Repository for candidate operations.

    Raises:
        Exception: If MinIO file deletion fails (caller should handle).
    """
    # Step 1: Get all associated CV documents
    cv_documents = await cv_doc_repo.find_by_candidate_id(candidate.id)

    # Step 2: Delete each CV file from MinIO
    for doc in cv_documents:
        await minio_client.delete_cv(doc.file_path)

    # Step 3: Delete CVDocument records from DB
    for doc in cv_documents:
        await cv_doc_repo.delete(doc.id)

    # Step 4: Delete Candidate record from DB
    await candidate_repo.delete(candidate.id)


async def retention_cleanup(ctx: dict) -> int:
    """ARQ scheduled task for retention cleanup of rejected candidates.

    Selects rejected candidates whose rejected_at timestamp exceeds the
    configured retention period, then hard-deletes each candidate along
    with their CV documents and MinIO files. Processes one candidate at
    a time so that failure on one does not block others.

    Args:
        ctx: ARQ job context dict. Expected keys:
            - session: AsyncSession instance
            - minio_client: RecruitmentMinIOClient instance
            - settings: RecruitmentSettings instance

    Returns:
        The number of candidates successfully deleted.
    """
    session: AsyncSession = ctx["session"]
    minio_client: RecruitmentMinIOClient = ctx["minio_client"]
    settings: RecruitmentSettings = ctx["settings"]

    retention_days = settings.retention_days
    batch_size = DEFAULT_BATCH_SIZE

    logger.info(
        "Starting retention cleanup: retention_days=%d, batch_size=%d",
        retention_days,
        batch_size,
    )

    # Query eligible candidates
    candidates = await _get_expired_candidates(session, retention_days, batch_size)

    if not candidates:
        logger.info("No candidates eligible for retention deletion.")
        return 0

    logger.info("Found %d candidates eligible for retention deletion.", len(candidates))

    deleted_count = 0
    candidate_repo = CandidateRepository(session)
    cv_doc_repo = CVDocumentRepository(session)

    for candidate in candidates:
        anonymized_id = _anonymize_candidate_id(candidate.id)

        try:
            await _delete_candidate_data(
                candidate=candidate,
                session=session,
                minio_client=minio_client,
                cv_doc_repo=cv_doc_repo,
                candidate_repo=candidate_repo,
            )

            # Commit the deletion for this candidate
            await session.commit()

            # Audit log successful deletion (Requirement 15.5)
            await log_audit(
                session=session,
                operation_type="candidate_data_deleted",
                entity_type="candidate",
                entity_id=None,  # Don't store real ID in audit
                change_summary=f"Retention cleanup: deleted candidate {anonymized_id}",
                success=True,
            )
            await session.commit()

            deleted_count += 1
            logger.info(
                "Successfully deleted candidate data: anonymized_id=%s",
                anonymized_id,
            )

        except Exception:
            # Requirement 15.2/15.3: failure on one doesn't block others
            await session.rollback()

            logger.error(
                "Failed to delete candidate data: anonymized_id=%s",
                anonymized_id,
                exc_info=True,
            )

            # Log audit entry for the failure (Requirement 15.3)
            try:
                await log_audit(
                    session=session,
                    operation_type="candidate_data_deleted",
                    entity_type="candidate",
                    entity_id=None,
                    change_summary=(f"Retention cleanup FAILED for candidate {anonymized_id}"),
                    success=False,
                )
                await session.commit()
            except Exception:
                logger.error(
                    "Failed to log audit entry for deletion failure: anonymized_id=%s",
                    anonymized_id,
                    exc_info=True,
                )

    logger.info(
        "Retention cleanup completed: deleted=%d, total_eligible=%d",
        deleted_count,
        len(candidates),
    )

    return deleted_count
