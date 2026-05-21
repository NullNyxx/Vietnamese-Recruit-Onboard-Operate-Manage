"""Unit tests for the Identity & Auth router endpoints.

Tests the FastAPI router endpoints for login, callback, refresh,
logout, me, and grant-status using mocked dependencies.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.modules.identity.api.router import (
    get_auth_service,
    get_current_user,
    get_oauth_service,
    get_rate_limiter,
    get_settings,
    get_token_service,
    router,
)
from src.modules.identity.api.schemas import GrantStatus, LoginRedirect
from src.modules.identity.application.auth_service import AuthResult
from src.modules.identity.domain.exceptions import (
    AccessDeniedError,
    InvalidStateError,
    InvalidTokenError,
    RateLimitExceededError,
)


@pytest.fixture
def mock_auth_service():
    """Create a mock AuthService."""
    service = AsyncMock()
    service.initiate_login = AsyncMock(
        return_value=LoginRedirect(
            redirect_url="https://accounts.google.com/o/oauth2/v2/auth?client_id=test",
            state_token="signed-state-token",
            code_verifier="test-code-verifier-43chars-long-enough-here",
        )
    )
    service.handle_callback = AsyncMock(
        return_value=AuthResult(
            access_token="new-access-token",
            refresh_token="new-refresh-token",
            user=MagicMock(),
            grant_status=GrantStatus(
                gmail_grant_valid=True, calendar_grant_valid=True
            ),
        )
    )
    service.logout = AsyncMock()
    return service


@pytest.fixture
def mock_token_service():
    """Create a mock TokenService."""
    service = AsyncMock()
    service.refresh_access_token = AsyncMock(return_value="refreshed-access-token")
    return service


@pytest.fixture
def mock_oauth_service():
    """Create a mock OAuthService."""
    service = AsyncMock()
    grant = MagicMock()
    grant.is_valid = True
    grant.scopes = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/calendar.events",
    ]
    service._grant_repository = AsyncMock()
    service._grant_repository.get_by_user_id = AsyncMock(return_value=grant)
    service.determine_grant_status = MagicMock(
        return_value=GrantStatus(gmail_grant_valid=True, calendar_grant_valid=True)
    )
    return service


@pytest.fixture
def mock_rate_limiter():
    """Create a mock RateLimiter that allows all requests."""
    limiter = AsyncMock()
    limiter.check_rate_limit = AsyncMock(return_value=True)
    return limiter


@pytest.fixture
def mock_settings():
    """Create a mock AuthSettings."""
    settings = MagicMock()
    settings.frontend_url = "http://localhost:3000"
    return settings


@pytest.fixture
def mock_current_user():
    """Create a mock authenticated User."""
    user = MagicMock()
    user.id = uuid4()
    user.email = "hr@example.com"
    user.name = "HR User"
    user.avatar_url = "https://example.com/avatar.png"
    user.role = "user"
    user.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    user.last_login = datetime(2024, 6, 15, tzinfo=UTC)
    return user


@pytest.fixture
def app(
    mock_auth_service,
    mock_token_service,
    mock_oauth_service,
    mock_rate_limiter,
    mock_settings,
    mock_current_user,
):
    """Create a FastAPI app with overridden dependencies for testing."""
    from fastapi import Request
    from fastapi.responses import JSONResponse

    from src.modules.identity.domain.exceptions import AuthError

    app = FastAPI()

    @app.exception_handler(AuthError)
    async def auth_error_handler(request: Request, exc: AuthError) -> JSONResponse:
        """Convert AuthError exceptions to JSON error responses."""
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.error_code, "message": exc.message}},
        )

    app.include_router(router)

    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
    app.dependency_overrides[get_token_service] = lambda: mock_token_service
    app.dependency_overrides[get_oauth_service] = lambda: mock_oauth_service
    app.dependency_overrides[get_rate_limiter] = lambda: mock_rate_limiter
    app.dependency_overrides[get_settings] = lambda: mock_settings
    app.dependency_overrides[get_current_user] = lambda: mock_current_user

    return app


@pytest.fixture
def client(app):
    """Create a test client for the FastAPI app."""
    return TestClient(app, follow_redirects=False)


class TestLoginEndpoint:
    """Tests for GET /api/auth/login."""

    def test_returns_302_redirect(self, client):
        """Should return a 302 redirect to Google OAuth2."""
        response = client.get("/api/auth/login")

        assert response.status_code == 302

    def test_redirects_to_google_auth_url(self, client):
        """Should redirect to the URL returned by AuthService."""
        response = client.get("/api/auth/login")

        assert response.headers["location"].startswith(
            "https://accounts.google.com/o/oauth2/v2/auth"
        )

    def test_sets_code_verifier_cookie(self, client):
        """Should set a code_verifier httpOnly cookie."""
        response = client.get("/api/auth/login")

        cookies = response.cookies
        assert "code_verifier" in cookies

    def test_rate_limit_exceeded_raises_429(
        self, app, mock_rate_limiter
    ):
        """Should raise RateLimitExceededError when rate limit is exceeded."""
        mock_rate_limiter.check_rate_limit = AsyncMock(return_value=False)
        client = TestClient(app, follow_redirects=False)

        response = client.get("/api/auth/login")

        assert response.status_code == 429

    def test_calls_rate_limiter_with_client_ip(
        self, client, mock_rate_limiter
    ):
        """Should check rate limit using the client's IP address."""
        client.get("/api/auth/login")

        mock_rate_limiter.check_rate_limit.assert_called_once()


