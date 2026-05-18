"""Unit tests for auth dependencies (get_current_user).

Tests the FastAPI dependency that extracts and validates the current
authenticated user from the access_token cookie.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.modules.identity.api.dependencies import get_current_user
from src.modules.identity.api.schemas import TokenPayload
from src.modules.identity.domain.exceptions import InvalidTokenError


@pytest.fixture
def mock_request():
    """Create a mock FastAPI Request with cookies."""
    request = MagicMock()
    request.cookies = {"access_token": "valid-jwt-token"}
    return request


@pytest.fixture
def mock_token_service():
    """Create a mock TokenService."""
    service = MagicMock()
    user_id = uuid4()
    service.verify_access_token.return_value = TokenPayload(
        sub=user_id,
        email="test@example.com",
        exp=1700000000,
        iat=1699999000,
    )
    return service


@pytest.fixture
def mock_user():
    """Create a mock User entity."""
    user = MagicMock()
    user.id = uuid4()
    user.email = "test@example.com"
    user.name = "Test User"
    user.is_active = True
    return user


@pytest.fixture
def mock_user_repository(mock_user):
    """Create a mock UserRepository."""
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=mock_user)
    return repo


class TestGetCurrentUser:
    """Tests for the get_current_user dependency."""

    async def test_returns_user_on_valid_token(
        self, mock_request, mock_token_service, mock_user_repository, mock_user
    ):
        """Should return the User entity when the token is valid."""
        result = await get_current_user(
            mock_request, mock_token_service, mock_user_repository
        )

        assert result == mock_user

    async def test_extracts_token_from_cookie(
        self, mock_request, mock_token_service, mock_user_repository
    ):
        """Should read the access_token from request cookies."""
        await get_current_user(
            mock_request, mock_token_service, mock_user_repository
        )

        mock_token_service.verify_access_token.assert_called_once_with(
            "valid-jwt-token"
        )

    async def test_raises_401_when_cookie_missing(
        self, mock_token_service, mock_user_repository
    ):
        """Should raise HTTPException 401 when access_token cookie is absent."""
        request = MagicMock()
        request.cookies = {}

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request, mock_token_service, mock_user_repository)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid or expired token"

    async def test_raises_401_when_token_invalid(
        self, mock_request, mock_token_service, mock_user_repository
    ):
        """Should raise HTTPException 401 when token verification fails."""
        mock_token_service.verify_access_token.side_effect = InvalidTokenError()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                mock_request, mock_token_service, mock_user_repository
            )

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid or expired token"

    async def test_raises_401_when_user_not_found(
        self, mock_request, mock_token_service, mock_user_repository
    ):
        """Should raise HTTPException 401 when user ID from token doesn't exist."""
        mock_user_repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                mock_request, mock_token_service, mock_user_repository
            )

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid or expired token"

    async def test_looks_up_user_by_token_sub(
        self, mock_request, mock_token_service, mock_user_repository
    ):
        """Should look up the user using the sub claim from the token payload."""
        await get_current_user(
            mock_request, mock_token_service, mock_user_repository
        )

        expected_user_id = mock_token_service.verify_access_token.return_value.sub
        mock_user_repository.get_by_id.assert_called_once_with(expected_user_id)

    async def test_raises_401_when_cookie_is_empty_string(
        self, mock_token_service, mock_user_repository
    ):
        """Should raise HTTPException 401 when access_token cookie is empty."""
        request = MagicMock()
        request.cookies = {"access_token": ""}

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request, mock_token_service, mock_user_repository)

        assert exc_info.value.status_code == 401
        # Token service should not be called for empty token
        mock_token_service.verify_access_token.assert_not_called()
