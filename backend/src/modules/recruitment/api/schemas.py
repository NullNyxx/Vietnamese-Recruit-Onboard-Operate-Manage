"""Pydantic v2 request/response schemas for the Recruitment CV Pipeline API.

Defines data transfer objects used by the recruitment router endpoints
for structured data validation and serialization.
"""

from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from src.modules.recruitment.domain.enums import CandidateStatus, ProcessingStatus
from src.modules.recruitment.domain.value_objects import EducationItem, ExperienceItem

# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class CandidateListParams(BaseModel):
    """Query parameters for listing candidates with pagination, search, and filters.

    Attributes:
        page: Page number (1-indexed).
        page_size: Number of items per page (1–100).
        search: Free-text search across name, email, phone, skills.
        status: Filter by one or more candidate statuses.
        from_date: Filter candidates created on or after this date.
        to_date: Filter candidates created on or before this date.
        min_confidence: Minimum confidence score filter (0.0–1.0).
        skills: Comma-separated skills filter (OR logic).
    """

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    search: str | None = Field(default=None, min_length=1, max_length=200)
    status: list[CandidateStatus] | None = None
    from_date: date | None = None
    to_date: date | None = None
    min_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    skills: str | None = None  # comma-separated


class ScheduleInterviewRequest(BaseModel):
    """Request schema for scheduling an interview with a candidate.

    Attributes:
        date: Interview date (must be a future date).
        time: Interview start time.
        duration_minutes: Duration in minutes (15–180).
        interviewer_ids: List of employee UUIDs conducting the interview (1–10).
        notes: Optional notes for the interview (max 1000 chars).
    """

    date: date
    time: time
    duration_minutes: int = Field(ge=15, le=180)
    interviewer_ids: list[UUID] = Field(min_length=1, max_length=10)
    notes: str | None = Field(default=None, max_length=1000)


class SendEmailRequest(BaseModel):
    """Request schema for sending an email to a candidate.

    Attributes:
        subject: Email subject line (1–500 characters).
        body_html: HTML body content (max 100,000 characters).
        template_name: Optional email template name to use instead of body_html.
    """

    subject: str = Field(min_length=1, max_length=500)
    body_html: str = Field(max_length=100_000)
    template_name: str | None = Field(default=None, max_length=100)


class RejectRequest(BaseModel):
    """Request schema for rejecting a candidate.

    Attributes:
        reason: Optional rejection reason (max 1000 characters).
    """

    reason: str | None = Field(default=None, max_length=1000)


class ParsedCVInput(BaseModel):
    """Request schema for submitting corrected CV data during manual review.

    Attributes:
        name: Candidate name (1–200 characters).
        email: Candidate email (valid format, max 254 characters).
        phone: Phone number (optional, max 20 characters).
        skills: List of skill strings (max 50 items).
        experience: List of experience entries (max 20 items).
        education: List of education entries (max 10 items).
        summary: Brief candidate summary (max 500 characters).
    """

    name: str = Field(min_length=1, max_length=200)
    email: EmailStr = Field(max_length=254)
    phone: str = Field(default="", max_length=20)
    skills: list[str] = Field(default_factory=list, max_length=50)
    experience: list[ExperienceItem] = Field(default_factory=list, max_length=20)
    education: list[EducationItem] = Field(default_factory=list, max_length=10)
    summary: str = Field(default="", max_length=500)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class CVDocumentResponse(BaseModel):
    """Response schema for a CV document linked to a candidate.

    Attributes:
        id: Unique document identifier.
        original_filename: Original uploaded filename.
        mime_type: MIME type of the file.
        size_bytes: File size in bytes.
        uploaded_at: When the file was uploaded.
        presigned_url: Pre-signed MinIO download URL (valid 15 min), or None.
        processing_status: Current processing status of the document.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_filename: str
    mime_type: str
    size_bytes: int
    uploaded_at: datetime
    presigned_url: str | None = None
    processing_status: ProcessingStatus


class CandidateListItemResponse(BaseModel):
    """Response schema for a single candidate in the list view.

    Attributes:
        id: Candidate UUID.
        name: Candidate full name.
        email: Candidate email address.
        phone: Candidate phone number.
        skills: Up to the first 5 skills.
        status: Current lifecycle status.
        confidence_score: Parse confidence score (0.0–1.0).
        created_at: When the candidate was created.
        has_cv: Whether the candidate has at least one CV document.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: str
    phone: str = ""
    skills: list[str] = Field(default_factory=list)
    status: CandidateStatus
    confidence_score: float = 0.0
    created_at: datetime
    has_cv: bool = False