class TestCallbackEndpoint:
    """Tests for GET /api/auth/callback."""

    def test_returns_302_redirect_to_frontend(self, client):
        """Should redirect to the frontend URL after successful callback."""
        response = client.get(
            "/api/auth/callback?code=auth-code&state=state-token"
        )

        assert response.status_code == 302
        assert response.headers["location"] == "http://localhost:3000"

    def test_sets_access_token_cookie(self, client):
        """Should set an access_token httpOnly cookie."""
        response = client.get(
            "/api/auth/callback?code=auth-code&state=state-token"
        )

        assert "access_token" in response.cookies

    def test_sets_refresh_token_cookie(self, client):
        """Should set a refresh_token httpOnly cookie."""
        response = client.get(
            "/api/auth/callback?code=auth-code&state=state-token"
        )

        assert "refresh_token" in response.cookies

    def test_rate_limit_exceeded_raises_429(
        self, app, mock_rate_limiter
    ):
        """Should raise RateLimitExceededError when rate limit is exceeded."""
        mock_rate_limiter.check_rate_limit = AsyncMock(return_value=False)
        client = TestClient(app, follow_redirects=False)

        response = client.get(
            "/api/auth/callback?code=auth-code&state=state-token"
        )

        assert response.status_code == 429

    def test_calls_handle_callback_with_code_and_state(
        self, client, mock_auth_service
    ):
        """Should pass code and state to AuthService.handle_callback."""
        client.get("/api/auth/callback?code=my-code&state=my-state")

        mock_auth_service.handle_callback.assert_called_once_with(
            code="my-code", state="my-state", code_verifier=""
        )


class TestRefreshEndpoint:
    """Tests for POST /api/auth/refresh."""

    def test_returns_200_with_message(self, client):
        """Should return 200 with success message when refresh succeeds."""
        client.cookies.set("refresh_token", "valid-refresh-token")
        response = client.post("/api/auth/refresh")

        assert response.status_code == 200
        assert response.json() == {"message": "Token refreshed"}

    def test_sets_new_access_token_cookie(self, client):
        """Should set a new access_token cookie after refresh."""
        client.cookies.set("refresh_token", "valid-refresh-token")
        response = client.post("/api/auth/refresh")

        assert "access_token" in response.cookies

    def test_raises_401_when_refresh_token_missing(self, client):
        """Should return 401 when no refresh_token cookie is present."""
        response = client.post("/api/auth/refresh")

        assert response.status_code == 401

    def test_raises_401_when_token_service_rejects(
        self, app, mock_token_service
    ):
        """Should return 401 when TokenService raises InvalidTokenError."""
        mock_token_service.refresh_access_token = AsyncMock(
            side_effect=InvalidTokenError()
        )
        client = TestClient(app)
        client.cookies.set("refresh_token", "expired-token")

        response = client.post("/api/auth/refresh")

        assert response.status_code == 401


