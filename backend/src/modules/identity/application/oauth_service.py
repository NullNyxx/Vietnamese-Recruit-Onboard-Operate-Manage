"""OAuth service for Google OAuth2 token operations.

Handles token exchange, refresh, and scope determination for the
Identity & Auth module. Uses httpx for HTTP calls to Google's token
endpoint and CryptoUtils for encrypting/decrypting stored tokens.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

import httpx

from src.modules.identity.api.schemas import GoogleTokens, GrantStatus
from src.modules.identity.domain.exceptions import GoogleAuthError
from src.modules.identity.infrastructure.config import AuthSettings
from src.modules.identity.infrastructure.crypto_utils import CryptoUtils

if TYPE_CHECKING:
    from src.modules.identity.domain.entities import OAuthGrant

# Google OAuth2 token endpoint.
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

# Required Gmail scopes for full grant validity.
_GMAIL_SCOPES = frozenset(
    {
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.send",
    }
)

# Required Calendar scope for grant validity.
_CALENDAR_SCOPES = frozenset(
    {
        "https://www.googleapis.com/auth/calendar.events",
    }
)


class OAuthGrantRepository(Protocol):
    """Protocol for OAuthGrant persistence operations.

    This protocol defines the interface that the OAuthService depends on
    for reading and writing OAuth grant records. The concrete implementation
    will be provided via dependency injection.
    """

    async def get_by_user_id(self, user_id: UUID) -> OAuthGrant | None:
        """Retrieve the OAuth grant for a user.

        Args:
            user_id: The user's unique identifier.

        Returns:
            The OAuthGrant record, or None if no grant exists.
        """
        ...

    async def upsert(
        self,
        user_id: UUID,
        access_token_enc: str,
        refresh_token_enc: str,
        scopes: list[str],
        token_expires_at: datetime,
    ) -> OAuthGrant:
        """Create or update an OAuth grant for a user.

        Args:
            user_id: The user's unique identifier.
            access_token_enc: Encrypted Google access token.
            refresh_token_enc: Encrypted Google refresh token.
            scopes: List of granted OAuth scopes.
            token_expires_at: When the access token expires.

        Returns:
            The created or updated OAuthGrant record.
        """
        ...

    async def mark_invalid(self, user_id: UUID) -> None:
        """Mark a user's OAuth grant as invalid (revoked).

        Args:
            user_id: The user's unique identifier.
        """
        ...


class OAuthService:
    """Manages Google OAuth2 token operations.

    Provides methods for exchanging authorization codes, refreshing
    expired tokens, retrieving valid access tokens, and determining
    which scopes were granted by the user.

    Args:
        settings: Application auth configuration.
        crypto: AES-256-GCM encryption utilities.
        grant_repository: Repository for OAuth grant persistence.
    """

    def __init__(
        self,
        settings: AuthSettings,
        crypto: CryptoUtils,
        grant_repository: OAuthGrantRepository,
    ) -> None:
        """Initialize OAuthService with dependencies.

        Args:
            settings: Application auth configuration containing Google
                client credentials and redirect URI.
            crypto: Encryption utilities for securing stored tokens.
            grant_repository: Repository for reading/writing OAuth grants.
        """
        self._settings = settings
        self._crypto = crypto
        self._grant_repository = grant_repository

    async def exchange_code(self, code: str, code_verifier: str) -> GoogleTokens:
        """Exchange an authorization code for Google tokens.

        Posts to Google's token endpoint with the authorization code,
        PKCE code verifier, and client credentials to obtain access,
        refresh, and ID tokens.

        Args:
            code: The authorization code from Google's OAuth2 callback.
            code_verifier: The PKCE code verifier generated during login
                initiation.

        Returns:
            GoogleTokens containing access_token, refresh_token, id_token,
            expires_in, and scope.

        Raises:
            GoogleAuthError: If the token exchange request fails or Google
                returns an error response.
        """
        payload = {
            "code": code,
            "client_id": self._settings.google_client_id,
            "client_secret": self._settings.google_client_secret,
            "redirect_uri": self._settings.google_redirect_uri,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(_GOOGLE_TOKEN_URL, data=payload)
            except httpx.HTTPError as exc:
                raise GoogleAuthError(f"Failed to connect to Google token endpoint: {exc}") from exc

        if response.status_code != 200:
            raise GoogleAuthError(
                f"Google token exchange failed with status {response.status_code}"
            )

        data = response.json()
        return GoogleTokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            id_token=data["id_token"],
            expires_in=data["expires_in"],
            scope=data["scope"],
        )

    async def refresh_google_token(self, user_id: UUID) -> GoogleTokens | None:
        """Refresh an expired Google access token.

        Retrieves the user's stored OAuth grant, decrypts the refresh
        token, calls Google's token endpoint to obtain a new access token,
        re-encrypts the new tokens, and updates the database.

        Args:
            user_id: The user's unique identifier.

        Returns:
            Updated GoogleTokens if refresh succeeds, or None if the
            refresh token has been revoked by the user (in which case
            the grant is marked invalid).

        Raises:
            GoogleAuthError: If the grant doesn't exist or the HTTP
                request to Google fails unexpectedly.
        """
        grant = await self._grant_repository.get_by_user_id(user_id)
        if grant is None:
            raise GoogleAuthError("No OAuth grant found for user")

        refresh_token = self._crypto.decrypt(grant.refresh_token_enc)

        payload = {
            "client_id": self._settings.google_client_id,
            "client_secret": self._settings.google_client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(_GOOGLE_TOKEN_URL, data=payload)
            except httpx.HTTPError as exc:
                raise GoogleAuthError(f"Failed to connect to Google token endpoint: {exc}") from exc

        # Google returns 400 when the refresh token is revoked.
        if response.status_code == 400:
            error_data = response.json()
            if error_data.get("error") == "invalid_grant":
                await self._grant_repository.mark_invalid(user_id)
                return None
            raise GoogleAuthError(
                "Google token refresh failed: "
                f"{error_data.get('error_description', 'unknown error')}"
            )

        if response.status_code != 200:
            raise GoogleAuthError(f"Google token refresh failed with status {response.status_code}")

        data = response.json()
        new_access_token = data["access_token"]
        expires_in = data["expires_in"]
        scope = data.get("scope", " ".join(grant.scopes))

        # Google may or may not return a new refresh token.
        new_refresh_token = data.get("refresh_token", refresh_token)

        # Re-encrypt tokens and update the database.
        encrypted_access = self._crypto.encrypt(new_access_token)
        encrypted_refresh = self._crypto.encrypt(new_refresh_token)
        token_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)

        await self._grant_repository.upsert(
            user_id=user_id,
            access_token_enc=encrypted_access,
            refresh_token_enc=encrypted_refresh,
            scopes=scope.split(" ") if isinstance(scope, str) else scope,
            token_expires_at=token_expires_at,
        )

        return GoogleTokens(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            id_token="",  # Not returned on refresh
            expires_in=expires_in,
            scope=scope if isinstance(scope, str) else " ".join(scope),
        )

    async def get_valid_access_token(self, user_id: UUID) -> str:
        """Get a valid Google access token, auto-refreshing if needed.

        Checks the stored OAuth grant's expiry. If the token is still
        valid, decrypts and returns it. If expired, triggers a refresh
        and returns the new access token.

        Args:
            user_id: The user's unique identifier.

        Returns:
            A valid (non-expired) Google access token string.

        Raises:
            GoogleAuthError: If no grant exists, the grant is invalid,
                or the refresh fails (token revoked).
        """
        grant = await self._grant_repository.get_by_user_id(user_id)
        if grant is None:
            raise GoogleAuthError("No OAuth grant found for user")

        if not grant.is_valid:
            raise GoogleAuthError("OAuth grant has been revoked")

        # Check if the token is still valid (with a 60-second buffer).
        if grant.token_expires_at > datetime.now(UTC) + timedelta(seconds=60):
            return self._crypto.decrypt(grant.access_token_enc)

        # Token is expired or about to expire — refresh it.
        tokens = await self.refresh_google_token(user_id)
        if tokens is None:
            raise GoogleAuthError("Google refresh token has been revoked")

        return tokens.access_token

    def determine_grant_status(self, scopes: list[str]) -> GrantStatus:
        """Determine which OAuth scopes were granted by the user.

        Checks the provided scope list against the required Gmail and
        Calendar scopes to determine grant validity.

        Args:
            scopes: List of OAuth scope strings granted by the user.

        Returns:
            GrantStatus indicating whether Gmail and Calendar grants
            are valid.
        """
        scope_set = frozenset(scopes)
        gmail_valid = _GMAIL_SCOPES.issubset(scope_set)
        calendar_valid = _CALENDAR_SCOPES.issubset(scope_set)

        return GrantStatus(
            gmail_grant_valid=gmail_valid,
            calendar_grant_valid=calendar_valid,
        )
