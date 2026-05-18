"""Unit tests for OAuthGrantRepository using mocked AsyncSession.

Since greenlet is incompatible with Python 3.14 on Windows, we mock
the AsyncSession to test repository logic without a real database.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.modules.identity.domain.entities import OAuthGrant
from src.modules.identity.infrastructure.oauth_grant_repository import (
    OAuthGrantRepository,
)


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


def _make_grant(
    user_id: UUID | None = None,
    access_token_enc: str = "encrypted_access_token",
    refresh_token_enc: str = "encrypted_refresh_token",
    scopes: list[str] | None = None,
    token_expires_at: datetime | None = None,
    is_valid: bool = True,
) -> OAuthGrant:
    """Create an OAuthGrant entity for testing."""
    return OAuthGrant(
        id=uuid4(),
        user_id=user_id or uuid4(),
        provider="google",
        access_token_enc=access_token_enc,
        refresh_token_enc=refresh_token_enc,
        scopes=scopes or ["openid", "email", "profile"],
        token_expires_at=token_expires_at or datetime.now(UTC) + timedelta(hours=1),
        is_valid=is_valid,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class TestGetByUserId:
    """Tests for OAuthGrantRepository.get_by_user_id."""

    async def test_returns_none_when_no_valid_grant_exists(self) -> None:
        session = _make_mock_session(query_result=None)
        repo = OAuthGrantRepository(session)

        result = await repo.get_by_user_id(uuid4())

        assert result is None
        session.execute.assert_called_once()

    async def test_returns_grant_when_valid_grant_exists(self) -> None:
        user_id = uuid4()
        grant = _make_grant(user_id=user_id)
        session = _make_mock_session(query_result=grant)
        repo = OAuthGrantRepository(session)

        result = await repo.get_by_user_id(user_id)

        assert result is not None
        assert result.user_id == user_id
        assert result.is_valid is True

    async def test_returns_grant_with_correct_tokens(self) -> None:
        grant = _make_grant(
            access_token_enc="enc_access_123",
            refresh_token_enc="enc_refresh_456",
        )
        session = _make_mock_session(query_result=grant)
        repo = OAuthGrantRepository(session)

        result = await repo.get_by_user_id(grant.user_id)

        assert result is not None
        assert result.access_token_enc == "enc_access_123"
        assert result.refresh_token_enc == "enc_refresh_456"


class TestUpsert:
    """Tests for OAuthGrantRepository.upsert."""

    async def test_creates_new_grant_when_none_exists(self) -> None:
        session = _make_mock_session(query_result=None)
        repo = OAuthGrantRepository(session)
        user_id = uuid4()
        expires_at = datetime.now(UTC) + timedelta(hours=1)

        result = await repo.upsert(
            user_id=user_id,
            access_token_enc="new_access_enc",
            refresh_token_enc="new_refresh_enc",
            scopes=["openid", "email", "gmail.readonly"],
            token_expires_at=expires_at,
        )

        session.add.assert_called_once()
        session.flush.assert_called_once()
        assert result.user_id == user_id
        assert result.access_token_enc == "new_access_enc"
        assert result.refresh_token_enc == "new_refresh_enc"
        assert result.scopes == ["openid", "email", "gmail.readonly"]
        assert result.token_expires_at == expires_at
        assert result.is_valid is True

    async def test_updates_existing_grant_tokens(self) -> None:
        user_id = uuid4()
        existing_grant = _make_grant(user_id=user_id)
        session = _make_mock_session(query_result=existing_grant)
        repo = OAuthGrantRepository(session)
        new_expires_at = datetime.now(UTC) + timedelta(hours=2)

        result = await repo.upsert(
            user_id=user_id,
            access_token_enc="updated_access_enc",
            refresh_token_enc="updated_refresh_enc",
            scopes=["openid", "email", "calendar.events"],
            token_expires_at=new_expires_at,
        )

        assert result is existing_grant
        assert result.access_token_enc == "updated_access_enc"
        assert result.refresh_token_enc == "updated_refresh_enc"
        assert result.scopes == ["openid", "email", "calendar.events"]
        assert result.token_expires_at == new_expires_at
        session.add.assert_called_once_with(existing_grant)
        session.flush.assert_called_once()

    async def test_upsert_sets_is_valid_true_on_update(self) -> None:
        existing_grant = _make_grant(is_valid=False)
        session = _make_mock_session(query_result=existing_grant)
        repo = OAuthGrantRepository(session)

        result = await repo.upsert(
            user_id=existing_grant.user_id,
            access_token_enc="new_enc",
            refresh_token_enc="new_ref_enc",
            scopes=["openid"],
            token_expires_at=datetime.now(UTC) + timedelta(hours=1),
        )

        assert result.is_valid is True

    async def test_upsert_updates_updated_at_on_existing(self) -> None:
        old_time = datetime(2024, 1, 1, tzinfo=UTC)
        existing_grant = _make_grant()
        existing_grant.updated_at = old_time
        session = _make_mock_session(query_result=existing_grant)
        repo = OAuthGrantRepository(session)

        result = await repo.upsert(
            user_id=existing_grant.user_id,
            access_token_enc="enc",
            refresh_token_enc="ref_enc",
            scopes=["openid"],
            token_expires_at=datetime.now(UTC) + timedelta(hours=1),
        )

        assert result.updated_at > old_time

    async def test_new_grant_has_uuid_id(self) -> None:
        session = _make_mock_session(query_result=None)
        repo = OAuthGrantRepository(session)

        result = await repo.upsert(
            user_id=uuid4(),
            access_token_enc="enc",
            refresh_token_enc="ref_enc",
            scopes=["openid"],
            token_expires_at=datetime.now(UTC) + timedelta(hours=1),
        )

        assert isinstance(result.id, UUID)

    async def test_new_grant_has_google_provider(self) -> None:
        session = _make_mock_session(query_result=None)
        repo = OAuthGrantRepository(session)

        result = await repo.upsert(
            user_id=uuid4(),
            access_token_enc="enc",
            refresh_token_enc="ref_enc",
            scopes=["openid"],
            token_expires_at=datetime.now(UTC) + timedelta(hours=1),
        )

        assert result.provider == "google"


class TestMarkInvalid:
    """Tests for OAuthGrantRepository.mark_invalid."""

    async def test_marks_grant_as_invalid(self) -> None:
        user_id = uuid4()
        grant = _make_grant(user_id=user_id, is_valid=True)
        session = _make_mock_session(query_result=grant)
        repo = OAuthGrantRepository(session)

        await repo.mark_invalid(user_id)

        assert grant.is_valid is False
        session.add.assert_called_once_with(grant)
        session.flush.assert_called_once()

    async def test_updates_updated_at_when_marking_invalid(self) -> None:
        old_time = datetime(2024, 1, 1, tzinfo=UTC)
        grant = _make_grant(is_valid=True)
        grant.updated_at = old_time
        session = _make_mock_session(query_result=grant)
        repo = OAuthGrantRepository(session)

        await repo.mark_invalid(grant.user_id)

        assert grant.updated_at > old_time

    async def test_does_nothing_when_no_grant_exists(self) -> None:
        session = _make_mock_session(query_result=None)
        repo = OAuthGrantRepository(session)

        await repo.mark_invalid(uuid4())

        session.add.assert_not_called()
        session.flush.assert_not_called()