class CandidateListResponse(BaseModel):
    """Paginated response for the candidate list endpoint.

    Attributes:
        candidates: List of candidate records for the current page.
        total_count: Total number of matching candidates.
        page: Current page number (1-indexed).
        page_size: Number of items per page.
    """

    candidates: list[CandidateListItemResponse]
    total_count: int
    page: int
    page_size: int


class CandidateDetailResponse(BaseModel):
    """Full candidate detail response including CV documents.

    Attributes:
        id: Candidate UUID.
        name: Candidate full name.
        email: Candidate email address.
        phone: Candidate phone number.
        skills: Full list of skills.
        experience: List of experience objects.
        education: List of education objects.
        summary: Candidate summary.
        status: Current lifecycle status.
        confidence_score: Confidence score (0.0–1.0).
        source_email_message_id: UUID of the source email, if available.
        rejection_reason: Rejection reason if rejected.
        rejected_at: Rejection timestamp.
        accepted_at: Acceptance timestamp.
        archived_at: Archive timestamp.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
        cv_documents: List of linked CV documents with presigned URLs.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: str
    phone: str = ""
    skills: list[str] = Field(default_factory=list)
    experience: list[dict] = Field(default_factory=list)
    education: list[dict] = Field(default_factory=list)
    summary: str = ""
    status: CandidateStatus
    confidence_score: float = 0.0
    source_email_message_id: UUID | None = None
    rejection_reason: str | None = None
    rejected_at: datetime | None = None
    accepted_at: datetime | None = None
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    cv_documents: list[CVDocumentResponse] = Field(default_factory=list)


class CVReviewItemResponse(BaseModel):
    """Response schema for a CV document in the review queue.

    Attributes:
        id: CV document identifier.
        original_filename: Original uploaded filename.
        mime_type: MIME type of the file.
        size_bytes: File size in bytes.
        uploaded_at: When the file was uploaded.
        processing_status: Current processing status.
        processing_error: Error message if processing failed.
        validation_errors: List of validation error details.
        ocr_output: Extracted OCR text (if available).
        parsed_cv_data: Partial parsed CV data (if available).
        presigned_url: Pre-signed MinIO download URL, or None.
        candidate_id: Linked candidate ID, if any.
        gmail_message_id: Source Gmail message ID.
        created_at: When the document was created.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_filename: str
    mime_type: str
    size_bytes: int
    uploaded_at: datetime
    processing_status: ProcessingStatus
    processing_error: str | None = None
    validation_errors: list[dict] | None = None
    ocr_output: str | None = None
    parsed_cv_data: dict | None = None
    presigned_url: str | None = None
    candidate_id: UUID | None = None
    gmail_message_id: str
    created_at: datetime


class MetricsResponse(BaseModel):
    """Response schema for CV processing pipeline metrics.

    Attributes:
        average_processing_time_ms: Average time to process a CV in milliseconds.
        success_rate: Ratio of successfully processed CVs (0.0–1.0).
        failure_rate: Ratio of failed CV processing attempts (0.0–1.0).
        queue_depth: Number of CVs currently pending processing.
    """

    average_processing_time_ms: float
    success_rate: float
    failure_rate: float
    queue_depth: int


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper.

    Attributes:
        items: List of items for the current page.
        total_count: Total number of matching items.
        page: Current page number (1-indexed).
        page_size: Number of items per page.
    """

    items: list
    total_count: int
    page: int
    page_size: int


class CandidateResponse(BaseModel):
    """Response schema for a single candidate (used by action endpoints).

    Attributes:
        id: Candidate UUID.
        name: Candidate full name.
        email: Candidate email address.
        phone: Candidate phone number.
        skills: List of skills.
        status: Current lifecycle status.
        confidence_score: Confidence score (0.0–1.0).
        rejection_reason: Rejection reason if rejected.
        rejected_at: Rejection timestamp.
        accepted_at: Acceptance timestamp.
        archived_at: Archive timestamp.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: str
    phone: str = ""
    skills: list[str] = Field(default_factory=list)
    status: CandidateStatus
    confidence_score: float = 0.0
    rejection_reason: str | None = None
    rejected_at: datetime | None = None
    accepted_at: datetime | None = None
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CVPresignedUrlResponse(BaseModel):
    """Response schema for a CV presigned URL request.

    Attributes:
        presigned_url: Presigned MinIO download URL (valid 15 minutes).
        filename: Original filename.
        mime_type: MIME type of the file.
        size_bytes: File size in bytes.
    """

    presigned_url: str
    filename: str
    mime_type: str
    size_bytes: int
