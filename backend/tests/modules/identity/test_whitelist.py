"""Unit tests for WhitelistLoader and WhitelistService."""

import os
import time
from pathlib import Path

import pytest

from src.modules.identity.application.whitelist_service import WhitelistService
from src.modules.identity.infrastructure.whitelist_loader import WhitelistLoader


@pytest.fixture
def whitelist_file(tmp_path: Path) -> Path:
    """Create a temporary whitelist file with sample emails."""
    file = tmp_path / "whitelist.txt"
    file.write_text(
        "alice@example.com\n"
        "bob@example.com\n"
        "charlie@example.com\n",
        encoding="utf-8",
    )
    return file


@pytest.fixture
def whitelist_file_with_comments(tmp_path: Path) -> Path:
    """Create a whitelist file with comments and empty lines."""
    file = tmp_path / "whitelist.txt"
    file.write_text(
        "# This is a comment\n"
        "\n"
        "alice@example.com\n"
        "# Another comment\n"
        "\n"
        "bob@example.com\n"
        "\n",
        encoding="utf-8",
    )
    return file


@pytest.fixture
def empty_whitelist_file(tmp_path: Path) -> Path:
    """Create an empty whitelist file."""
    file = tmp_path / "whitelist.txt"
    file.write_text("", encoding="utf-8")
    return file


class TestWhitelistLoader:
    """Tests for WhitelistLoader."""

    def test_loads_emails_from_file(self, whitelist_file: Path) -> None:
        loader = WhitelistLoader(str(whitelist_file))
        emails = loader.get_emails()
        assert emails == {"alice@example.com", "bob@example.com", "charlie@example.com"}

    def test_stores_emails_as_lowercase(self, tmp_path: Path) -> None:
        file = tmp_path / "whitelist.txt"
        file.write_text("Alice@Example.COM\nBOB@EXAMPLE.COM\n", encoding="utf-8")
        loader = WhitelistLoader(str(file))
        emails = loader.get_emails()
        assert emails == {"alice@example.com", "bob@example.com"}

    def test_ignores_comments(self, whitelist_file_with_comments: Path) -> None:
        loader = WhitelistLoader(str(whitelist_file_with_comments))
        emails = loader.get_emails()
        assert emails == {"alice@example.com", "bob@example.com"}

    def test_ignores_empty_lines(self, whitelist_file_with_comments: Path) -> None:
        loader = WhitelistLoader(str(whitelist_file_with_comments))
        emails = loader.get_emails()
        assert "" not in emails

    def test_empty_file_returns_empty_set(self, empty_whitelist_file: Path) -> None:
        loader = WhitelistLoader(str(empty_whitelist_file))
        emails = loader.get_emails()
        assert emails == set()

    def test_file_not_found_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Whitelist file not found"):
            WhitelistLoader(str(tmp_path / "nonexistent.txt"))

    def test_detects_file_modification(self, whitelist_file: Path) -> None:
        loader = WhitelistLoader(str(whitelist_file))
        assert "alice@example.com" in loader.get_emails()
        assert "new@example.com" not in loader.get_emails()

        # Ensure mtime changes (some filesystems have 1-second resolution)
        time.sleep(0.05)
        whitelist_file.write_text(
            "new@example.com\nalice@example.com\n", encoding="utf-8"
        )
        # Force a different mtime by touching the file
        os.utime(whitelist_file, (time.time() + 1, time.time() + 1))

        emails = loader.get_emails()
        assert "new@example.com" in emails
        assert "alice@example.com" in emails
        assert "bob@example.com" not in emails

    def test_reload_forces_reread(self, whitelist_file: Path) -> None:
        loader = WhitelistLoader(str(whitelist_file))
        assert "alice@example.com" in loader.get_emails()

        whitelist_file.write_text("only@example.com\n", encoding="utf-8")
        loader.reload()

        emails = loader.get_emails()
        assert emails == {"only@example.com"}


class TestWhitelistService:
    """Tests for WhitelistService."""

    def test_is_allowed_returns_true_for_listed_email(
        self, whitelist_file: Path
    ) -> None:
        service = WhitelistService(str(whitelist_file))
        assert service.is_allowed("alice@example.com") is True

    def test_is_allowed_case_insensitive(self, whitelist_file: Path) -> None:
        service = WhitelistService(str(whitelist_file))
        assert service.is_allowed("ALICE@EXAMPLE.COM") is True
        assert service.is_allowed("Alice@Example.Com") is True
        assert service.is_allowed("aLiCe@eXaMpLe.CoM") is True

    def test_is_allowed_returns_false_for_unlisted_email(
        self, whitelist_file: Path
    ) -> None:
        service = WhitelistService(str(whitelist_file))
        assert service.is_allowed("unknown@example.com") is False

    def test_is_allowed_empty_whitelist(self, empty_whitelist_file: Path) -> None:
        service = WhitelistService(str(empty_whitelist_file))
        assert service.is_allowed("anyone@example.com") is False

    def test_file_not_found_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            WhitelistService(str(tmp_path / "missing.txt"))

    def test_hot_reload_on_file_change(self, whitelist_file: Path) -> None:
        service = WhitelistService(str(whitelist_file))
        assert service.is_allowed("alice@example.com") is True
        assert service.is_allowed("new@example.com") is False

        # Modify the file
        whitelist_file.write_text("new@example.com\n", encoding="utf-8")
        os.utime(whitelist_file, (time.time() + 1, time.time() + 1))

        # Should detect change and reload
        assert service.is_allowed("new@example.com") is True
        assert service.is_allowed("alice@example.com") is False

    @pytest.mark.asyncio
    async def test_reload_forces_reread(self, whitelist_file: Path) -> None:
        service = WhitelistService(str(whitelist_file))
        assert service.is_allowed("alice@example.com") is True

        whitelist_file.write_text("reloaded@example.com\n", encoding="utf-8")
        await service.reload()

        assert service.is_allowed("reloaded@example.com") is True
        assert service.is_allowed("alice@example.com") is False
