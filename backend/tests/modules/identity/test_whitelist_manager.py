"""Unit tests for WhitelistManager composite whitelist service."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.modules.identity.application.whitelist_manager import (
    WhitelistManager,
    WhitelistEntryResponse,
)
from src.modules.identity.domain.entities import (
    User,
    UserRole,
    WhitelistEntry,
    WhitelistEntryType,
)
from src.modules.identity.infrastructure.whitelist_loader import WhitelistLoader


@pytest.fixture
def mock_repo() -> MagicMock:
    """Create a mock WhitelistRepository."""
    repo = MagicMock()
    repo.session = MagicMock()
    repo.get_all = AsyncMock(return_value=[])
    repo.add = AsyncMock()
    repo.remove = AsyncMock()
    repo.exists = AsyncMock(return_value=False)
    return repo


@pytest.fixture
def whitelist_file(tmp_path: Path) -> Path:
    """Create a temporary whitelist file with sample entries."""
    file = tmp_path / "whitelist.txt"
    file.write_text(
        "alice@example.com\n"
        "bob@company.org\n"
        "@allowed-domain.com\n",
        encoding="utf-8",
    )
    return file


@pytest.fixture
def file_loader(whitelist_file: Path) -> WhitelistLoader:
    """Create a WhitelistLoader from the temp file."""
    return WhitelistLoader(str(whitelist_file))


@pytest.fixture
def admin_user() -> User:
    """Create a mock admin user."""
    return User(
        id=uuid4(),
        email="admin@example.com",
        name="Admin User",
        google_sub="google-sub-123",
        role=UserRole.ADMIN,
    )


@pytest.fixture
def sample_db_entries(admin_user: User) -> list[WhitelistEntry]:
    """Create sample database whitelist entries."""
    return [
        WhitelistEntry(
            id=uuid4(),
            value="db-user@example.com",
            entry_type=WhitelistEntryType.EXACT_EMAIL,
            added_by_user_id=admin_user.id,
            created_at=datetime.now(UTC),
        ),
        WhitelistEntry(
            id=uuid4(),
            value="@db-domain.com",
            entry_type=WhitelistEntryType.DOMAIN_PATTERN,
            added_by_user_id=admin_user.id,
            created_at=datetime.now(UTC),
        ),
    ]


class TestWhitelistManagerIsAllowed:
    """Tests for is_allowed and is_allowed_async methods."""

    async def test_exact_email_match_from_file(
        self, mock_repo: MagicMock, file_loader: WhitelistLoader
    ) -> None:
        manager = WhitelistManager(repo=mock_repo, file_loader=file_loader)
        assert await manager.is_allowed_async("alice@example.com") is True

    async def test_exact_email_case_insensitive(
        self, mock_repo: MagicMock, file_loader: WhitelistLoader
    ) -> None:
        manager = WhitelistManager(repo=mock_repo, file_loader=file_loader)
        assert await manager.is_allowed_async("ALICE@EXAMPLE.COM") is True
        assert await manager.is_allowed_async("Alice@Example.Com") is True

    async def test_domain_pattern_match_from_file(
        self, mock_repo: MagicMock, file_loader: WhitelistLoader
    ) -> None:
        manager = WhitelistManager(repo=mock_repo, file_loader=file_loader)
        assert await manager.is_allowed_async("anyone@allowed-domain.com") is True
        assert await manager.is_allowed_async("user123@allowed-domain.com") is True

    async def test_domain_pattern_case_insensitive(
        self, mock_repo: MagicMock, file_loader: WhitelistLoader
    ) -> None:
        manager = WhitelistManager(repo=mock_repo, file_loader=file_loader)
        assert await manager.is_allowed_async("USER@ALLOWED-DOMAIN.COM") is True

    async def test_unlisted_email_rejected(
        self, mock_repo: MagicMock, file_loader: WhitelistLoader
    ) -> None:
        manager = WhitelistManager(repo=mock_repo, file_loader=file_loader)
        assert await manager.is_allowed_async("unknown@other.com") is False

    async def test_db_exact_email_match(
        self, mock_repo: MagicMock, sample_db_entries: list[WhitelistEntry]
    ) -> None:
        mock_repo.get_all = AsyncMock(return_value=sample_db_entries)
        manager = WhitelistManager(repo=mock_repo, file_loader=None)
        assert await manager.is_allowed_async("db-user@example.com") is True

    async def test_db_domain_pattern_match(
        self, mock_repo: MagicMock, sample_db_entries: list[WhitelistEntry]
    ) -> None:
        mock_repo.get_all = AsyncMock(return_value=sample_db_entries)
        manager = WhitelistManager(repo=mock_repo, file_loader=None)
        assert await manager.is_allowed_async("anyone@db-domain.com") is True

    async def test_union_of_file_and_db(
        self,
        mock_repo: MagicMock,
        file_loader: WhitelistLoader,
        sample_db_entries: list[WhitelistEntry],
    ) -> None:
        mock_repo.get_all = AsyncMock(return_value=sample_db_entries)
        manager = WhitelistManager(repo=mock_repo, file_loader=file_loader)
        await manager.refresh_cache()

        # File entries
        assert manager.is_allowed("alice@example.com") is True
        assert manager.is_allowed("anyone@allowed-domain.com") is True
        # DB entries
        assert manager.is_allowed("db-user@example.com") is True
        assert manager.is_allowed("anyone@db-domain.com") is True

    async def test_no_file_loader_works(
        self, mock_repo: MagicMock, sample_db_entries: list[WhitelistEntry]
    ) -> None:
        mock_repo.get_all = AsyncMock(return_value=sample_db_entries)
        manager = WhitelistManager(repo=mock_repo, file_loader=None)
        assert await manager.is_allowed_async("db-user@example.com") is True
        assert await manager.is_allowed_async("alice@example.com") is False


class TestWhitelistManagerAddEntry:
    """Tests for add_entry method."""

    async def test_add_valid_email(
        self, mock_repo: MagicMock, admin_user: User
    ) -> None:
        mock_repo.add = AsyncMock(
            side_effect=lambda entry: entry
        )
        manager = WhitelistManager(repo=mock_repo, file_loader=None)
        await manager.refresh_cache()

        result = await manager.add_entry("new@example.com", admin_user)
        assert result.value == "new@example.com"
        assert result.entry_type == WhitelistEntryType.EXACT_EMAIL
        assert result.added_by_user_id == admin_user.id

    async def test_add_valid_domain_pattern(
        self, mock_repo: MagicMock, admin_user: User
    ) -> None:
        mock_repo.add = AsyncMock(
            side_effect=lambda entry: entry
        )
        manager = WhitelistManager(repo=mock_repo, file_loader=None)
        await manager.refresh_cache()

        result = await manager.add_entry("@newdomain.com", admin_user)
        assert result.value == "@newdomain.com"
        assert result.entry_type == WhitelistEntryType.DOMAIN_PATTERN

    async def test_add_invalid_format_raises_422(
        self, mock_repo: MagicMock, admin_user: User
    ) -> None:
        manager = WhitelistManager(repo=mock_repo, file_loader=None)
        await manager.refresh_cache()

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await manager.add_entry("not-an-email", admin_user)
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["code"] == "WHITELIST_INVALID_FORMAT"

    async def test_add_invalid_domain_raises_422(
        self, mock_repo: MagicMock, admin_user: User
    ) -> None:
        manager = WhitelistManager(repo=mock_repo, file_loader=None)
        await manager.refresh_cache()

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await manager.add_entry("@", admin_user)
        assert exc_info.value.status_code == 422

    async def test_add_duplicate_raises_409(
        self, mock_repo: MagicMock, admin_user: User
    ) -> None:
        mock_repo.exists = AsyncMock(return_value=True)
        manager = WhitelistManager(repo=mock_repo, file_loader=None)
        await manager.refresh_cache()

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await manager.add_entry("existing@example.com", admin_user)
        assert exc_info.value.status_code == 409
        assert exc_info.value.detail["code"] == "WHITELIST_DUPLICATE"

    async def test_add_duplicate_from_file_raises_409(
        self, mock_repo: MagicMock, file_loader: WhitelistLoader, admin_user: User
    ) -> None:
        manager = WhitelistManager(repo=mock_repo, file_loader=file_loader)
        await manager.refresh_cache()

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await manager.add_entry("alice@example.com", admin_user)
        assert exc_info.value.status_code == 409

    async def test_add_updates_cache_immediately(
        self, mock_repo: MagicMock, admin_user: User
    ) -> None:
        mock_repo.add = AsyncMock(side_effect=lambda entry: entry)
        manager = WhitelistManager(repo=mock_repo, file_loader=None)
        await manager.refresh_cache()

        assert manager.is_allowed("new@example.com") is False
        await manager.add_entry("new@example.com", admin_user)
        assert manager.is_allowed("new@example.com") is True

    async def test_add_domain_updates_cache_immediately(
        self, mock_repo: MagicMock, admin_user: User
    ) -> None:
        mock_repo.add = AsyncMock(side_effect=lambda entry: entry)
        manager = WhitelistManager(repo=mock_repo, file_loader=None)
        await manager.refresh_cache()

        assert manager.is_allowed("user@newdomain.com") is False
        await manager.add_entry("@newdomain.com", admin_user)
        assert manager.is_allowed("user@newdomain.com") is True


class TestWhitelistManagerRemoveEntry:
    """Tests for remove_entry method."""

    async def test_remove_existing_entry(
        self,
        mock_repo: MagicMock,
        admin_user: User,
        sample_db_entries: list[WhitelistEntry],
    ) -> None:
        mock_repo.get_all = AsyncMock(return_value=sample_db_entries)
        manager = WhitelistManager(repo=mock_repo, file_loader=None)
        await manager.refresh_cache()

        entry_id = sample_db_entries[0].id
        await manager.remove_entry(entry_id, admin_user)
        mock_repo.remove.assert_called_once_with(entry_id)

    async def test_remove_nonexistent_raises_404(
        self, mock_repo: MagicMock, admin_user: User
    ) -> None:
        mock_repo.get_all = AsyncMock(return_value=[])
        manager = WhitelistManager(repo=mock_repo, file_loader=None)
        await manager.refresh_cache()

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await manager.remove_entry(uuid4(), admin_user)
        assert exc_info.value.status_code == 404

    async def test_remove_updates_cache(
        self,
        mock_repo: MagicMock,
        admin_user: User,
        sample_db_entries: list[WhitelistEntry],
    ) -> None:
        mock_repo.get_all = AsyncMock(return_value=sample_db_entries)
        manager = WhitelistManager(repo=mock_repo, file_loader=None)
        await manager.refresh_cache()

        assert manager.is_allowed("db-user@example.com") is True
        await manager.remove_entry(sample_db_entries[0].id, admin_user)
        assert manager.is_allowed("db-user@example.com") is False


class TestWhitelistManagerListEntries:
    """Tests for list_entries method."""

    async def test_list_db_entries(
        self,
        mock_repo: MagicMock,
        admin_user: User,
        sample_db_entries: list[WhitelistEntry],
    ) -> None:
        mock_repo.get_all = AsyncMock(return_value=sample_db_entries)

        # Mock the session execute for admin email lookup
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = admin_user
        mock_result.scalars.return_value = mock_scalars
        mock_repo.session.execute = AsyncMock(return_value=mock_result)

        manager = WhitelistManager(repo=mock_repo, file_loader=None)
        entries = await manager.list_entries()

        assert len(entries) == 2
        assert all(e.source == "database" for e in entries)
        assert all(e.is_readonly is False for e in entries)

    async def test_list_file_entries_marked_readonly(
        self, mock_repo: MagicMock, file_loader: WhitelistLoader
    ) -> None:
        mock_repo.get_all = AsyncMock(return_value=[])
        manager = WhitelistManager(repo=mock_repo, file_loader=file_loader)
        entries = await manager.list_entries()

        assert len(entries) == 3  # alice, bob, @allowed-domain.com
        assert all(e.source == "file" for e in entries)
        assert all(e.is_readonly is True for e in entries)
        assert all(e.added_by_email == "system" for e in entries)

    async def test_list_deduplication_db_takes_precedence(
        self, mock_repo: MagicMock, file_loader: WhitelistLoader, admin_user: User
    ) -> None:
        # DB has same entry as file
        db_entry = WhitelistEntry(
            id=uuid4(),
            value="alice@example.com",
            entry_type=WhitelistEntryType.EXACT_EMAIL,
            added_by_user_id=admin_user.id,
            created_at=datetime.now(UTC),
        )
        mock_repo.get_all = AsyncMock(return_value=[db_entry])

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = admin_user
        mock_result.scalars.return_value = mock_scalars
        mock_repo.session.execute = AsyncMock(return_value=mock_result)

        manager = WhitelistManager(repo=mock_repo, file_loader=file_loader)
        entries = await manager.list_entries()

        # alice@example.com should appear once (from DB), plus bob and @allowed-domain from file
        alice_entries = [e for e in entries if "alice" in e.value]
        assert len(alice_entries) == 1
        assert alice_entries[0].source == "database"
        assert alice_entries[0].is_readonly is False


class TestWhitelistManagerRefreshCache:
    """Tests for refresh_cache method."""

    async def test_refresh_reloads_from_both_sources(
        self,
        mock_repo: MagicMock,
        file_loader: WhitelistLoader,
        sample_db_entries: list[WhitelistEntry],
    ) -> None:
        mock_repo.get_all = AsyncMock(return_value=sample_db_entries)
        manager = WhitelistManager(repo=mock_repo, file_loader=file_loader)
        await manager.refresh_cache()

        # File entries
        assert manager.is_allowed("alice@example.com") is True
        # DB entries
        assert manager.is_allowed("db-user@example.com") is True
        assert manager.is_allowed("anyone@db-domain.com") is True

    async def test_refresh_updates_timestamp(self, mock_repo: MagicMock) -> None:
        manager = WhitelistManager(repo=mock_repo, file_loader=None)
        assert manager._cache_timestamp == 0.0
        await manager.refresh_cache()
        assert manager._cache_timestamp > 0.0


class TestWhitelistManagerEntryTypeDetection:
    """Tests for _detect_entry_type static method."""

    def test_valid_email(self) -> None:
        assert (
            WhitelistManager._detect_entry_type("user@example.com")
            == WhitelistEntryType.EXACT_EMAIL
        )

    def test_valid_domain_pattern(self) -> None:
        assert (
            WhitelistManager._detect_entry_type("@example.com")
            == WhitelistEntryType.DOMAIN_PATTERN
        )

    def test_invalid_no_at_sign(self) -> None:
        assert WhitelistManager._detect_entry_type("notanemail") is None

    def test_invalid_just_at(self) -> None:
        assert WhitelistManager._detect_entry_type("@") is None

    def test_invalid_domain_no_tld(self) -> None:
        assert WhitelistManager._detect_entry_type("@localhost") is None

    def test_valid_subdomain_pattern(self) -> None:
        assert (
            WhitelistManager._detect_entry_type("@sub.example.com")
            == WhitelistEntryType.DOMAIN_PATTERN
        )

    def test_valid_complex_email(self) -> None:
        assert (
            WhitelistManager._detect_entry_type("user.name+tag@example.co.uk")
            == WhitelistEntryType.EXACT_EMAIL
        )
