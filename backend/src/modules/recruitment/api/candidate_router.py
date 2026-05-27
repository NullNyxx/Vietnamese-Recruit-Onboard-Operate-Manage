"""FastAPI router for the Recruitment Candidate Pool endpoints.

Defines the /api/recruitment/candidates/* endpoints for candidate
list, detail, CV view, and action operations (schedule interview,
send email, reject, accept, archive).

Requirements: 6.1, 6.7, 7.1, 7.3-7.5, 8.1-8.5, 9.1, 9.3, 9.5,
10.1, 10.4, 10.7-10.8, 11.1, 11.3, 11.5, 12.1, 12.3, 12.5,
13.1, 13.5
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.container import get_current_user, get_db_session
from src.modules.identity.domain.entities import User
from src.modules.recruitment.api.schemas import (
    CandidateDetailResponse,
    CandidateListItemResponse,
    CandidateListResponse,
    CandidateResponse,
    CVDocumentResponse,
    CVPresignedUrlResponse,
    RejectRequest,
    ScheduleInterviewRequest,
    SendEmailRequest,
)
from src.modules.recruitment.application.candidate_service import (
    CandidateService,
    PaginatedCandidates,
)
from src.modules.recruitment.domain.enums import CandidateStatus, ProcessingStatus
from src.modules.recruitment.domain.exceptions import (
    CandidateNotFoundError,
    CVDocumentNotFoundError,
    CVFileNotFoundError,
    StorageServiceUnavailableError,
)
from src.modules.recruitment.infrastructure.minio_client import RecruitmentMinIOClient
from src.modules.recruitment.infrastructure.repositories import (
    CandidateRepository,
    CVDocumentRepository,
)

# ---------------------------------------------------------------------------
# Dependency injection
# ---------------------------------------------------------------------------


def _get_minio_client() -> RecruitmentMinIOClient:
    """Provide the RecruitmentMinIOClient singleton.

    Returns:
        A RecruitmentMinIOClient configured with recruitment settings.
    """
    from src.modules.recruitment.container import get_recruitment_settings

    settings = get_recruitment_settings()
    return RecruitmentMinIOClient(settings)


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
    minio_client = _get_minio_client()

    return CandidateService(
        candidate_repo=candidate_repo,
        cv_document_repo=cv_document_repo,
        minio_client=minio_client,
        session=session,
        user_id=current_user.id,
    )


# ---------------------------------------------------------------------------
# Type aliases for injected dependencies
# ---------------------------------------------------------------------------

CurrentUserDep = Annotated[User, Depends(get_current_user)]
CandidateServiceDep = Annotated[CandidateService, Depends(get_candidate_service)]


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

candidate_router = APIRouter(
    prefix="/api/recruitment/candidates",
    tags=["recruitment-candidates"],
)


# ---------------------------------------------------------------------------
# List candidates
# ---------------------------------------------------------------------------


@candidate_router.get("", response_model=CandidateListResponse)
async def list_candidates(
    current_user: CurrentUserDep,
    candidate_service: CandidateServiceDep,
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    search: str | None = Query(
        default=None, min_length=1, max_length=200, description="Search query"
    ),
    status: list[CandidateStatus] | None = Query(default=None, description="Filter by status"),
    from_date: date | None = Query(default=None, description="Filter from date"),
    to_date: date | None = Query(default=None, description="Filter to date"),
    min_confidence: float | None = Query(
        default=None, ge=0.0, le=1.0, description="Minimum confidence score"
    ),
    skills: str | None = Query(default=None, description="Comma-separated skills filter"),
) -> CandidateListResponse:
    """List candidates with pagination, search, and filters.

    Returns a paginated list of candidates sorted by created_at descending.
    Archived candidates are excluded unless explicitly filtered by status.

    Args:
        current_user: The authenticated user.
        candidate_service: The candidate service.
        page: Page number (1-indexed).
        page_size: Number of items per page (1–100).
        search: Optional search query for name/email/phone/skills.
        status: Optional status filter (one or more values).
        from_date: Optional start date for created_at range.
        to_date: Optional end date for created_at range.
        min_confidence: Optional minimum confidence score (0.0–1.0).
        skills: Optional comma-separated skills filter.

    Returns:
        Paginated list of candidates with total count.
    """
    # Parse skills filter from comma-separated string
    skills_list: list[str] | None = None
    if skills:
        skills_list = [s.strip() for s in skills.split(",") if s.strip()]

    # Convert status enum list to string list for the service
    status_list: list[str] | None = None
    if status:
        status_list = [s.value for s in status]

    # Convert dates to datetime for the service
    date_from: datetime | None = None
    date_to: datetime | None = None
    if from_date:
        date_from = datetime(from_date.year, from_date.month, from_date.day)
    if to_date:
        date_to = datetime(to_date.year, to_date.month, to_date.day, 23, 59, 59)

    result: PaginatedCandidates = await candidate_service.list_candidates(
        status=status_list,
        date_from=date_from,
        date_to=date_to,
        min_confidence=min_confidence,
        skills=skills_list,
        search=search,
        page=page,
        page_size=page_size,
    )

    # Build response items with skills truncated to first 5
    items = [
        CandidateListItemResponse(
            id=c.id,
            name=c.name,
            email=c.email,
            phone=c.phone or "",
            skills=(c.skills or [])[:5],
            status=c.status,
            confidence_score=c.confidence_score,
            created_at=c.created_at,
            has_cv=True,  # Candidates are created from CVs
        )
        for c in result.candidates
    ]

    return CandidateListResponse(
        candidates=items,
        total_count=result.total_count,
        page=result.page,
        page_size=result.page_size,
    )


# ---------------------------------------------------------------------------
# Get candidate detail
# ---------------------------------------------------------------------------


@candidate_router.get("/{candidate_id}", response_model=CandidateDetailResponse)
async def get_candidate(
    candidate_id: UUID,
    current_user: CurrentUserDep,
    candidate_service: CandidateServiceDep,
) -> CandidateDetailResponse:
    """Get full candidate detail with linked CV documents.

    Returns the complete candidate record including all CV documents
    with presigned download URLs.

    Args:
        candidate_id: UUID of the candidate.
        current_user: The authenticated user.
        candidate_service: The candidate service.

    Returns:
        Full candidate detail with CV documents.

    Raises:
        CandidateNotFoundError: If the candidate doesn't exist.
    """
    detail = await candidate_service.get_candidate(candidate_id)

    cv_docs = [
        CVDocumentResponse(
            id=doc.id,
            original_filename=doc.original_filename,
            mime_type=doc.mime_type,
            size_bytes=doc.size_bytes,
            uploaded_at=doc.uploaded_at,
            presigned_url=doc.presigned_url,
            processing_status=ProcessingStatus.COMPLETED,
        )
        for doc in detail.cv_documents
    ]

    candidate = detail.candidate
    return CandidateDetailResponse(
        id=candidate.id,
        name=candidate.name,
        email=candidate.email,
        phone=candidate.phone or "",
        skills=candidate.skills or [],
        experience=candidate.experience or [],
        education=candidate.education or [],
        summary=candidate.summary or "",
        status=candidate.status,
        confidence_score=candidate.confidence_score,
        source_email_message_id=candidate.source_email_message_id,
        rejection_reason=candidate.rejection_reason,
        rejected_at=candidate.rejected_at,
        accepted_at=candidate.accepted_at,
        archived_at=candidate.archived_at,
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
        cv_documents=cv_docs,
    )


# ---------------------------------------------------------------------------
# View CV presigned URL
# ---------------------------------------------------------------------------


@candidate_router.get(
    "/{candidate_id}/cv/{document_id}",
    response_model=CVPresignedUrlResponse,
)
async def get_cv_presigned_url(
    candidate_id: UUID,
    document_id: UUID,
    current_user: CurrentUserDep,
    session: AsyncSession = Depends(get_db_session),
) -> CVPresignedUrlResponse:
    """Get a presigned URL for downloading a candidate's CV document.

    Returns a presigned MinIO URL valid for 15 minutes along with
    file metadata.

    Args:
        candidate_id: UUID of the candidate.
        document_id: UUID of the CV document.
        current_user: The authenticated user.
        session: The async database session.

    Returns:
        Presigned URL and file metadata.

    Raises:
        CandidateNotFoundError: If the candidate doesn't exist.
        CVDocumentNotFoundError: If the document doesn't exist or
            doesn't belong to the candidate.
        CVFileNotFoundError: If the file is missing from MinIO.
        StorageServiceUnavailableError: If MinIO is unreachable.
    """
    # Verify candidate exists
    candidate_repo = CandidateRepository(session)
    candidate = await candidate_repo.get_by_id(candidate_id)
    if candidate is None:
        raise CandidateNotFoundError(f"Candidate not found: {candidate_id}")

    # Verify document exists and belongs to candidate
    cv_doc_repo = CVDocumentRepository(session)
    cv_doc = await cv_doc_repo.get_by_id(document_id)
    if cv_doc is None or cv_doc.candidate_id != candidate_id:
        raise CVDocumentNotFoundError(
            f"CV document not found or does not belong to candidate: {document_id}"
        )

    # Generate presigned URL
    minio_client = _get_minio_client()
    try:
        presigned_url = await minio_client.generate_presigned_url(cv_doc.file_path)
    except CVFileNotFoundError:
        raise
    except StorageServiceUnavailableError:
        raise
    except Exception as exc:
        raise StorageServiceUnavailableError(f"Failed to generate presigned URL: {exc}")

    return CVPresignedUrlResponse(
        presigned_url=presigned_url,
        filename=cv_doc.original_filename,
        mime_type=cv_doc.mime_type,
        size_bytes=cv_doc.size_bytes,
    )


# ---------------------------------------------------------------------------
# Schedule interview
# ---------------------------------------------------------------------------


@candidate_router.post(
    "/{candidate_id}/schedule-interview",
    response_model=CandidateResponse,
)
async def schedule_interview(
    candidate_id: UUID,
    body: ScheduleInterviewRequest,
    current_user: CurrentUserDep,
    candidate_service: CandidateServiceDep,
) -> CandidateResponse:
    """Schedule an interview for a candidate.

    Validates the status transition and interviewer IDs, then updates
    the candidate status to interview_scheduled.

    Args:
        candidate_id: UUID of the candidate.
        body: Interview scheduling parameters.
        current_user: The authenticated user.
        candidate_service: The candidate service.

    Returns:
        The updated candidate record.

    Raises:
        CandidateNotFoundError: If the candidate doesn't exist.
        InvalidStatusTransitionError: If the transition is not allowed.
        ValueError: If interviewer IDs are invalid.
    """
    candidate = await candidate_service.schedule_interview(
        candidate_id=candidate_id,
        interviewer_ids=body.interviewer_ids,
        date=body.date.isoformat() if body.date else None,
        time=body.time.isoformat() if body.time else None,
        duration_minutes=body.duration_minutes,
        notes=body.notes,
    )

    return CandidateResponse.model_validate(candidate)


# ---------------------------------------------------------------------------
# Send email
# ---------------------------------------------------------------------------


@candidate_router.post(
    "/{candidate_id}/send-email",
    status_code=200,
)
async def send_email(
    candidate_id: UUID,
    body: SendEmailRequest,
    current_user: CurrentUserDep,
    candidate_service: CandidateServiceDep,
) -> dict[str, str]:
    """Send an email to a candidate via Gmail.

    Validates Gmail connection and candidate email, then sends
    the email using the Gmail adapter.

    Args:
        candidate_id: UUID of the candidate.
        body: Email parameters (subject, body_html, optional template).
        current_user: The authenticated user.
        candidate_service: The candidate service.

    Returns:
        Success message.

    Raises:
        CandidateNotFoundError: If the candidate doesn't exist.
        GmailNotConnectedError: If Gmail is not connected.
        ValueError: If the candidate's email is invalid.
    """
    await candidate_service.send_email_to_candidate(
        candidate_id=candidate_id,
        subject=body.subject,
        body_html=body.body_html,
        template_name=body.template_name,
    )

    return {"message": "Email sent successfully"}


# ---------------------------------------------------------------------------
# Reject candidate
# ---------------------------------------------------------------------------


@candidate_router.post(
    "/{candidate_id}/reject",
    response_model=CandidateResponse,
)
async def reject_candidate(
    candidate_id: UUID,
    current_user: CurrentUserDep,
    candidate_service: CandidateServiceDep,
    body: RejectRequest | None = None,
) -> CandidateResponse:
    """Reject a candidate.

    Updates the candidate status to rejected and stores the optional
    rejection reason.

    Args:
        candidate_id: UUID of the candidate.
        current_user: The authenticated user.
        candidate_service: The candidate service.
        body: Optional rejection reason.

    Returns:
        The updated candidate record.

    Raises:
        CandidateNotFoundError: If the candidate doesn't exist.
        InvalidStatusTransitionError: If the transition is not allowed.
    """
    reason = body.reason if body else None
    candidate = await candidate_service.reject_candidate(
        candidate_id=candidate_id,
        reason=reason,
    )

    return CandidateResponse.model_validate(candidate)


# ---------------------------------------------------------------------------
# Accept candidate
# ---------------------------------------------------------------------------


@candidate_router.post(
    "/{candidate_id}/accept",
    response_model=CandidateResponse,
)
async def accept_candidate(
    candidate_id: UUID,
    current_user: CurrentUserDep,
    candidate_service: CandidateServiceDep,
) -> CandidateResponse:
    """Accept a candidate (pass interview).

    Updates the candidate status to accepted. Only allowed from
    interview_scheduled or reviewing status.

    Args:
        candidate_id: UUID of the candidate.
        current_user: The authenticated user.
        candidate_service: The candidate service.

    Returns:
        The updated candidate record.

    Raises:
        CandidateNotFoundError: If the candidate doesn't exist.
        InvalidStatusTransitionError: If the transition is not allowed.
    """
    candidate = await candidate_service.accept_candidate(candidate_id)
    return CandidateResponse.model_validate(candidate)


# ---------------------------------------------------------------------------
# Archive candidate
# ---------------------------------------------------------------------------


@candidate_router.post(
    "/{candidate_id}/archive",
    response_model=CandidateResponse,
)
async def archive_candidate(
    candidate_id: UUID,
    current_user: CurrentUserDep,
    candidate_service: CandidateServiceDep,
) -> CandidateResponse:
    """Archive a candidate.

    Updates the candidate status to archived. Idempotent for
    already-archived candidates. Not allowed from accepted status.

    Args:
        candidate_id: UUID of the candidate.
        current_user: The authenticated user.
        candidate_service: The candidate service.

    Returns:
        The updated candidate record.

    Raises:
        CandidateNotFoundError: If the candidate doesn't exist.
        InvalidStatusTransitionError: If the transition is not allowed.
    """
    candidate = await candidate_service.archive_candidate(candidate_id)
    return CandidateResponse.model_validate(candidate)
