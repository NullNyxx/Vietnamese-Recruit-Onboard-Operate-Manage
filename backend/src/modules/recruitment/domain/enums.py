"""Domain enums for the Recruitment CV Pipeline module.

Defines the enumeration types used across the recruitment module
for candidate lifecycle status, CV processing status, and email
intent classification.
"""

from enum import StrEnum


class CandidateStatus(StrEnum):
    """Lifecycle status of a candidate in the recruitment pipeline.

    Transitions follow a defined state machine:
    - new → reviewing, interview_scheduled, rejected, archived
    - reviewing → interview_scheduled, accepted, rejected, archived
    - interview_scheduled → accepted, rejected, archived
    - accepted → (no transitions)
    - rejected → (no transitions)
    - archived → (idempotent re-archive only)
    """

    NEW = "new"
    REVIEWING = "reviewing"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class ProcessingStatus(StrEnum):
    """Status of CV document processing through the pipeline.

    Tracks the progress of a CV document from initial upload
    through OCR extraction, LLM parsing, and final validation.
    """

    PENDING = "pending"
    OCR_PROCESSING = "ocr_processing"
    LLM_PARSING = "llm_parsing"
    COMPLETED = "completed"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"
    SKIPPED = "skipped"
    DISMISSED = "dismissed"
    UPLOAD_FAILED = "upload_failed"
    PERMANENTLY_FAILED = "permanently_failed"


class EmailIntent(StrEnum):
    """Classification intent for incoming emails.

    Determined by the AI Intent Classifier using LLM analysis
    of email subject, sender, snippet, and attachment metadata.
    """

    CV = "cv"
    PARTNER = "partner"
    EVENT = "event"
    INTERNAL = "internal"
    OTHER = "other"
