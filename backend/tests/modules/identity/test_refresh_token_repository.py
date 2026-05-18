"""Unit tests for RefreshTokenRepository using mocked AsyncSession.

Since greenlet is incompatible with Python 3.14 on Windows, we mock
the AsyncSession to test repository logic without a real database.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.modules.identity.domain.entities import RefreshToken
from src.modules.identity.infrastructure.refresh_token_repository import (
    RefreshTokenRepository,
    RefreshTokenWithEmail,
)


def _make_mock_session(query_result=None):
    """Create a mock AsyncSession that returns the given query result.

    For single-row results (e.g., find_by_token_hash), set query_result
    to the value that result.first() should return.
    """
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.first.return_value = query_result
    scalars_mock = MagicMock()
    scalars_mock.first.return_value = query_result
    scalars_mock.all.return_value = query_result if isinstance(query_result, list) else []
    result_mock.scalars.return_value = scalars_mock
    session.execute.return_value = result_mock
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


def _make_refresh_token(
    user_id: UUID | None = None,
    token_hash: str = "abc123hash",
    expires_at: datetime | None = None,
    revoked_at: datetime | None = None,
    user_agent: str | None = "Mozilla/5.0",
) -> RefreshToken:
    """Create a RefreshToken entity for testing."""
    return RefreshToken(
        id=uuid4(),
        user_id=user_id or uuid4(),
        token_hash=token_hash,
        expires_at=expires_at or datetime.now(UTC) + timedelta(days=7),
        revoked_at=revoked_at,
        created_at=datetime.now(UTC),
        user_agent=user_agent,
    )


class TestCreate:
    """Tests for RefreshTokenRepository.create."""

    async def test_creates_refresh_token_with_all_fields(self) -> None:
        session = _make_mock_session()
        repo = RefreshTokenRepository(session)
        user_id = uuid4()
        expires_at = datetime.now(UTC) + timedelta(days=7)

        result = await repo.create(
            user_id=user_id,
            token_hash="sha256hexdigest",
            expires_at=expires_at,
            user_agent="Mozilla/5.0",
        )

        assert result.user_id == user_id
        assert result.token_hash == "sha256hexdigest"
        assert result.expires_at == expires_at
        assert result.user_agent == "Mozilla/5.0"
        session.add.assert_called_once()
        session.flush.assert_called_once()

    async def test_creates_refresh_token_without_user_agent(self) -> None:
        session = _make_mock_session()
        repo = RefreshTokenRepository(session)
        user_id = uuid4()
        expires_at = datetime.now(UTC) + timedelta(days=7)

        result = await repo.create(
            user_id=user_id,
            token_hash="anotherhash",
            expires_at=expires_at,
        )

        assert result.user_agent is None
        assert result.user_id == user_id
        session.add.assert_called_once()

    async def test_created_token_has_uuid_id(self) -> None:
        session = _make_mock_session()
        repo = RefreshTokenRepository(session)

        result = await repo.create(
            user_id=uuid4(),
            token_hash="somehash",
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )

        assert isinstance(result.id, UUID)

    async def test_created_token_has_no_revoked_at(self) -> None:
        session = _make_mock_session()
        repo = RefreshTokenRepository(session)

        result = await repo.create(
            user_id=uuid4(),
            token_hash="somehash",
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )

        assert result.revoked_at is None


class TestFindByTokenHash:
    """Tests for RefreshTokenRepository.find_by_token_hash."""

    async def test_returns_none_when_token_not_found(self) -> None:
        session = _make_mock_session(query_result=None)
        repo = RefreshTokenRepository(session)

        result = await repo.find_by_token_hash("nonexistenthash")

        assert result is None
        session.execute.assert_called_once()

    async def test_returns_token_with_email_when_found(self) -> None:
        user_id = uuid4()
        token = _make_refresh_token(user_id=user_id, token_hash="foundhash")
        # Simulate the join result: (RefreshToken, email)
        session = _make_mock_session(query_result=(token, "user@example.com"))
        repo = RefreshTokenRepository(session)

        result = await repo.find_by_token_hash("foundhash")

        assert result is not None
        assert isinstance(result, RefreshTokenWithEmail)
        assert result.user_id == user_id
        assert result.token_hash == "foundhash"
        assert result.email == "user@example.com"
        assert result.revoked_at is None

    async def test_returns_revoked_token_with_revoked_at(self) -> None:
        revoked_time = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
        token = _make_refresh_token(
            token_hash="revokedhash",
            revoked_at=revoked_time,
        )
        session = _make_mock_session(query_result=(token, "revoked@example.com"))
        repo = RefreshTokenRepository(session)

        result = await repo.find_by_token_hash("revokedhash")

        assert result is not None
        assert result.revoked_at == revoked_time
        assert result.email == "revoked@example.com"

    async def test_returns_correct_expires_at(self) -> None:
        expires = datetime(2025, 1, 15, 0, 0, 0, tzinfo=UTC)
        token = _make_refresh_token(token_hash="exphash", expires_at=expires)
        session = _make_mock_session(query_result=(token, "test@example.com"))
        repo = RefreshTokenRepository(session)

        result = await repo.find_by_token_hash("exphash")

        assert result is not None
        assert result.expires_at == expires


class TestRevokeAllForUser:
    """Tests for RefreshTokenRepository.revoke_all_for_user."""

    async def test_revokes_all_active_tokens_for_user(self) -> None:
        user_id = uuid4()
        token1 = _make_refresh_token(user_id=user_id, token_hash="hash1")
        token2 = _make_refresh_token(user_id=user_id, token_hash="hash2")

        session = _make_mock_session(query_result=[token1, token2])
        repo = RefreshTokenRepository(session)

        await repo.revoke_all_for_user(user_id)

        assert token1.revoked_at is not None
        assert token2.revoked_at is not None
        assert session.add.call_count == 2
        session.flush.assert_called_once()

    async def test_sets_revoked_at_to_current_time(self) -> None:
        user_id = uuid4()
        token = _make_refresh_token(user_id=user_id)

        session = _make_mock_session(query_result=[token])
        repo = RefreshTokenRepository(session)

        before = datetime.now(UTC)
        await repo.revoke_all_for_user(user_id)
        after = datetime.now(UTC)

        assert token.revoked_at is not None
        assert before <= token.revoked_at <= after

    async def test_does_nothing_when_no_active_tokens(self) -> None:
        session = _make_mock_session(query_result=[])
        repo = RefreshTokenRepository(session)

        await repo.revoke_all_for_user(uuid4())

        session.add.assert_not_called()
        session.flush.assert_not_called()
