"""Unit tests for RoleService using mocked AsyncSession.

Tests cover promote_to_admin, demote_to_user, and ensure_super_admin
including protection against demoting the last admin and the super admin.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.modules.identity.application.role_service import (
    LastAdminError,
    RoleService,
    SuperAdminProtectedError,
    UserNotFoundError,
)
from src.modules.identity.domain.entities import User, UserRole


def _make_user(
    email: str = "user@example.com",
    role: UserRole = UserRole.USER,
) -> User:
    """Create a User entity for testing."""
    return User(
        id=uuid4(),
        email=email,
        name="Test User",
        avatar_url=None,
        google_sub=f"google-sub-{uuid4().hex[:8]}",
        created_at=datetime.now(UTC),
        last_login=datetime.now(UTC),
        is_active=True,
        role=role,
    )


def _make_mock_session(user_result=None, admin_count: int = 2):
    """Create a mock AsyncSession.

    Args:
        user_result: The user to return from select queries.
        admin_count: The count to return from admin count queries.
    """
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    # We need to handle multiple execute calls differently:
    # - First call is typically the user lookup (returns scalars().first())
    # - Second call may be the admin count (returns scalar_one())
    call_count = 0

    async def mock_execute(statement):
        nonlocal call_count
        call_count += 1

        result_mock = MagicMock()

        # Determine if this is a count query by checking if scalar_one is needed
        # We use a simple heuristic: first call is user lookup, second is count
        if call_count == 1:
            scalars_mock = MagicMock()
            scalars_mock.first.return_value = user_result
            result_mock.scalars.return_value = scalars_mock
        else:
            result_mock.scalar_one.return_value = admin_count
            # Also provide scalars for ensure_super_admin which only does user lookup
            scalars_mock = MagicMock()
            scalars_mock.first.return_value = user_result
            result_mock.scalars.return_value = scalars_mock

        return result_mock

    session.execute = AsyncMock(side_effect=mock_execute)
    return session


class TestPromoteToAdmin:
    """Tests for RoleService.promote_to_admin."""

    async def test_promotes_user_to_admin(self) -> None:
        user = _make_user(role=UserRole.USER)
        admin = _make_user(email="admin@example.com", role=UserRole.ADMIN)
        session = _make_mock_session(user_result=user)
        service = RoleService(session)

        result = await service.promote_to_admin(user.id, admin)

        assert result.role == UserRole.ADMIN
        session.add.assert_called_once_with(user)
        session.flush.assert_called_once()

    async def test_noop_when_already_admin(self) -> None:
        user = _make_user(role=UserRole.ADMIN)
        admin = _make_user(email="admin@example.com", role=UserRole.ADMIN)
        session = _make_mock_session(user_result=user)
        service = RoleService(session)

        result = await service.promote_to_admin(user.id, admin)

        assert result.role == UserRole.ADMIN
        # Should not call add/flush since no change was made
        session.add.assert_not_called()

    async def test_raises_user_not_found(self) -> None:
        admin = _make_user(email="admin@example.com", role=UserRole.ADMIN)
        session = _make_mock_session(user_result=None)
        service = RoleService(session)

        with pytest.raises(UserNotFoundError):
            await service.promote_to_admin(uuid4(), admin)


class TestDemoteToUser:
    """Tests for RoleService.demote_to_user."""

    async def test_demotes_admin_to_user(self) -> None:
        user = _make_user(email="target@example.com", role=UserRole.ADMIN)
        admin = _make_user(email="admin@example.com", role=UserRole.ADMIN)
        session = _make_mock_session(user_result=user, admin_count=2)
        service = RoleService(session)

        result = await service.demote_to_user(user.id, admin)

        assert result.role == UserRole.USER
        session.add.assert_called_once_with(user)

    async def test_noop_when_already_user(self) -> None:
        user = _make_user(role=UserRole.USER)
        admin = _make_user(email="admin@example.com", role=UserRole.ADMIN)
        session = _make_mock_session(user_result=user)
        service = RoleService(session)

        result = await service.demote_to_user(user.id, admin)

        assert result.role == UserRole.USER
        session.add.assert_not_called()

    async def test_raises_user_not_found(self) -> None:
        admin = _make_user(email="admin@example.com", role=UserRole.ADMIN)
        session = _make_mock_session(user_result=None)
        service = RoleService(session)

        with pytest.raises(UserNotFoundError):
            await service.demote_to_user(uuid4(), admin)

    async def test_raises_super_admin_protected(self) -> None:
        super_admin = _make_user(email="super@example.com", role=UserRole.ADMIN)
        admin = _make_user(email="admin@example.com", role=UserRole.ADMIN)
        session = _make_mock_session(user_result=super_admin, admin_count=2)
        service = RoleService(session, super_admin_email="super@example.com")

        with pytest.raises(SuperAdminProtectedError):
            await service.demote_to_user(super_admin.id, admin)

    async def test_super_admin_check_is_case_insensitive(self) -> None:
        super_admin = _make_user(email="Super@Example.COM", role=UserRole.ADMIN)
        admin = _make_user(email="admin@example.com", role=UserRole.ADMIN)
        session = _make_mock_session(user_result=super_admin, admin_count=2)
        service = RoleService(session, super_admin_email="super@example.com")

        with pytest.raises(SuperAdminProtectedError):
            await service.demote_to_user(super_admin.id, admin)

    async def test_raises_last_admin_error(self) -> None:
        user = _make_user(email="only-admin@example.com", role=UserRole.ADMIN)
        admin = user  # Same user trying to demote themselves
        session = _make_mock_session(user_result=user, admin_count=1)
        service = RoleService(session)

        with pytest.raises(LastAdminError):
            await service.demote_to_user(user.id, admin)


class TestEnsureSuperAdmin:
    """Tests for RoleService.ensure_super_admin."""

    async def test_assigns_admin_role_to_existing_user(self) -> None:
        user = _make_user(email="super@example.com", role=UserRole.USER)
        session = _make_mock_session(user_result=user)
        service = RoleService(session, super_admin_email="super@example.com")

        await service.ensure_super_admin("super@example.com")

        assert user.role == UserRole.ADMIN
        session.add.assert_called_once_with(user)
        session.flush.assert_called_once()

    async def test_noop_when_already_admin(self) -> None:
        user = _make_user(email="super@example.com", role=UserRole.ADMIN)
        session = _make_mock_session(user_result=user)
        service = RoleService(session, super_admin_email="super@example.com")

        await service.ensure_super_admin("super@example.com")

        assert user.role == UserRole.ADMIN
        session.add.assert_not_called()

    async def test_logs_info_when_user_not_found(self) -> None:
        session = _make_mock_session(user_result=None)
        service = RoleService(session, super_admin_email="super@example.com")

        # Should not raise, just log
        await service.ensure_super_admin("super@example.com")

        session.add.assert_not_called()
        session.flush.assert_not_called()
