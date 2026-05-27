"""Domain exceptions for the Recruitment CV Pipeline module.

This module defines the exception hierarchy used throughout the recruitment
module to represent business rule violations, resource errors, and external
service failures.
"""


class RecruitmentError(Exception):
    """Base exception for the recruitment module.

    All domain-specific exceptions inherit from this class, enabling
    a single exception handler to catch any recruitment-related error
    and return a consistent JSON error response.

    Attributes:
        status_code: HTTP status code to return to the client.
        error_code: Machine-readable error identifier.
        message: Human-readable error description.
    """

    status_code: int = 500
    error_code: str = "RECRUITMENT_ERROR"
    message: str = "A recruitment module error occurred"

    def __init__(self, message: str | None = None) -> None:
        """Initialize RecruitmentError.

        Args:
            message: Optional custom message override. If not provided,
                the class-level default message is used.
        """
        if message is not None:
            self.message = message
        super().__init__(self.message)


class CandidateNotFoundError(RecruitmentError):
    """Candidate with given ID does not exist.

    Raised when an operation targets a candidate ID that cannot be
    found in the database.
    """

    status_code = 404
    error_code = "CANDIDATE_NOT_FOUND"
    message = "Candidate not found"


class CVDocumentNotFoundError(RecruitmentError):
    """CV document not found or doesn't belong to candidate.

    Raised when a CV document ID cannot be found in the database,
    or when the document does not belong to the specified candidate.
    """

    status_code = 404
    error_code = "CV_DOCUMENT_NOT_FOUND"
    message = "CV document not found"


class InvalidStatusTransitionError(RecruitmentError):
    """Attempted status transition is not allowed.

    Raised when an action would result in an invalid state machine
    transition for a candidate's lifecycle status.

    Attributes:
        current_status: The candidate's current status.
        attempted_action: The action that was attempted.
    """

    status_code = 409
    error_code = "INVALID_STATUS_TRANSITION"
    message = "Invalid status transition"

    def __init__(self, current_status: str, attempted_action: str) -> None:
        """Initialize InvalidStatusTransitionError.

        Args:
            current_status: The candidate's current status value.
            attempted_action: The action that was attempted on the candidate.
        """
        self.current_status = current_status
        self.attempted_action = attempted_action
        self.message = (
            f"Cannot perform '{attempted_action}' on candidate with status '{current_status}'"
        )
        super().__init__(self.message)


class CVFileNotFoundError(RecruitmentError):
    """File exists in DB but missing from MinIO storage.

    Raised when a CV document record exists in the database but
    the corresponding file cannot be found in MinIO object storage,
    indicating storage corruption or premature deletion.
    """

    status_code = 404
    error_code = "CV_FILE_MISSING"
    message = "CV file not found in storage"


class StorageServiceUnavailableError(RecruitmentError):
    """MinIO service is unreachable.

    Raised when the MinIO object storage service cannot be reached
    during upload, download, or presigned URL generation operations.
    """

    status_code = 502
    error_code = "STORAGE_SERVICE_UNAVAILABLE"
    message = "Storage service is unavailable"


class GmailNotConnectedError(RecruitmentError):
    """Gmail OAuth connection is not active.

    Raised when an operation requires Gmail access but the HR user's
    OAuth connection is not in 'connected' status.
    """

    status_code = 409
    error_code = "GMAIL_NOT_CONNECTED"
    message = "Gmail is not connected"


class PipelineTimeoutError(RecruitmentError):
    """CV processing pipeline exceeded maximum time.

    Raised when the overall CV processing pipeline (OCR + LLM parse +
    validation) exceeds the configured timeout (default 660 seconds).
    """

    status_code = 504
    error_code = "PIPELINE_TIMEOUT"
    message = "CV processing pipeline timed out"


class OCRExtractionError(RecruitmentError):
    """OCR text extraction failed.

    Raised when the olmOCR server fails to extract text from a CV
    document after all retry attempts are exhausted.
    """

    status_code = 502
    error_code = "OCR_EXTRACTION_FAILED"
    message = "OCR text extraction failed"


class LLMParseError(RecruitmentError):
    """LLM failed to parse CV into structured data.

    Raised when the LLM service fails to return valid structured
    JSON from the OCR text after all retry attempts, including
    the simplified prompt retry.
    """

    status_code = 502
    error_code = "LLM_PARSE_FAILED"
    message = "LLM CV parsing failed"
