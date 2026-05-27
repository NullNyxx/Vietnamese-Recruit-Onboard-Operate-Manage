"""ConnectionService for Gmail OAuth2 connection lifecycle management.

Manages the Gmail connection status, OAuth2 connect/disconnect flows,
and callback handling. Works with the existing OAuth_Grant table from
the Identity module and integrates with LabelService for post-connection
label initialization.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Protocol
from urllib.parse import urlencode
from uuid import UUID

from src.modules.gmail.domain.enums import ConnectionStatus
from src.modules.gmail.domain.exceptions import (
    GmailConnectFailedException,
)
from src.modules.gmail.infrastructure.config import GmailSettings
from src.modules.identity.infrastructure.crypto_utils import CryptoUtils

if TYPE_CHECKING:
    from src.modules.gmail.infrastructure.gmail_adapter import GmailAdapter
    from src.modules.identity.infrastructure.oauth_grant_repository import (
        OAuthGrantRepository,
    )


class LabelServiceProtocol(Protocol):
    """Protocol for LabelService dependency to avoid circular imports."""

    async def initialize_labels(self, user_id: UUID, access_token: str) -> None:
        """Initialize VroomHR labels on the user's Gmail account."""
        ...


logger = logging.getLogger(__name__)

# Google OAuth2 authorization endpoint.
_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

# Required Gmail scopes for full connection.
GMAIL_SCOPES = frozenset(
    {
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.send",
    }
)

_GMAIL_SCOPE_STRING = " ".join(sorted(GMAIL_SCOPES))


@dataclass
class ConnectionStatusResponse:
    """Response for connection status queries.

    Attributes:
        status: The current connection status.
        email: The connected Gmail email address (if connected).
    """

    status: ConnectionStatus
    email: str | None = None


@dataclass
class ConnectResponse:
    """Response for connection initiation.

    Attributes:
        status: The current connection status (connected if already valid).
        redirect_url: OAuth2 redirect URL (if connection flow needed).
    """

    status: ConnectionStatus | None = None
    redirect_url: str | None = None


