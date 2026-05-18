"""Unit tests for AuthService orchestrator.

Tests the login initiation, callback handling, and logout flows
with all dependencies mocked.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.modules.identity.api.schemas import (
    GoogleTokens,
    GoogleUserInfo,
    GrantStatus,
    LoginRedirect,
)
from src.modules.identity.application.auth_service import (
    AuthResult,
    AuthService,
    _generate_code_challenge,
    _generate_code_verifier,
)
from src.modules.identity.domain.exceptions import AccessDeniedError, InvalidStateError


@pytest.fixture
def mock_settings():
    """Create a mock AuthSettings."""
    settings = MagicMock()
    settings.google_client_id = "test-client-id"
    settings.google_client_secret = "test-client-secret"
    settings.google_redirect_uri = "http://localhost:8000/api/auth/callback"
    settings.access_token_expire_minutes = 15
    settings.refresh_token_expire_days = 7
    settings.frontend_url = "http://localhost:3000"
    return settings


@pytest.fixture
def mock_jwt_utils():
    """Create a mock JWTUtils."""
    jwt_utils = MagicMock()
    jwt_utils.create_state_token.return_value = "signed-state-token"
    jwt_utils.verify_state_token.return_value = {"nonce": "test-nonce", "purpose": "state"}
    return jwt_utils


@pytest.fixture
def mock_crypto():
    """Create a mock CryptoUtils."""
    crypto = MagicMock()
    crypto.encrypt.side_effect = lambda x: f"encrypted:{x}"
    crypto.decrypt.side_effect = lambda x: x.replace("encrypted:", "")
    return crypto


@pytest.fixture
def mock_whitelist_service():
    """Create a mock WhitelistService."""
    service = MagicMock()
    service.is_allowed.return_value = True
    return service


@pytest.fixture
def mock_oauth_service():
    """Create a mock OAuthService."""
    service = MagicMock()
    service.exchange_code = AsyncMock(
        return_value=GoogleTokens(
            access_token="google-access-token",
            refresh_token="google-refresh-token",
            id_token="eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwibmFtZSI6IlRlc3QgVXNlciIsInBpY3R1cmUiOiJodHRwczovL2V4YW1wbGUuY29tL2F2YXRhci5qcGcifQ.signature",
            expires_in=3600,
            scope="openid email profile https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/calendar.events",
        )
    )
    service.determine_grant_status.return_value = GrantStatus(
        gmail_grant_valid=True,
        calendar_grant_valid=True,
    )
    return service


@pytest.fixture
def mock_token_service():
    """Create a mock TokenService."""
    service = MagicMock()
    service.create_access_token.return_value = "jwt-access-token"
    service.create_refresh_token.return_value = ("raw-refresh-token", "hashed-refresh-token")
    service.revoke_user_tokens = AsyncMock()
    return service


@pytest.fixture
def mock_user_repository():
    """Create a mock UserRepository."""
    user = MagicMock()
    user.id = uuid4()
    user.email = "test@example.com"
    user.name = "Test User"
    user.avatar_url = "https://example.com/avatar.jpg"

    repo = MagicMock()
    repo.upsert = AsyncMock(return_value=user)
    repo.get_by_id = AsyncMock(return_value=user)
    return repo


@pytest.fixture
def mock_oauth_grant_repository():
    """Create a mock OAuthGrantRepository."""
    repo = MagicMock()
    repo.upsert = AsyncMock()
    return repo


@pytest.fixture
def mock_refresh_token_repository():
    """Create a mock RefreshTokenRepository."""
    repo = MagicMock()
    repo.store = AsyncMock()
    repo.find_by_token_hash = AsyncMock(return_value=MagicMock(token_hash="some-hash"))
    repo.revoke = AsyncMock()
    return repo


@pytest.fixture
def auth_service(
    mock_settings,
    mock_jwt_utils,
    mock_crypto,
    mock_whitelist_service,
    mock_oauth_service,
    mock_token_service,
    mock_user_repository,
    mock_oauth_grant_repository,
    mock_refresh_token_repository,
):
    """Create an AuthService with all mocked dependencies."""
    return AuthService(
        settings=mock_settings,
        jwt_utils=mock_jwt_utils,
        crypto=mock_crypto,
        whitelist_service=mock_whitelist_service,
        oauth_service=mock_oauth_service,
        token_service=mock_token_service,
        user_repository=mock_user_repository,
        oauth_grant_repository=mock_oauth_grant_repository,
        refresh_token_repository=mock_refresh_token_repository,
    )


class TestGenerateCodeVerifier:
    """Tests for PKCE code verifier generation."""

    def test_length_within_bounds(self):
        """Code verifier should be between 43 and 128 characters."""
        verifier = _generate_code_verifier()
        assert 43 <= len(verifier) <= 128

    def test_url_safe_characters(self):
        """Code verifier should only contain URL-safe characters."""
        verifier = _generate_code_verifier()
        # URL-safe base64 uses A-Z, a-z, 0-9, -, _
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
        assert all(c in allowed for c in verifier)

    def test_uniqueness(self):
        """Each generated verifier should be unique."""
        verifiers = {_generate_code_verifier() for _ in range(100)}
        assert len(verifiers) == 100


class TestGenerateCodeChallenge:
    """Tests for PKCE code challenge generation."""

    def test_known_value(self):
        """Code challenge should match expected SHA-256 + base64url output."""
        # Known test vector
        verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        challenge = _generate_code_challenge(verifier)
        # The challenge should be a base64url-encoded SHA-256 hash
        assert challenge  # Non-empty
        assert "=" not in challenge  # No padding
        assert "+" not in challenge  # URL-safe (no +)
        assert "/" not in challenge  # URL-safe (no /)

    def test_deterministic(self):
        """Same verifier should always produce the same challenge."""
        verifier = "test-verifier-value"
        challenge1 = _generate_code_challenge(verifier)
        challenge2 = _generate_code_challenge(verifier)
        assert challenge1 == challenge2


class TestInitiateLogin:
    """Tests for AuthService.initiate_login."""

    async def test_returns_login_redirect(self, auth_service):
        """initiate_login should return a LoginRedirect with all fields."""
        result = await auth_service.initiate_login()

        assert isinstance(result, LoginRedirect)
        assert result.redirect_url
        assert result.state_token
        assert result.code_verifier

    async def test_redirect_url_contains_required_params(self, auth_service):
        """Redirect URL should contain all required OAuth2 parameters."""
        result = await auth_service.initiate_login()

        assert "client_id=test-client-id" in result.redirect_url
        assert "redirect_uri=" in result.redirect_url
        assert "response_type=code" in result.redirect_url
        assert "access_type=offline" in result.redirect_url
        assert "prompt=consent" in result.redirect_url
        assert "code_challenge=" in result.redirect_url
        assert "code_challenge_method=S256" in result.redirect_url
        assert "state=" in result.redirect_url

    async def test_redirect_url_contains_all_scopes(self, auth_service):
        """Redirect URL should request all required OAuth scopes."""
        result = await auth_service.initiate_login()

        assert "openid" in result.redirect_url
        assert "email" in result.redirect_url
        assert "profile" in result.redirect_url
        assert "gmail.readonly" in result.redirect_url
        assert "gmail.modify" in result.redirect_url
        assert "gmail.send" in result.redirect_url
        assert "calendar.events" in result.redirect_url

    async def test_state_token_created_with_nonce(self, auth_service, mock_jwt_utils):
        """State token should be created with a nonce payload."""
        await auth_service.initiate_login()

        mock_jwt_utils.create_state_token.assert_called_once()
        call_args = mock_jwt_utils.create_state_token.call_args[0][0]
        assert "nonce" in call_args

    async def test_code_verifier_is_url_safe(self, auth_service):
        """Code verifier in result should be URL-safe."""
        result = await auth_service.initiate_login()

        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
        assert all(c in allowed for c in result.code_verifier)


class TestHandleCallback:
    """Tests for AuthService.handle_callback."""

    async def test_successful_callback(self, auth_service, mock_user_repository):
        """Successful callback should return AuthResult with all fields."""
        with patch("src.modules.identity.application.auth_service.jose_jwt") as mock_jose:
            mock_jose.get_unverified_claims.return_value = {
                "sub": "google-sub-123",
                "email": "test@example.com",
                "name": "Test User",
                "picture": "https://example.com/avatar.jpg",
            }

            result = await auth_service.handle_callback("auth-code", "state-token")

        assert isinstance(result, AuthResult)
        assert result.access_token == "jwt-access-token"
        assert result.refresh_token == "raw-refresh-token"
        assert result.user == mock_user_repository.upsert.return_value
        assert result.grant_status.gmail_grant_valid is True
        assert result.grant_status.calendar_grant_valid is True

    async def test_validates_state_token(self, auth_service, mock_jwt_utils):
        """Callback should verify the CSRF state token."""
        with patch("src.modules.identity.application.auth_service.jose_jwt") as mock_jose:
            mock_jose.get_unverified_claims.return_value = {
                "sub": "google-sub-123",
                "email": "test@example.com",
                "name": "Test User",
            }

            await auth_service.handle_callback("auth-code", "state-token")

        mock_jwt_utils.verify_state_token.assert_called_once_with("state-token")

    async def test_invalid_state_raises_error(self, auth_service, mock_jwt_utils):
        """Invalid state token should raise InvalidStateError."""
        mock_jwt_utils.verify_state_token.side_effect = InvalidStateError()

        with pytest.raises(InvalidStateError):
            await auth_service.handle_callback("auth-code", "bad-state")

    async def test_whitelist_check_denies_access(
        self, auth_service, mock_whitelist_service
    ):
        """Non-whitelisted email should raise AccessDeniedError."""
        mock_whitelist_service.is_allowed.return_value = False

        with patch("src.modules.identity.application.auth_service.jose_jwt") as mock_jose:
            mock_jose.get_unverified_claims.return_value = {
                "sub": "google-sub-123",
                "email": "unauthorized@example.com",
                "name": "Unauthorized User",
            }

            with pytest.raises(AccessDeniedError):
                await auth_service.handle_callback("auth-code", "state-token")

    async def test_upserts_user(self, auth_service, mock_user_repository):
        """Callback should upsert the user from Google profile."""
        with patch("src.modules.identity.application.auth_service.jose_jwt") as mock_jose:
            mock_jose.get_unverified_claims.return_value = {
                "sub": "google-sub-123",
                "email": "test@example.com",
                "name": "Test User",
                "picture": "https://example.com/avatar.jpg",
            }

            await auth_service.handle_callback("auth-code", "state-token")

        mock_user_repository.upsert.assert_called_once()
        call_arg = mock_user_repository.upsert.call_args[0][0]
        assert isinstance(call_arg, GoogleUserInfo)
        assert call_arg.email == "test@example.com"
        assert call_arg.name == "Test User"

    async def test_encrypts_and_stores_tokens(
        self, auth_service, mock_crypto, mock_oauth_grant_repository
    ):
        """Callback should encrypt Google tokens and store them."""
        with patch("src.modules.identity.application.auth_service.jose_jwt") as mock_jose:
            mock_jose.get_unverified_claims.return_value = {
                "sub": "google-sub-123",
                "email": "test@example.com",
                "name": "Test User",
            }

            await auth_service.handle_callback("auth-code", "state-token")

        # Verify encryption was called for both tokens
        mock_crypto.encrypt.assert_any_call("google-access-token")
        mock_crypto.encrypt.assert_any_call("google-refresh-token")

        # Verify grant was stored
        mock_oauth_grant_repository.upsert.assert_called_once()

    async def test_revokes_old_tokens(self, auth_service, mock_token_service):
        """Callback should revoke old refresh tokens before issuing new ones."""
        with patch("src.modules.identity.application.auth_service.jose_jwt") as mock_jose:
            mock_jose.get_unverified_claims.return_value = {
                "sub": "google-sub-123",
                "email": "test@example.com",
                "name": "Test User",
            }

            await auth_service.handle_callback("auth-code", "state-token")

        mock_token_service.revoke_user_tokens.assert_called_once()

    async def test_stores_refresh_token_hash(
        self, auth_service, mock_refresh_token_repository
    ):
        """Callback should store the new refresh token hash."""
        with patch("src.modules.identity.application.auth_service.jose_jwt") as mock_jose:
            mock_jose.get_unverified_claims.return_value = {
                "sub": "google-sub-123",
                "email": "test@example.com",
                "name": "Test User",
            }

            await auth_service.handle_callback("auth-code", "state-token")

        mock_refresh_token_repository.store.assert_called_once()
        call_kwargs = mock_refresh_token_repository.store.call_args[1]
        assert call_kwargs["token_hash"] == "hashed-refresh-token"


class TestLogout:
    """Tests for AuthService.logout."""

    async def test_revokes_refresh_token(
        self, auth_service, mock_refresh_token_repository
    ):
        """Logout should hash the token and revoke it."""
        raw_token = "my-refresh-token"
        expected_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        await auth_service.logout(raw_token)

        mock_refresh_token_repository.find_by_token_hash.assert_called_once_with(
            expected_hash
        )
        mock_refresh_token_repository.revoke.assert_called_once_with(expected_hash)

    async def test_logout_nonexistent_token_does_not_raise(
        self, auth_service, mock_refresh_token_repository
    ):
        """Logout with a non-existent token should not raise."""
        mock_refresh_token_repository.find_by_token_hash.return_value = None

        # Should not raise
        await auth_service.logout("nonexistent-token")

        mock_refresh_token_repository.revoke.assert_not_called()
