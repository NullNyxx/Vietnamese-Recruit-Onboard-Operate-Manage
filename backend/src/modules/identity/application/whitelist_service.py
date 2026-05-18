"""Whitelist service for email access control.

Provides case-insensitive email matching against a file-based whitelist
with automatic hot-reload when the file changes.
"""

from src.modules.identity.infrastructure.whitelist_loader import WhitelistLoader


class WhitelistService:
    """Email whitelist access control with hot-reload.

    Wraps :class:`WhitelistLoader` to provide a simple interface for
    checking whether an email is authorized. The underlying loader
    automatically detects file modifications via mtime checks.

    Args:
        file_path: Path to the whitelist text file.

    Raises:
        FileNotFoundError: If the whitelist file does not exist on construction.
    """

    def __init__(self, file_path: str) -> None:
        self._loader = WhitelistLoader(file_path)

    def is_allowed(self, email: str) -> bool:
        """Check if an email is in the whitelist.

        Performs a case-insensitive exact match against the current
        whitelist. The underlying file is automatically reloaded if
        it has been modified since the last check.

        Args:
            email: The email address to check.

        Returns:
            True if the email is in the whitelist, False otherwise.
        """
        return email.lower() in self._loader.get_emails()

    async def reload(self) -> None:
        """Reload the whitelist from file.

        Forces a re-read of the whitelist file regardless of whether
        the mtime has changed.

        Raises:
            FileNotFoundError: If the whitelist file does not exist.
        """
        self._loader.reload()
