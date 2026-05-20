"""Unit tests for attachment validation logic."""

from src.modules.recruitment.application.validators import (
    ALLOWED_MIME_TYPES,
    MAX_FILE_SIZE_BYTES,
    ValidationResult,
    validate_attachment,
)


class TestValidateAttachment:
    """Tests for validate_attachment function."""

    # --- Valid cases ---

    def test_valid_pdf(self):
        """A PDF within size limit passes validation."""
        result = validate_attachment("application/pdf", 1_000_000)
        assert result == ValidationResult(is_valid=True)

    def test_valid_docx(self):
        """A DOCX within size limit passes validation."""
        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        result = validate_attachment(mime, 5_000_000)
        assert result == ValidationResult(is_valid=True)

    def test_valid_jpeg(self):
        """A JPEG within size limit passes validation."""
        result = validate_attachment("image/jpeg", 2_000_000)
        assert result == ValidationResult(is_valid=True)

    def test_valid_png(self):
        """A PNG within size limit passes validation."""
        result = validate_attachment("image/png", 3_000_000)
        assert result == ValidationResult(is_valid=True)

    def test_exactly_max_size(self):
        """A file exactly at the 10MB limit passes validation."""
        result = validate_attachment("application/pdf", MAX_FILE_SIZE_BYTES)
        assert result.is_valid is True

    def test_zero_size_file(self):
        """A zero-byte file with valid MIME type passes validation."""
        result = validate_attachment("application/pdf", 0)
        assert result.is_valid is True

    # --- Invalid MIME type cases ---

    def test_invalid_mime_type_text(self):
        """A text/plain file is rejected."""
        result = validate_attachment("text/plain", 100)
        assert result.is_valid is False
        assert "text/plain" in result.error_message
        assert "not allowed" in result.error_message

    def test_invalid_mime_type_html(self):
        """An HTML file is rejected."""
        result = validate_attachment("text/html", 100)
        assert result.is_valid is False

    def test_invalid_mime_type_zip(self):
        """A ZIP file is rejected."""
        result = validate_attachment("application/zip", 100)
        assert result.is_valid is False

    def test_invalid_mime_type_gif(self):
        """A GIF image is rejected (only JPEG and PNG allowed)."""
        result = validate_attachment("image/gif", 100)
        assert result.is_valid is False

    def test_invalid_mime_type_empty_string(self):
        """An empty MIME type string is rejected."""
        result = validate_attachment("", 100)
        assert result.is_valid is False

    # --- Invalid size cases ---

    def test_exceeds_max_size_by_one_byte(self):
        """A file one byte over the limit is rejected."""
        result = validate_attachment("application/pdf", MAX_FILE_SIZE_BYTES + 1)
        assert result.is_valid is False
        assert "exceeds" in result.error_message

    def test_large_file_rejected(self):
        """A 20MB file is rejected."""
        result = validate_attachment("application/pdf", 20 * 1024 * 1024)
        assert result.is_valid is False

    # --- Custom max_file_size_bytes ---

    def test_custom_max_size_allows_larger(self):
        """A custom larger limit allows bigger files."""
        result = validate_attachment(
            "application/pdf",
            15_000_000,
            max_file_size_bytes=20_000_000,
        )
        assert result.is_valid is True

    def test_custom_max_size_restricts_smaller(self):
        """A custom smaller limit rejects files that would pass default."""
        result = validate_attachment(
            "application/pdf",
            5_000_000,
            max_file_size_bytes=1_000_000,
        )
        assert result.is_valid is False

    # --- MIME type checked before size ---

    def test_invalid_mime_reported_even_if_size_also_invalid(self):
        """MIME type error is reported first when both MIME and size are invalid."""
        result = validate_attachment("text/plain", MAX_FILE_SIZE_BYTES + 1)
        assert result.is_valid is False
        assert "MIME type" in result.error_message

    # --- Constants ---

    def test_max_file_size_is_10mb(self):
        """MAX_FILE_SIZE_BYTES constant equals 10MB."""
        assert MAX_FILE_SIZE_BYTES == 10 * 1024 * 1024
        assert MAX_FILE_SIZE_BYTES == 10_485_760

    def test_allowed_mime_types_contains_four_types(self):
        """Exactly four MIME types are allowed."""
        assert len(ALLOWED_MIME_TYPES) == 4
        assert "application/pdf" in ALLOWED_MIME_TYPES
        assert (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            in ALLOWED_MIME_TYPES
        )
        assert "image/jpeg" in ALLOWED_MIME_TYPES
        assert "image/png" in ALLOWED_MIME_TYPES
