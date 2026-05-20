"""Unit tests for the filename sanitizer utility."""

from src.modules.recruitment.infrastructure.filename_sanitizer import sanitize_filename


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""

    def test_normal_filename_unchanged(self):
        """A normal filename without invalid chars passes through."""
        assert sanitize_filename("resume.pdf") == "resume.pdf"

    def test_removes_path_separators(self):
        """Forward and back slashes are removed."""
        assert sanitize_filename("path/to/resume.pdf") == "pathtoresume.pdf"
        assert sanitize_filename("path\\to\\resume.pdf") == "pathtoresume.pdf"

    def test_removes_invalid_characters(self):
        """Characters invalid for object storage are removed."""
        assert sanitize_filename('file<name>.pdf') == "filename.pdf"
        assert sanitize_filename('file:name.pdf') == "filename.pdf"
        assert sanitize_filename('file"name.pdf') == "filename.pdf"
        assert sanitize_filename("file|name.pdf") == "filename.pdf"
        assert sanitize_filename("file?name.pdf") == "filename.pdf"
        assert sanitize_filename("file*name.pdf") == "filename.pdf"

    def test_removes_null_bytes_and_control_chars(self):
        """Null bytes and control characters are removed."""
        assert sanitize_filename("file\x00name.pdf") == "filename.pdf"
        assert sanitize_filename("file\x01name.pdf") == "filename.pdf"
        assert sanitize_filename("file\x1fname.pdf") == "filename.pdf"

    def test_truncates_to_255_characters(self):
        """Filenames exceeding 255 characters are truncated."""
        long_name = "a" * 300 + ".pdf"
        result = sanitize_filename(long_name)
        assert len(result) <= 255
        assert result.endswith(".pdf")

    def test_truncation_preserves_extension(self):
        """When truncating, the file extension is preserved."""
        long_name = "x" * 260 + ".docx"
        result = sanitize_filename(long_name)
        assert len(result) <= 255
        assert result.endswith(".docx")

    def test_empty_filename_returns_fallback(self):
        """An empty filename produces a fallback name."""
        assert sanitize_filename("") == "attachment"

    def test_all_invalid_chars_returns_fallback(self):
        """A filename made entirely of invalid chars produces a fallback."""
        assert sanitize_filename("///\\\\") == "attachment"
        assert sanitize_filename("<>:?*") == "attachment"

    def test_whitespace_only_returns_fallback(self):
        """A filename of only whitespace produces a fallback."""
        assert sanitize_filename("   ") == "attachment"

    def test_deduplication_with_numeric_suffix(self):
        """Duplicate filenames get _1, _2, etc. suffixes."""
        existing = ["resume.pdf"]
        result = sanitize_filename("resume.pdf", existing)
        assert result == "resume_1.pdf"

    def test_deduplication_increments(self):
        """Multiple duplicates get incrementing suffixes."""
        existing = ["resume.pdf", "resume_1.pdf"]
        result = sanitize_filename("resume.pdf", existing)
        assert result == "resume_2.pdf"

    def test_deduplication_with_no_extension(self):
        """Deduplication works for files without extensions."""
        existing = ["readme"]
        result = sanitize_filename("readme", existing)
        assert result == "readme_1"

    def test_no_deduplication_when_unique(self):
        """No suffix added when filename is already unique."""
        existing = ["other.pdf"]
        result = sanitize_filename("resume.pdf", existing)
        assert result == "resume.pdf"

    def test_preserves_unicode_characters(self):
        """Vietnamese and other Unicode characters are preserved."""
        assert sanitize_filename("hồ_sơ_ứng_viên.pdf") == "hồ_sơ_ứng_viên.pdf"

    def test_strips_leading_trailing_whitespace(self):
        """Leading and trailing whitespace is stripped."""
        assert sanitize_filename("  resume.pdf  ") == "resume.pdf"

    def test_strips_leading_dots(self):
        """Leading dots are stripped (hidden files)."""
        assert sanitize_filename("...resume.pdf") == "resume.pdf"

    def test_very_long_extension_treated_as_stem(self):
        """Extensions longer than 20 chars are treated as part of the stem."""
        long_ext = "file." + "x" * 25
        result = sanitize_filename(long_ext)
        # Should not split at the dot since extension is too long
        assert result == long_ext

    def test_none_existing_filenames_defaults_to_empty(self):
        """When existing_filenames is None, no deduplication occurs."""
        result = sanitize_filename("resume.pdf", None)
        assert result == "resume.pdf"

    def test_deduplication_respects_max_length(self):
        """Deduplication suffix doesn't push filename over 255 chars."""
        stem = "a" * 250
        filename = stem + ".pdf"
        # First sanitize truncates to 255
        first = sanitize_filename(filename)
        assert len(first) <= 255
        # Second with deduplication also stays within 255
        second = sanitize_filename(filename, [first])
        assert len(second) <= 255
        assert second != first
