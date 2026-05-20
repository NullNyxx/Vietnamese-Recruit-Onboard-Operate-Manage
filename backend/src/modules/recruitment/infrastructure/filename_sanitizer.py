"""Filename sanitizer for CV attachments stored in MinIO.

Removes invalid characters, truncates to 255 characters, and disambiguates
duplicate filenames within the same email with numeric suffixes.
"""

import os
import re

# Characters invalid for object storage keys and filesystem paths
_INVALID_CHARS_PATTERN = re.compile(r'[/\\<>:"|?*\x00-\x1f]')

_MAX_FILENAME_LENGTH = 255


def sanitize_filename(
    filename: str,
    existing_filenames: list[str] | None = None,
) -> str:
    """Sanitize a filename for safe storage in MinIO.

    Args:
        filename: The original filename from the email attachment.
        existing_filenames: List of already-sanitized filenames from the same email,
            used for deduplication with numeric suffixes.

    Returns:
        A sanitized filename that is safe for object storage, truncated to 255
        characters maximum, with duplicates disambiguated via _1, _2, etc. suffixes.
    """
    if existing_filenames is None:
        existing_filenames = []

    # Strip leading/trailing whitespace
    sanitized = filename.strip()

    # Remove invalid characters
    sanitized = _INVALID_CHARS_PATTERN.sub("", sanitized)

    # Strip any remaining leading/trailing whitespace or dots (hidden files on Unix)
    sanitized = sanitized.strip(". ")

    # If nothing remains after sanitization, use a fallback name
    if not sanitized:
        sanitized = "attachment"

    # Split into stem and extension
    stem, ext = _split_filename(sanitized)

    # Truncate to fit within max length while preserving extension
    sanitized = _truncate(stem, ext)

    # Disambiguate duplicates
    sanitized = _disambiguate(sanitized, existing_filenames)

    return sanitized


def _split_filename(filename: str) -> tuple[str, str]:
    """Split filename into stem and extension.

    Handles edge cases like files with no extension, multiple dots,
    and very long extensions (treats extensions > 20 chars as part of stem).
    """
    # Use os.path.splitext for standard splitting
    stem, ext = os.path.splitext(filename)

    # If extension is unreasonably long (> 20 chars including dot), treat it as part of stem
    if len(ext) > 21:  # 20 chars + the dot
        stem = filename
        ext = ""

    # If stem is empty but we have an extension (e.g., ".pdf"), use extension as stem
    if not stem and ext:
        stem = ext
        ext = ""

    return stem, ext


def _truncate(stem: str, ext: str) -> str:
    """Truncate filename to fit within 255 characters while preserving extension."""
    max_stem_length = _MAX_FILENAME_LENGTH - len(ext)

    if max_stem_length <= 0:
        # Extension itself is too long; truncate the whole thing
        return (stem + ext)[:_MAX_FILENAME_LENGTH]

    if len(stem) > max_stem_length:
        stem = stem[:max_stem_length]

    return stem + ext


def _disambiguate(filename: str, existing_filenames: list[str]) -> str:
    """Add numeric suffix if filename already exists in the list.

    Produces: filename.ext -> filename_1.ext -> filename_2.ext, etc.
    """
    if filename not in existing_filenames:
        return filename

    stem, ext = os.path.splitext(filename)
    # Handle very long extensions the same way
    if len(ext) > 21:
        stem = filename
        ext = ""

    counter = 1
    while True:
        candidate = f"{stem}_{counter}{ext}"
        # Ensure the disambiguated name still fits within max length
        if len(candidate) > _MAX_FILENAME_LENGTH:
            # Shorten stem to make room for suffix
            suffix = f"_{counter}{ext}"
            max_stem = _MAX_FILENAME_LENGTH - len(suffix)
            if max_stem <= 0:
                candidate = candidate[:_MAX_FILENAME_LENGTH]
            else:
                candidate = stem[:max_stem] + suffix
        if candidate not in existing_filenames:
            return candidate
        counter += 1