class TestLogoutEndpoint:
    """Tests for POST /api/auth/logout."""

    def test_returns_200_with_message(self, client):
        """Should return 200 with logout confirmation."""
        client.cookies.set("refresh_token", "valid-refresh-token")
        response = client.post("/api/auth/logout")

        assert response.status_code == 200
        assert response.json() == {"message": "Logged out"}

    def test_calls_auth_service_logout(self, client, mock_auth_service):
        """Should call AuthService.logout with the refresh token."""
        client.cookies.set("refresh_token", "my-refresh-token")
        client.post("/api/auth/logout")

        mock_auth_service.logout.assert_called_once_with("my-refresh-token")

    def test_clears_access_token_cookie(self, client):
        """Should delete the access_token cookie."""
        client.cookies.set("refresh_token", "valid-refresh-token")
        client.cookies.set("access_token", "some-access-token")
        response = client.post("/api/auth/logout")

        # Cookie should be cleared (set to empty with max_age=0)
        set_cookie_headers = response.headers.get_list("set-cookie")
        access_cookie_cleared = any(
            'access_token=""' in h or "access_token=;" in h
            for h in set_cookie_headers
        )
        assert access_cookie_cleared

    def test_clears_refresh_token_cookie(self, client):
        """Should delete the refresh_token cookie."""
        client.cookies.set("refresh_token", "valid-refresh-token")
        response = client.post("/api/auth/logout")

        set_cookie_headers = response.headers.get_list("set-cookie")
        refresh_cookie_cleared = any(
            'refresh_token=""' in h or "refresh_token=;" in h
            for h in set_cookie_headers
        )
        assert refresh_cookie_cleared

    def test_succeeds_without_refresh_token(self, client, mock_auth_service):
        """Should succeed even if no refresh_token cookie is present."""
        response = client.post("/api/auth/logout")

        assert response.status_code == 200
        mock_auth_service.logout.assert_not_called()


class TestMeEndpoint:
    """Tests for GET /api/auth/me."""

    def test_returns_200_with_user_data(self, client, mock_current_user):
        """Should return 200 with user profile and grant status."""
        response = client.get("/api/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == mock_current_user.email
        assert data["name"] == mock_current_user.name
        assert data["gmail_grant_valid"] is True
        assert data["calendar_grant_valid"] is True

    def test_returns_user_id(self, client, mock_current_user):
        """Should include the user's UUID in the response."""
        response = client.get("/api/auth/me")

        data = response.json()
        assert data["id"] == str(mock_current_user.id)

    def test_returns_avatar_url(self, client, mock_current_user):
        """Should include the avatar URL in the response."""
        response = client.get("/api/auth/me")

        data = response.json()
        assert data["avatar_url"] == mock_current_user.avatar_url


class TestGrantStatusEndpoint:
    """Tests for GET /api/auth/grant-status."""

    def test_returns_200_with_grant_status(self, client):
        """Should return 200 with grant validity status."""
        response = client.get("/api/auth/grant-status")

        assert response.status_code == 200
        data = response.json()
        assert "gmail_grant_valid" in data
        assert "calendar_grant_valid" in data

    def test_returns_valid_grants(self, client):
        """Should return True for both grants when all scopes are present."""
        response = client.get("/api/auth/grant-status")

        data = response.json()
        assert data["gmail_grant_valid"] is True
        assert data["calendar_grant_valid"] is True

    def test_returns_invalid_grants_when_no_grant(
        self, app, mock_oauth_service, mock_current_user
    ):
        """Should return False for both grants when no OAuth grant exists."""
        mock_oauth_service._grant_repository.get_by_user_id = AsyncMock(
            return_value=None
        )
        client = TestClient(app)

        response = client.get("/api/auth/grant-status")

        data = response.json()
        assert data["gmail_grant_valid"] is False
        assert data["calendar_grant_valid"] is False
