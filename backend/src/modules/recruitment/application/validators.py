"""Attachment validation logic for the Recruitment CV Pipeline.

Validates file MIME types and sizes against allowed constraints before
processing attachments through the CV pipeline.
"""

from dataclasses import dataclass

# Standalone constant for testing and reference
MAX_FILE_SIZE_BYTES: int = 10_485_760  # 10MB

ALLOWED_MIME_TYPES: frozenset[str] = frozenset(
    {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "image/jpeg",
        "image/png",
    }
)


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Result of an attachment validation check.

    Attributes:
        is_valid: Whether the attachment passes all validation checks.
        error_message: Human-readable error description if invalid, None otherwise.
    """

    is_valid: bool
    error_message: str | None = None


def validate_attachment(
    mime_type: str,
    size_bytes: int,
    *,
    max_file_size_bytes: int | None = None,
) -> ValidationResult:
    """Validate an attachment's MIME type and file size.

    Checks that the MIME type is in the allowed set and that the file
    size does not exceed the configured maximum.

    Args:
        mime_type: The MIME type of the attachment (e.g. "application/pdf").
        size_bytes: The size of the attachment in bytes.
        max_file_size_bytes: Optional override for the maximum allowed file size.
            Defaults to MAX_FILE_SIZE_BYTES (10MB) if not provided.

    Returns:
        ValidationResult with is_valid=True if the attachment is acceptable,
        or is_valid=False with an error_message describing the issue.
    """
    limit = max_file_size_bytes if max_file_size_bytes is not None else MAX_FILE_SIZE_BYTES

    if mime_type not in ALLOWED_MIME_TYPES:
        allowed_list = ", ".join(sorted(ALLOWED_MIME_TYPES))
        return ValidationResult(
            is_valid=False,
            error_message=(
                f"MIME type '{mime_type}' is not allowed. Allowed types: {allowed_list}"
            ),
        )

    if size_bytes > limit:
        limit_mb = limit / (1024 * 1024)
        size_mb = size_bytes / (1024 * 1024)
        return ValidationResult(
            is_valid=False,
            error_message=(
                f"File size {size_mb:.2f}MB exceeds maximum allowed size of {limit_mb:.2f}MB"
            ),
        )

    return ValidationResult(is_valid=True)
