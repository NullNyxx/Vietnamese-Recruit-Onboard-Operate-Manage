"""Whitelist file loader with hot-reload support.

Reads a plain text whitelist file (one email per line) and detects
file modifications via mtime checks for automatic reloading.
"""

import os
from pathlib import Path


class WhitelistLoader:
    """Loads and caches email addresses from a whitelist file.

    The loader reads a plain text file where each line contains one email
    address. Empty lines and lines starting with ``#`` (comments) are ignored.
    All emails are stored as lowercase for case-insensitive matching.

    File modification is detected via ``os.stat`` mtime checks. Call
    :meth:`get_emails` to retrieve the current set — it will automatically
    reload if the file has been modified since the last read.

    Args:
        file_path: Path to the whitelist text file.

    Raises:
        FileNotFoundError: If the whitelist file does not exist on initial load.
    """

    def __init__(self, file_path: str) -> None:
        self._file_path = Path(file_path)
        self._emails: set[str] = set()
        self._last_mtime: float = 0.0
        self._load()

    def _load(self) -> None:
        """Read the whitelist file and update the cached email set.

        Raises:
            FileNotFoundError: If the whitelist file does not exist.
        """
        if not self._file_path.exists():
            raise FileNotFoundError(f"Whitelist file not found: {self._file_path}")

        self._last_mtime = os.stat(self._file_path).st_mtime
        emails: set[str] = set()

        with open(self._file_path, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                emails.add(stripped.lower())

        self._emails = emails

    def _check_reload(self) -> None:
        """Reload the file if it has been modified since the last read."""
        try:
            current_mtime = os.stat(self._file_path).st_mtime
        except OSError:
            # File may have been removed; keep existing set
            return

        if current_mtime != self._last_mtime:
            self._load()

    def get_emails(self) -> set[str]:
        """Return the current set of whitelisted emails.

        Checks for file modifications and reloads if necessary before
        returning the cached set.

        Returns:
            A set of lowercase email addresses from the whitelist file.
        """
        self._check_reload()
        return self._emails

    def reload(self) -> None:
        """Force a reload of the whitelist file.

        Raises:
            FileNotFoundError: If the whitelist file does not exist.
        """
        self._load()
