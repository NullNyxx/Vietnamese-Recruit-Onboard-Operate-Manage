"""Unit tests for ConnectionService."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.modules.gmail.application.connection_service import (
    GMAIL_SCOPES,
    ConnectionService,
    ConnectionStatusResponse,
    ConnectResponse,
)
from src.modules.gmail.domain.enums import ConnectionStatus
from src.modules.gmail.domain.exceptions import GmailConnectFailedException
from src.modules.gmail.infrastructure.config import GmailSettings
from src.modules.identity.infrastructure.crypto_utils import CryptoUtils


@pytest.fixture
def settings() -> GmailSettings:
    """Create GmailSettings with defaults."""
    return GmailSettings()


@pytest.fixture
def oauth_grant_repo() -> AsyncMock:
    """Create a mocked OAuthGrantRepository."""
    return AsyncMock()


@pytest.fixture
def gmail_adapter() -> AsyncMock:
    """Create a mocked GmailAdapter."""
    return AsyncMock()


@pytest.fixture
def crypto() -> MagicMock:
    """Create a mocked CryptoUtils."""
    mock = MagicMock(spec=CryptoUtils)
    mock.encrypt.side_effect = lambda x: f"encrypted_{x}"
    mock.decrypt.side_effect = lambda x: x.replace("encrypted_", "")
    return mock


@pytest.fixture
def label_service() -> AsyncMock:
    """Create a mocked LabelService."""
    return AsyncMock()


@pytest.fixture
def connection_service(
    settings: GmailSettings,
    oauth_grant_repo: AsyncMock,
    gmail_adapter: AsyncMock,
    crypto: MagicMock,
    label_service: AsyncMock,
) -> ConnectionService:
    """Create a ConnectionService with mocked dependencies."""
    return ConnectionService(
        settings=settings,
        auth_settings_client_id="test-client-id",
        auth_settings_client_secret="test-client-secret",
        gmail_redirect_uri="http://localhost:8000/api/gmail/callback",
        oauth_grant_repo=oauth_grant_repo,
        gmail_adapter=gmail_adapter,
        crypto=crypto,
        label_service=label_service,
    )


def _make_grant(
    *,
    is_valid: bool = True,
    scopes: list[str] | None = None,
    token_expires_at: datetime | None = None,
    refresh_token_enc: str = "encrypted_refresh_token",
) -> MagicMock:
    """Create a mock OAuth grant with configurable fields."""
    grant = MagicMock()
    grant.is_valid = is_valid
    grant.scopes = scopes or list(GMAIL_SCOPES)
    grant.token_expires_at = token_expires_at or (datetime.now(UTC) + timedelta(hours=1))
    grant.refresh_token_enc = refresh_token_enc
    grant.access_token_enc = "encrypted_access_token"
    return grant


class TestGetStatus:
    """Tests for ConnectionService.get_status."""

    async def test_returns_disconnected_when_no_grant(
        self, connection_service: ConnectionService, oauth_grant_repo: AsyncMock
    ) -> None:
        """Returns disconnected when no OAuth grant exists."""
        oauth_grant_repo.get_by_user_id.return_value = None
        user_id = uuid4()

        result = await connection_service.get_status(user_id)

        assert result.status == ConnectionStatus.disconnected
        assert result.email is None

    async def test_returns_disconnected_when_no_gmail_scopes(
        self, connection_service: ConnectionService, oauth_grant_repo: AsyncMock
    ) -> None:
        """Returns disconnected when grant exists but lacks Gmail scopes."""
        grant = _make_grant(scopes=["openid", "email", "profile"])
        oauth_grant_repo.get_by_user_id.return_value = grant
        user_id = uuid4()

        result = await connection_service.get_status(user_id)

        assert result.status == ConnectionStatus.disconnected

    async def test_returns_connected_when_valid_grant_with_gmail_scopes(
        self, connection_service: ConnectionService, oauth_grant_repo: AsyncMock
    ) -> None:
        """Returns connected when grant is valid with Gmail scopes and future expiry."""
        grant = _make_grant(
            is_valid=True,
            token_expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        oauth_grant_repo.get_by_user_id.return_value = grant
        user_id = uuid4()

        result = await connection_service.get_status(user_id)

        assert result.status == ConnectionStatus.connected

    async def test_returns_token_expired_when_invalid_grant(
        self, connection_service: ConnectionService, oauth_grant_repo: AsyncMock
    ) -> None:
        """Returns token_expired when grant exists but is_valid is false."""
        grant = _make_grant(is_valid=False)
        oauth_grant_repo.get_by_user_id.return_value = grant
        user_id = uuid4()

        result = await connection_service.get_status(user_id)

        assert result.status == ConnectionStatus.token_expired

    async def test_returns_token_expired_when_token_past_expiry(
        self, connection_service: ConnectionService, oauth_grant_repo: AsyncMock
    ) -> None:
        """Returns token_expired when token_expires_at is in the past."""
        grant = _make_grant(
            is_valid=True,
            token_expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        oauth_grant_repo.get_by_user_id.return_value = grant
        user_id = uuid4()

        result = await connection_service.get_status(user_id)

        assert result.status == ConnectionStatus.token_expired


class TestInitiateConnect:
    """Tests for ConnectionService.initiate_connect."""

    async def test_returns_connected_when_already_valid(
        self, connection_service: ConnectionService, oauth_grant_repo: AsyncMock
    ) -> None:
        """Returns connected status when user already has valid Gmail connection."""
        grant = _make_grant(
            is_valid=True,
            token_expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        oauth_grant_repo.get_by_user_id.return_value = grant
        user_id = uuid4()

        result = await connection_service.initiate_connect(user_id)

        assert result.status == ConnectionStatus.connected
        assert result.redirect_url is None

    async def test_returns_redirect_url_when_no_grant(
        self, connection_service: ConnectionService, oauth_grant_repo: AsyncMock
    ) -> None:
        """Returns redirect URL when no grant exists."""
        oauth_grant_repo.get_by_user_id.return_value = None
        user_id = uuid4()

        result = await connection_service.initiate_connect(user_id)

        assert result.redirect_url is not None
        assert "accounts.google.com" in result.redirect_url
        assert "gmail.readonly" in result.redirect_url
        assert "gmail.modify" in result.redirect_url
        assert "gmail.send" in result.redirect_url

    async def test_returns_redirect_url_when_grant_invalid(
        self, connection_service: ConnectionService, oauth_grant_repo: AsyncMock
    ) -> None:
        """Returns redirect URL when grant exists but is invalid."""
        grant = _make_grant(is_valid=False)
        oauth_grant_repo.get_by_user_id.return_value = grant
        user_id = uuid4()

        result = await connection_service.initiate_connect(user_id)

        assert result.redirect_url is not None
        assert "accounts.google.com" in result.redirect_url

    async def test_returns_redirect_url_when_token_expired(
        self, connection_service: ConnectionService, oauth_grant_repo: AsyncMock
    ) -> None:
        """Returns redirect URL when token is expired."""
        grant = _make_grant(
            is_valid=True,
            token_expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        oauth_grant_repo.get_by_user_id.return_value = grant
        user_id = uuid4()

        result = await connection_service.initiate_connect(user_id)

        assert result.redirect_url is not None

    async def test_redirect_url_contains_required_params(
        self, connection_service: ConnectionService, oauth_grant_repo: AsyncMock
    ) -> None:
        """Redirect URL contains client_id, redirect_uri, access_type offline."""
        oauth_grant_repo.get_by_user_id.return_value = None
        user_id = uuid4()

        result = await connection_service.initiate_connect(user_id)

        assert "client_id=test-client-id" in result.redirect_url
        assert "access_type=offline" in result.redirect_url
        assert "prompt=consent" in result.redirect_url
        assert "response_type=code" in result.redirect_url


class TestHandleCallback:
    """Tests for ConnectionService.handle_callback."""

    async def test_stores_encrypted_tokens_on_success(
        self,
        connection_service: ConnectionService,
        oauth_grant_repo: AsyncMock,
        crypto: MagicMock,
        label_service: AsyncMock,
    ) -> None:
        """Stores encrypted tokens and returns connected on successful callback."""
        user_id = uuid4()
        scope_str = " ".join(GMAIL_SCOPES)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "expires_in": 3600,
                "scope": scope_str,
            }
            mock_client.post.return_value = mock_response

            result = await connection_service.handle_callback(user_id, "auth_code")

        assert result.status == ConnectionStatus.connected
        crypto.encrypt.assert_any_call("new_access_token")
        crypto.encrypt.assert_any_call("new_refresh_token")
        oauth_grant_repo.upsert.assert_called_once()

    async def test_triggers_label_initialization(
        self,
        connection_service: ConnectionService,
        oauth_grant_repo: AsyncMock,
        label_service: AsyncMock,
    ) -> None:
        """Triggers label initialization after successful callback."""
        user_id = uuid4()
        scope_str = " ".join(GMAIL_SCOPES)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "expires_in": 3600,
                "scope": scope_str,
            }
            mock_client.post.return_value = mock_response

            await connection_service.handle_callback(user_id, "auth_code")

        label_service.initialize_labels.assert_called_once_with(
            user_id=user_id, access_token="new_access_token"
        )

    async def test_raises_on_token_exchange_failure(
        self, connection_service: ConnectionService
    ) -> None:
        """Raises GmailConnectFailedException when token exchange fails."""
        user_id = uuid4()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.text = "invalid_grant"
            mock_client.post.return_value = mock_response

            with pytest.raises(GmailConnectFailedException):
                await connection_service.handle_callback(user_id, "bad_code")

    async def test_raises_on_missing_scopes(
        self, connection_service: ConnectionService
    ) -> None:
        """Raises GmailConnectFailedException when not all scopes granted."""
        user_id = uuid4()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "token",
                "refresh_token": "refresh",
                "expires_in": 3600,
                "scope": "https://www.googleapis.com/auth/gmail.readonly",
            }
            mock_client.post.return_value = mock_response

            with pytest.raises(GmailConnectFailedException):
                await connection_service.handle_callback(user_id, "auth_code")

    async def test_proceeds_when_label_init_fails(
        self,
        connection_service: ConnectionService,
        oauth_grant_repo: AsyncMock,
        label_service: AsyncMock,
    ) -> None:
        """Proceeds with connected status even if label initialization fails."""
        user_id = uuid4()
        scope_str = " ".join(GMAIL_SCOPES)
        label_service.initialize_labels.side_effect = Exception("Label API error")

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "expires_in": 3600,
                "scope": scope_str,
            }
            mock_client.post.return_value = mock_response

            result = await connection_service.handle_callback(user_id, "auth_code")

        assert result.status == ConnectionStatus.connected


class TestDisconnect:
    """Tests for ConnectionService.disconnect."""

    async def test_revokes_token_and_marks_invalid(
        self,
        connection_service: ConnectionService,
        oauth_grant_repo: AsyncMock,
        gmail_adapter: AsyncMock,
        crypto: MagicMock,
    ) -> None:
        """Revokes token and marks grant invalid on disconnect."""
        user_id = uuid4()
        grant = _make_grant(refresh_token_enc="encrypted_refresh_token")
        oauth_grant_repo.get_by_user_id.return_value = grant
        gmail_adapter.revoke_token.return_value = True

        result = await connection_service.disconnect(user_id)

        assert result.status == ConnectionStatus.disconnected
        gmail_adapter.revoke_token.assert_called_once_with("refresh_token")
        oauth_grant_repo.mark_invalid.assert_called_once_with(user_id)

    async def test_proceeds_when_revocation_fails(
        self,
        connection_service: ConnectionService,
        oauth_grant_repo: AsyncMock,
        gmail_adapter: AsyncMock,
    ) -> None:
        """Marks grant invalid even when token revocation fails."""
        user_id = uuid4()
        grant = _make_grant(refresh_token_enc="encrypted_refresh_token")
        oauth_grant_repo.get_by_user_id.return_value = grant
        gmail_adapter.revoke_token.return_value = False

        result = await connection_service.disconnect(user_id)

        assert result.status == ConnectionStatus.disconnected
        oauth_grant_repo.mark_invalid.assert_called_once_with(user_id)

    async def test_proceeds_when_revocation_raises(
        self,
        connection_service: ConnectionService,
        oauth_grant_repo: AsyncMock,
        gmail_adapter: AsyncMock,
    ) -> None:
        """Marks grant invalid even when revocation raises an exception."""
        user_id = uuid4()
        grant = _make_grant(refresh_token_enc="encrypted_refresh_token")
        oauth_grant_repo.get_by_user_id.return_value = grant
        gmail_adapter.revoke_token.side_effect = Exception("Network error")

        result = await connection_service.disconnect(user_id)

        assert result.status == ConnectionStatus.disconnected
        oauth_grant_repo.mark_invalid.assert_called_once_with(user_id)

    async def test_returns_disconnected_when_no_grant(
        self,
        connection_service: ConnectionService,
        oauth_grant_repo: AsyncMock,
        gmail_adapter: AsyncMock,
    ) -> None:
        """Returns disconnected without calling revoke when no grant exists."""
        user_id = uuid4()
        oauth_grant_repo.get_by_user_id.return_value = None

        result = await connection_service.disconnect(user_id)

        assert result.status == ConnectionStatus.disconnected
        gmail_adapter.revoke_token.assert_not_called()
        oauth_grant_repo.mark_invalid.assert_not_called()

    async def test_returns_disconnected_when_no_gmail_scopes(
        self,
        connection_service: ConnectionService,
        oauth_grant_repo: AsyncMock,
        gmail_adapter: AsyncMock,
    ) -> None:
        """Returns disconnected without revoking when grant has no Gmail scopes."""
        user_id = uuid4()
        grant = _make_grant(scopes=["openid", "email"])
        oauth_grant_repo.get_by_user_id.return_value = grant

        result = await connection_service.disconnect(user_id)

        assert result.status == ConnectionStatus.disconnected
        gmail_adapter.revoke_token.assert_not_called()
        oauth_grant_repo.mark_invalid.assert_not_called()