class ConnectionService:
    """Manages Gmail OAuth2 connection status and lifecycle.

    Provides methods to check connection status, initiate OAuth2 connect
    flow, handle OAuth2 callbacks, and disconnect (revoke tokens).

    Args:
        settings: Gmail module configuration.
        auth_settings_client_id: Google OAuth2 client ID.
        auth_settings_client_secret: Google OAuth2 client secret.
        gmail_redirect_uri: OAuth2 callback URL for Gmail connection.
        oauth_grant_repo: Repository for OAuth grant persistence.
        gmail_adapter: Gmail API adapter for token operations.
        crypto: AES-256-GCM encryption utilities.
        label_service: LabelService for post-connection label initialization.
    """

    def __init__(
        self,
        settings: GmailSettings,
        auth_settings_client_id: str,
        auth_settings_client_secret: str,
        gmail_redirect_uri: str,
        oauth_grant_repo: OAuthGrantRepository,
        gmail_adapter: GmailAdapter,
        crypto: CryptoUtils,
        label_service: LabelServiceProtocol | None = None,
    ) -> None:
        """Initialize ConnectionService with dependencies.

        Args:
            settings: Gmail module configuration.
            auth_settings_client_id: Google OAuth2 client ID.
            auth_settings_client_secret: Google OAuth2 client secret.
            gmail_redirect_uri: OAuth2 callback URL for Gmail connection.
            oauth_grant_repo: Repository for OAuth grant persistence.
            gmail_adapter: Gmail API adapter for token operations.
            crypto: AES-256-GCM encryption utilities.
            label_service: LabelService for post-connection label initialization.
        """
        self._settings = settings
        self._client_id = auth_settings_client_id
        self._client_secret = auth_settings_client_secret
        self._gmail_redirect_uri = gmail_redirect_uri
        self._oauth_grant_repo = oauth_grant_repo
        self._gmail_adapter = gmail_adapter
        self._crypto = crypto
        self._label_service = label_service

    async def get_status(self, user_id: UUID) -> ConnectionStatusResponse:
        """Determine the current Gmail connection status for a user.

        Checks the OAuth_Grant record to determine connection state:
        - No grant with Gmail scopes → disconnected
        - Grant exists, is_valid=true, token not expired → connected
        - Grant exists, is_valid=false or token expired → token_expired

        Args:
            user_id: The UUID of the user to check.

        Returns:
            ConnectionStatusResponse with the current status.
        """
        grant = await self._oauth_grant_repo.get_by_user_id(user_id)

        if grant is None:
            return ConnectionStatusResponse(status=ConnectionStatus.disconnected)

        # Check if the grant has Gmail scopes
        if not self._has_gmail_scopes(grant.scopes):
            return ConnectionStatusResponse(status=ConnectionStatus.disconnected)

        # Grant exists with Gmail scopes — check validity
        if not grant.is_valid:
            return ConnectionStatusResponse(status=ConnectionStatus.token_expired)

        # Check token expiry
        if grant.token_expires_at <= datetime.now(UTC):
            return ConnectionStatusResponse(status=ConnectionStatus.token_expired)

        # Connected — decrypt access token to get email is not needed here,
        # but we return connected status
        return ConnectionStatusResponse(status=ConnectionStatus.connected)

    async def initiate_connect(self, user_id: UUID) -> ConnectResponse:
        """Initiate Gmail OAuth2 connection flow.

        If the user already has a valid Gmail connection (valid grant with
        Gmail scopes and non-expired token), returns the existing connected
        status. Otherwise, generates an OAuth2 redirect URL for the Google
        consent screen.

        Args:
            user_id: The UUID of the user initiating the connection.

        Returns:
            ConnectResponse with either connected status or redirect_url.
        """
        grant = await self._oauth_grant_repo.get_by_user_id(user_id)

        # Check if already connected with valid Gmail scopes
        if grant is not None and self._has_gmail_scopes(grant.scopes):
            if grant.is_valid and grant.token_expires_at > datetime.now(UTC):
                return ConnectResponse(status=ConnectionStatus.connected)

        # Need to initiate OAuth2 flow — generate redirect URL
        redirect_url = self._build_oauth2_redirect_url()
        return ConnectResponse(redirect_url=redirect_url)

    async def handle_callback(self, user_id: UUID, code: str) -> ConnectionStatusResponse:
        """Handle the OAuth2 callback after user consent.

        Exchanges the authorization code for tokens, validates that all
        required Gmail scopes were granted, encrypts and stores the tokens,
        and triggers label initialization.

        Args:
            user_id: The UUID of the user completing the OAuth2 flow.
            code: The authorization code from Google's OAuth2 callback.

        Returns:
            ConnectionStatusResponse with connected status on success.

        Raises:
            GmailConnectFailedException: If the token exchange fails,
                the user denied scopes, or only partial scopes were granted.
        """
        import httpx

        # Exchange authorization code for tokens
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    _GOOGLE_TOKEN_URL,
                    data={
                        "code": code,
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "redirect_uri": self._gmail_redirect_uri,
                        "grant_type": "authorization_code",
                    },
                )
        except httpx.HTTPError as exc:
            logger.error("OAuth2 token exchange HTTP error: %s", exc)
            raise GmailConnectFailedException("Failed to connect to Google token endpoint") from exc

        if response.status_code != 200:
            logger.error(
                "OAuth2 token exchange failed with status %d: %s",
                response.status_code,
                response.text,
            )
            raise GmailConnectFailedException("OAuth2 token exchange failed")

        data = response.json()
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        expires_in = data.get("expires_in", 3600)
        scope_str = data.get("scope", "")

        if not access_token:
            raise GmailConnectFailedException("No access token received from Google")

        # Validate that all required Gmail scopes were granted
        granted_scopes = set(scope_str.split()) if scope_str else set()
        if not GMAIL_SCOPES.issubset(granted_scopes):
            missing = GMAIL_SCOPES - granted_scopes
            logger.warning(
                "Gmail connect missing scopes: %s (granted: %s)",
                missing,
                granted_scopes,
            )
            raise GmailConnectFailedException(
                f"Required Gmail scopes not granted: {', '.join(sorted(missing))}"
            )

        # Encrypt tokens for storage
        encrypted_access = self._crypto.encrypt(access_token)
        encrypted_refresh = self._crypto.encrypt(refresh_token or "")

        token_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)

        # Store encrypted tokens in OAuth_Grant
        await self._oauth_grant_repo.upsert(
            user_id=user_id,
            access_token_enc=encrypted_access,
            refresh_token_enc=encrypted_refresh,
            scopes=list(granted_scopes),
            token_expires_at=token_expires_at,
        )

        # Trigger label initialization (fire-and-forget style, log errors)
        if self._label_service is not None:
            try:
                await self._label_service.initialize_labels(
                    user_id=user_id, access_token=access_token
                )
            except Exception as exc:
                logger.warning(
                    "Label initialization failed after connect (will retry on next poll): %s",
                    exc,
                )

        return ConnectionStatusResponse(status=ConnectionStatus.connected)

    async def disconnect(self, user_id: UUID) -> ConnectionStatusResponse:
        """Disconnect Gmail by revoking tokens and invalidating the grant.

        Attempts to revoke the token via Google's revocation endpoint with
        a 10-second timeout. Regardless of whether revocation succeeds,
        marks the OAuth_Grant as invalid and removes Gmail scopes.

        Args:
            user_id: The UUID of the user disconnecting Gmail.

        Returns:
            ConnectionStatusResponse with disconnected status.
        """
        grant = await self._oauth_grant_repo.get_by_user_id(user_id)

        if grant is None or not self._has_gmail_scopes(grant.scopes):
            # Already disconnected
            return ConnectionStatusResponse(status=ConnectionStatus.disconnected)

        # Attempt to revoke the token (proceed on failure)
        try:
            refresh_token = self._crypto.decrypt(grant.refresh_token_enc)
            if refresh_token:
                revoked = await self._gmail_adapter.revoke_token(refresh_token)
                if not revoked:
                    logger.warning(
                        "Token revocation failed or timed out for user %s,"
                        " proceeding with disconnect",
                        user_id,
                    )
        except Exception as exc:
            logger.warning(
                "Error during token revocation for user %s: %s, proceeding with disconnect",
                user_id,
                exc,
            )

        # Mark grant as invalid and remove Gmail scopes
        await self._oauth_grant_repo.mark_invalid(user_id)

        return ConnectionStatusResponse(status=ConnectionStatus.disconnected)

    def _has_gmail_scopes(self, scopes: list[str]) -> bool:
        """Check if the given scopes include all required Gmail scopes.

        Args:
            scopes: List of OAuth scope strings from the grant.

        Returns:
            True if all required Gmail scopes are present.
        """
        return GMAIL_SCOPES.issubset(set(scopes))

    def _build_oauth2_redirect_url(self) -> str:
        """Build the Google OAuth2 consent screen redirect URL.

        Constructs the URL with required parameters including Gmail
        scopes (gmail.readonly, gmail.modify, gmail.send), access_type
        offline for refresh token, and prompt consent.

        Returns:
            The full OAuth2 authorization URL string.
        """
        params = {
            "client_id": self._client_id,
            "redirect_uri": self._gmail_redirect_uri,
            "response_type": "code",
            "scope": _GMAIL_SCOPE_STRING,
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{_GOOGLE_AUTH_URL}?{urlencode(params)}"
