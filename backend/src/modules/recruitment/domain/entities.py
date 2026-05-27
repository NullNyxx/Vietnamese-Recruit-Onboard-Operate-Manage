"""Domain entities for the Recruitment CV Pipeline module.

Defines the SQLModel table classes for Candidate, CVDocument, and
RecruitmentAuditLog that map to PostgreSQL tables used for recruitment
pipeline management.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class Candidate(SQLModel, table=True):
    """Represents a recruitment candidate created from CV processing.

    Candidates are created automatically when a CV is parsed with
    sufficient confidence, or manually by HR during review. Each
    candidate has a lifecycle status tracked by CandidateStatus enum.
    Deduplication is performed by email address.
    """

    __tablename__ = "candidates"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(max_length=255, nullable=False)
    email: str = Field(max_length=255, nullable=False, index=True)
    phone: str = Field(default="", max_length=20)
    skills: list[str] = Field(default_factory=list, sa_column=Column(JSONB, nullable=False))
    experience: list[dict] = Field(default_factory=list, sa_column=Column(JSONB, nullable=False))
    education: list[dict] = Field(default_factory=list, sa_column=Column(JSONB, nullable=False))
    summary: str = Field(default="", max_length=500)
    parsed_cv_json: dict | None = Field(default=None, sa_column=Column(JSONB))
    status: str = Field(default="new", max_length=30, nullable=False, index=True)
    confidence_score: float = Field(default=0.0, nullable=False)
    source_email_message_id: UUID | None = Field(default=None, foreign_key="email_messages.id")
    rejection_reason: str | None = Field(default=None, max_length=1000)
    rejected_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    accepted_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    archived_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class CVDocument(SQLModel, table=True):
    """Represents a CV file stored in MinIO object storage.

    Tracks the lifecycle of a CV document from upload through OCR
    extraction and LLM parsing. Each document is linked to a Gmail
    message and optionally to a Candidate record once processing
    completes successfully.
    """

    __tablename__ = "cv_documents"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    candidate_id: UUID | None = Field(default=None, foreign_key="candidates.id", index=True)
    gmail_message_id: str = Field(max_length=255, nullable=False, index=True)
    original_filename: str = Field(max_length=255, nullable=False)
    mime_type: str = Field(max_length=100, nullable=False)
    size_bytes: int = Field(nullable=False)
    file_path: str = Field(max_length=500, nullable=False)
    ocr_output: str | None = Field(default=None)
    parsed_cv_data: dict | None = Field(default=None, sa_column=Column(JSONB))
    confidence_score: float | None = Field(default=None)
    processing_status: str = Field(default="pending", max_length=30, nullable=False, index=True)
    processing_error: str | None = Field(default=None, max_length=500)
    validation_errors: list[dict] | None = Field(default=None, sa_column=Column(JSONB))
    retry_count: int = Field(default=0, nullable=False)
    uploaded_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class RecruitmentAuditLog(SQLModel, table=True):
    """Audit log entry for recruitment module operations.

    Records all significant actions performed within the recruitment
    pipeline including intent classification, CV parsing, candidate
    status changes, and data retention operations. Ensures PII is
    never stored in audit entries.
    """

    __tablename__ = "recruitment_audit_logs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID | None = Field(default=None, foreign_key="users.id", index=True)
    operation_type: str = Field(max_length=50, nullable=False, index=True)
    entity_type: str = Field(max_length=50, nullable=False)
    entity_id: UUID | None = Field(default=None, index=True)
    previous_value: dict | None = Field(default=None, sa_column=Column(JSONB))
    new_value: dict | None = Field(default=None, sa_column=Column(JSONB))
    change_summary: str | None = Field(default=None, max_length=500)
    model_name: str | None = Field(default=None, max_length=100)
    token_usage: dict | None = Field(default=None, sa_column=Column(JSONB))
    latency_ms: int | None = Field(default=None)
    success: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True),
    )
