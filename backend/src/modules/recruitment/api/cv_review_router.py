"""FastAPI router for the CV Review queue endpoints.

Provides endpoints for HR to manage CV documents that need manual review:
listing the review queue, submitting corrections, retrying LLM parse,
and dismissing documents from the queue.

Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7, 14.8
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.container import get_current_user, get_db_session
from src.modules.identity.domain.entities import User
from src.modules.recruitment.application.review_service import (
    ReviewService,
    ReviewValidationError,
)
from src.modules.recruitment.domain.exceptions import CVDocumentNotFoundError
from src.modules.recruitment.domain.value_objects import (
    EducationItem,
    ExperienceItem,
    ParsedCV,
)

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class ParsedCVInput(BaseModel):
    """Request body for submitting corrected CV data.

    HR uses this to provide corrected structured data for a CV document
    that failed automatic parsing or had low confidence.
    """

    name: str = Field(min_length=1, max_length=200)
    email: EmailStr = Field(max_length=254)
    phone: str = Field(default="", max_length=20)
    skills: list[str] = Field(default_factory=list, max_length=50)
    experience: list[ExperienceItem] = Field(default_factory=list, max_length=20)
    education: list[EducationItem] = Field(default_factory=list, max_length=10)
    summary: str = Field(default="", max_length=500)


class CVReviewItemResponse(BaseModel):
    """Response model for a single CV document in the review queue."""

    id: UUID
    candidate_id: UUID | None = None
    gmail_message_id: str
    original_filename: str
    mime_type: str
    size_bytes: int
    file_path: str
    ocr_output: str | None = None
    parsed_cv_data: dict | None = None
    confidence_score: float | None = None
    processing_status: str
    processing_error: str | None = None
    validation_errors: list[dict] | None = None
    retry_count: int = 0
    uploaded_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CVReviewListResponse(BaseModel):
    """Paginated response for the review queue listing."""

    items: list[CVReviewItemResponse]
    total: int
    page: int
    page_size: int


class CandidateResponse(BaseModel):
    """Minimal candidate response returned after correction submission."""

    id: UUID
    name: str
    email: str
    phone: str = ""
    status: str
    confidence_score: float = 0.0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Dependency injection
# ---------------------------------------------------------------------------

CurrentUserDep = Annotated[User, Depends(get_current_user)]


async def get_review_service(
    session: AsyncSession = Depends(get_db_session),
) -> ReviewService:
    """Provide a ReviewService instance with all dependencies injected.

    Delegates to the recruitment container for proper dependency wiring.

    Args:
        session: The async database session from DI.

    Returns:
        A ReviewService instance with all dependencies injected.
    """
    from src.modules.recruitment.container import get_review_service as _get_review_service

    return await _get_review_service(session=session)


ReviewServiceDep = Annotated[ReviewService, Depends(get_review_service)]


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

cv_review_router = APIRouter(
    prefix="/api/recruitment/cv-review",
    tags=["cv-review"],
)


@cv_review_router.get("", response_model=CVReviewListResponse)
async def list_review_queue(
    current_user: CurrentUserDep,
    review_service: ReviewServiceDep,
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> CVReviewListResponse:
    """List CV documents needing manual review with pagination.

    Returns documents with processing_status "needs_review" or "failed",
    sorted by created_at descending (newest first).

    Args:
        current_user: The authenticated user.
        review_service: The review service.
        page: Page number (1-indexed).
        page_size: Number of items per page (1–100).

    Returns:
        Paginated list of CV documents in the review queue.
    """
    result = await review_service.list_review_queue(
        page=page,
        page_size=page_size,
    )

    return CVReviewListResponse(
        items=[CVReviewItemResponse.model_validate(doc) for doc in result.documents],
        total=result.total_count,
        page=result.page,
        page_size=result.page_size,
    )


@cv_review_router.put(
    "/{cv_document_id}",
    response_model=CandidateResponse,
)
async def submit_correction(
    cv_document_id: UUID,
    body: ParsedCVInput,
    current_user: CurrentUserDep,
    review_service: ReviewServiceDep,
) -> CandidateResponse | JSONResponse:
    """Submit corrected CV data for a document in the review queue.

    HR provides corrected structured data which is validated, then used
    to create or update a Candidate record. The CV document's processing
    status is set to "completed".

    Args:
        cv_document_id: UUID of the CV document to correct.
        body: The corrected ParsedCV data from HR.
        current_user: The authenticated user.
        review_service: The review service.

    Returns:
        The created or updated Candidate record.

    Raises:
        404: If the CV document is not found.
        422: If the corrected data fails validation.
    """
    # Convert request body to domain value object
    parsed_cv = ParsedCV(
        name=body.name,
        email=body.email,
        phone=body.phone,
        skills=body.skills,
        experience=body.experience,
        education=body.education,
        summary=body.summary,
    )

    try:
        candidate = await review_service.submit_correction(
            cv_document_id=cv_document_id,
            corrected_data=parsed_cv,
        )
    except CVDocumentNotFoundError as exc:
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                }
            },
        )
    except ReviewValidationError as exc:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Corrected data validation failed",
                    "details": exc.errors,
                }
            },
        )

    return CandidateResponse.model_validate(candidate)


@cv_review_router.post(
    "/{cv_document_id}/retry",
    response_model=CVReviewItemResponse,
)
async def retry_parse(
    cv_document_id: UUID,
    current_user: CurrentUserDep,
    review_service: ReviewServiceDep,
) -> CVReviewItemResponse | JSONResponse:
    """Retry LLM parse for a CV document in the review queue.

    Re-runs the LLM parse step on the stored OCR text with a 60 second
    timeout. If the retry fails or times out, the processing status is
    set back to "needs_review".

    Args:
        cv_document_id: UUID of the CV document to retry parsing for.
        current_user: The authenticated user.
        review_service: The review service.

    Returns:
        The updated CV document with new processing status.

    Raises:
        404: If the CV document is not found.
    """
    try:
        cv_document = await review_service.retry_parse(cv_document_id)
    except CVDocumentNotFoundError as exc:
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                }
            },
        )

    return CVReviewItemResponse.model_validate(cv_document)


@cv_review_router.delete(
    "/{cv_document_id}/dismiss",
    status_code=204,
)
async def dismiss_from_queue(
    cv_document_id: UUID,
    current_user: CurrentUserDep,
    review_service: ReviewServiceDep,
) -> None:
    """Dismiss a CV document from the review queue.

    Marks the document as "dismissed", removing it from the review queue
    without creating a Candidate record.

    Args:
        cv_document_id: UUID of the CV document to dismiss.
        current_user: The authenticated user.
        review_service: The review service.

    Returns:
        204 No Content on success.

    Raises:
        CVDocumentNotFoundError: If the CV document is not found (404).
    """
    await review_service.dismiss(cv_document_id)
