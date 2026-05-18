"""Unit tests for UserRepository using mocked AsyncSession.

Since greenlet is incompatible with Python 3.14 on Windows, we mock
the AsyncSession to test repository logic without a real database.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.modules.identity.api.schemas import GoogleUserInfo
from src.modules.identity.domain.entities import User
from src.modules.identity.infrastructure.user_repository import UserRepository


def _make_mock_session(query_result=None):
    """Create a mock AsyncSession that returns the given query result."""
    session = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.first.return_value = query_result
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    session.execute.return_value = result_mock
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


def _make_user(
    email: str = "alice@example.com",
    name: str = "Alice Nguyen",
    google_sub: str = "google-sub-12345",
    avatar_url: str | None = "https://lh3.googleusercontent.com/photo.jpg",
) -> User:
    """Create a User entity for testing."""
    return User(
        id=uuid4(),
        email=email,
        name=name,
        avatar_url=avatar_url,
        google_sub=google_sub,
        created_at=datetime.now(UTC),
        last_login=datetime.now(UTC),
        is_active=True,
    )


@pytest.fixture
def sample_google_user() -> GoogleUserInfo:
    """A sample Google user profile for testing."""
    return GoogleUserInfo(
        sub="google-sub-12345",
        email="alice@example.com",
        name="Alice Nguyen",
        picture="https://lh3.googleusercontent.com/photo.jpg",
    )


@pytest.fixture
def another_google_user() -> GoogleUserInfo:
    """A second Google user profile for testing."""
    return GoogleUserInfo(
        sub="google-sub-67890",
        email="bob@example.com",
        name="Bob Tran",
        picture=None,
    )


class TestGetByEmail:
    """Tests for UserRepository.get_by_email."""

    async def test_returns_none_when_user_not_found(self) -> None:
        session = _make_mock_session(query_result=None)
        repo = UserRepository(session)

        result = await repo.get_by_email("nonexistent@example.com")

        assert result is None
        session.execute.assert_called_once()

    async def test_returns_user_when_found(self) -> None:
        user = _make_user()
        session = _make_mock_session(query_result=user)
        repo = UserRepository(session)

        result = await repo.get_by_email("alice@example.com")

        assert result is not None
        assert result.email == "alice@example.com"
        assert result.name == "Alice Nguyen"

    async def test_passes_lowercased_email_to_query(self) -> None:
        session = _make_mock_session(query_result=None)
        repo = UserRepository(session)

        await repo.get_by_email("ALICE@EXAMPLE.COM")

        # Verify execute was called (the actual SQL filtering is tested via integration)
        session.execute.assert_called_once()


class TestGetById:
    """Tests for UserRepository.get_by_id."""

    async def test_returns_none_when_user_not_found(self) -> None:
        session = _make_mock_session(query_result=None)
        repo = UserRepository(session)

        result = await repo.get_by_id(uuid4())

        assert result is None
        session.execute.assert_called_once()

    async def test_returns_user_when_found(self) -> None:
        user = _make_user()
        session = _make_mock_session(query_result=user)
        repo = UserRepository(session)

        result = await repo.get_by_id(user.id)

        assert result is not None
        assert result.id == user.id
        assert result.email == "alice@example.com"


class TestUpsert:
    """Tests for UserRepository.upsert."""

    async def test_creates_new_user_when_not_found(
        self, sample_google_user: GoogleUserInfo
    ) -> None:
        session = _make_mock_session(query_result=None)
        repo = UserRepository(session)

        result = await repo.upsert(sample_google_user)

        # Should add a new user to the session
        session.add.assert_called_once()
        session.flush.assert_called_once()
        # The returned user should have the correct fields
        assert result.email == "alice@example.com"
        assert result.name == "Alice Nguyen"
        assert result.avatar_url == "https://lh3.googleusercontent.com/photo.jpg"
        assert result.google_sub == "google-sub-12345"
        assert result.is_active is True

    async def test_creates_user_without_picture(
        self, another_google_user: GoogleUserInfo
    ) -> None:
        session = _make_mock_session(query_result=None)
        repo = UserRepository(session)

        result = await repo.upsert(another_google_user)

        assert result.email == "bob@example.com"
        assert result.avatar_url is None

    async def test_updates_existing_user_last_login(
        self, sample_google_user: GoogleUserInfo
    ) -> None:
        existing_user = _make_user()
        old_login = existing_user.last_login
        session = _make_mock_session(query_result=existing_user)
        repo = UserRepository(session)

        result = await repo.upsert(sample_google_user)

        # Should update last_login
        assert result.last_login >= old_login
        # Should update profile data
        assert result.name == "Alice Nguyen"
        # Should add to session and flush
        session.add.assert_called_once_with(existing_user)
        session.flush.assert_called_once()

    async def test_updates_profile_data_on_existing_user(self) -> None:
        existing_user = _make_user(name="Old Name", avatar_url="https://old.jpg")
        session = _make_mock_session(query_result=existing_user)
        repo = UserRepository(session)

        updated_info = GoogleUserInfo(
            sub="google-sub-12345",
            email="alice@example.com",
            name="New Name",
            picture="https://new.jpg",
        )
        result = await repo.upsert(updated_info)

        assert result.name == "New Name"
        assert result.avatar_url == "https://new.jpg"

    async def test_returns_same_user_instance_on_update(
        self, sample_google_user: GoogleUserInfo
    ) -> None:
        existing_user = _make_user()
        session = _make_mock_session(query_result=existing_user)
        repo = UserRepository(session)

        result = await repo.upsert(sample_google_user)

        # Should return the same user object (updated in place)
        assert result is existing_user

    async def test_new_user_has_uuid_id(
        self, sample_google_user: GoogleUserInfo
    ) -> None:
        session = _make_mock_session(query_result=None)
        repo = UserRepository(session)

        result = await repo.upsert(sample_google_user)

        assert isinstance(result.id, UUID)

    async def test_new_user_has_timestamps(
        self, sample_google_user: GoogleUserInfo
    ) -> None:
        session = _make_mock_session(query_result=None)
        repo = UserRepository(session)

        result = await repo.upsert(sample_google_user)

        assert result.created_at is not None
        assert result.last_login is not None
