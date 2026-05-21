"""AuthService orchestrator for the Identity & Auth module.

Coordinates the complete OAuth2 authentication flow including login
initiation with PKCE, callback handling with whitelist validation,
and logout with token revocation.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from urllib.parse import urlencode

from jose import jwt as jose_jwt

from src.modules.identity.api.schemas import GoogleUserInfo, GrantStatus, LoginRedirect
from src.modules.identity.domain.entities import UserRole
from src.modules.identity.domain.exceptions import AccessDeniedError, InvalidStateError
from src.modules.identity.infrastructure.config import AuthSettings
from src.modules.identity.infrastructure.crypto_utils import CryptoUtils
from src.modules.identity.infrastructure.jwt_utils import JWTUtils

if TYPE_CHECKING:
    from src.modules.identity.application.oauth_service import OAuthService
    from src.modules.identity.application.token_service import (
        RefreshTokenRepository,
        TokenService,
    )
    from src.modules.identity.application.whitelist_service import WhitelistService
    from src.modules.identity.infrastructure.oauth_grant_repository import (
        OAuthGrantRepository,
    )
    from src.modules.identity.infrastructure.user_repository import UserRepository

# Google OAuth2 authorization endpoint.
_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"

# All OAuth scopes requested during login.
_ALL_SCOPES = (
    "openid "
    "email "
    "profile "
    "https://www.googleapis.com/auth/gmail.readonly "
    "https://www.googleapis.com/auth/gmail.modify "
    "https://www.googleapis.com/auth/gmail.send "
    "https://www.googleapis.com/auth/calendar.events"
)


@dataclass
class AuthResult:
    """Result of a successful OAuth2 callback.

    Contains the session tokens, user entity, and grant status
    returned to the caller after a successful authentication flow.

    Attributes:
        access_token: JWT access token for API authentication.
        refresh_token: Opaque refresh token for session renewal.
        user: The authenticated user entity.
        grant_status: Indicates which OAuth scopes were granted.
    """

    access_token: str
    refresh_token: str
    user: object  # User entity
    grant_status: GrantStatus


def _generate_code_verifier() -> str:
    """Generate a PKCE code verifier (43-128 URL-safe characters).

    Returns:
        A cryptographically random URL-safe string between 43 and 128
        characters in length.
    """
    # secrets.token_urlsafe(32) produces 43 characters
    return secrets.token_urlsafe(32)


def _generate_code_challenge(code_verifier: str) -> str:
    """Generate a PKCE code challenge from a code verifier.

    Computes the SHA-256 hash of the verifier and encodes it as
    base64url without padding, per RFC 7636.

    Args:
        code_verifier: The PKCE code verifier string.

    Returns:
        The base64url-encoded SHA-256 hash of the verifier.
    """
    import base64

    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


class AuthService:
    """Orchestrates the complete authentication flow.

    Coordinates between OAuth, token, whitelist, and repository services
    to implement login initiation, callback handling, and logout.

    Args:
        settings: Application auth configuration.
        jwt_utils: JWT encode/decode utilities.
        crypto: AES-256-GCM encryption utilities.
        whitelist_service: Email whitelist access control.
        oauth_service: Google OAuth2 token operations.
        token_service: JWT session token management.
        user_repository: User entity persistence.
        oauth_grant_repository: OAuth grant persistence.
        refresh_token_repository: Refresh token persistence.
    """

    def __init__(
        self,
        settings: AuthSettings,
        jwt_utils: JWTUtils,
        crypto: CryptoUtils,
        whitelist_service: WhitelistService,
        oauth_service: OAuthService,
        token_service: TokenService,
        user_repository: UserRepository,
        oauth_grant_repository: OAuthGrantRepository,
        refresh_token_repository: RefreshTokenRepository,
    ) -> None:
        """Initialize AuthService with all required dependencies.

        Args:
            settings: Application auth configuration containing Google
                client credentials and token settings.
            jwt_utils: Utility for JWT and state token operations.
            crypto: Encryption utilities for securing stored tokens.
            whitelist_service: Service for email whitelist checks.
            oauth_service: Service for Google OAuth2 token exchange.
            token_service: Service for JWT access/refresh token management.
            user_repository: Repository for user CRUD operations.
            oauth_grant_repository: Repository for OAuth grant persistence.
            refresh_token_repository: Repository for refresh token persistence.
        """
        self._settings = settings
        self._jwt_utils = jwt_utils
        self._crypto = crypto
        self._whitelist_service = whitelist_service
        self._oauth_service = oauth_service
        self._token_service = token_service
        self._user_repository = user_repository
        self._oauth_grant_repository = oauth_grant_repository
        self._refresh_token_repository = refresh_token_repository

    async def initiate_login(self) -> LoginRedirect:
        """Generate an OAuth2 redirect URL with PKCE and CSRF state.

        Creates a PKCE code verifier and challenge, generates a signed
        CSRF state token, and builds the full Google OAuth2 authorization
        URL with all required parameters.

        Returns:
            A LoginRedirect containing the redirect URL, state token,
            and code verifier for later use in the callback.
        """
        # Generate PKCE code verifier and challenge.
        code_verifier = _generate_code_verifier()
        code_challenge = _generate_code_challenge(code_verifier)

        # Create signed CSRF state token with a nonce.
        nonce = secrets.token_urlsafe(16)
        state_token = self._jwt_utils.create_state_token({"nonce": nonce})

        # Build Google OAuth2 authorization URL.
        params = {
            "client_id": self._settings.google_client_id,
            "redirect_uri": self._settings.google_redirect_uri,
            "response_type": "code",
            "scope": _ALL_SCOPES,
            "access_type": "offline",
            "prompt": "consent",
            "state": state_token,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        redirect_url = f"{_GOOGLE_AUTH_URL}?{urlencode(params)}"

        return LoginRedirect(
            redirect_url=redirect_url,
            state_token=state_token,
            code_verifier=code_verifier,
        )

    async def handle_callback(self, code: str, state: str, code_verifier: str) -> AuthResult:
        """Process the OAuth2 callback after user consent.

        Validates the CSRF state token, exchanges the authorization code
        for Google tokens, checks the user's email against the whitelist,
        upserts the user, stores encrypted OAuth tokens, revokes old
        refresh tokens, and issues new session tokens.

        Args:
            code: The authorization code from Google's OAuth2 callback.
            state: The CSRF state token to validate.
            code_verifier: The PKCE code verifier stored during login initiation.

        Returns:
            An AuthResult containing session tokens, user entity, and
            grant status.

        Raises:
            InvalidStateError: If the state token is invalid or expired.
            GoogleAuthError: If the token exchange with Google fails.
            AccessDeniedError: If the user's email is not whitelisted.
        """
        # 1. Validate CSRF state token.
        self._jwt_utils.verify_state_token(state)

        # 2. Exchange authorization code for Google tokens.
        google_tokens = await self._oauth_service.exchange_code(code, code_verifier)

        # 3. Decode Google ID token to get user info.
        # We decode without verification since we just received it from Google.
        id_token_claims = jose_jwt.get_unverified_claims(google_tokens.id_token)
        user_info = GoogleUserInfo(
            sub=id_token_claims["sub"],
            email=id_token_claims["email"],
            name=id_token_claims.get("name", id_token_claims["email"]),
            picture=id_token_claims.get("picture"),
        )

        # 4. Check whitelist.
        if not self._whitelist_service.is_allowed(user_info.email):
            raise AccessDeniedError()

        # 5. Upsert user. Assign admin role if email matches super admin.
        role = None
        super_admin_email = self._settings.super_admin_email
        if super_admin_email and user_info.email.lower() == super_admin_email.lower():
            role = UserRole.ADMIN
        user = await self._user_repository.upsert(user_info, role=role)

        # 6. Encrypt and store Google tokens.
        encrypted_access = self._crypto.encrypt(google_tokens.access_token)
        encrypted_refresh = self._crypto.encrypt(
            google_tokens.refresh_token or ""
        )
        scopes = google_tokens.scope.split(" ")
        token_expires_at = datetime.now(UTC) + timedelta(
            seconds=google_tokens.expires_in
        )

        await self._oauth_grant_repository.upsert(
            user_id=user.id,
            access_token_enc=encrypted_access,
            refresh_token_enc=encrypted_refresh,
            scopes=scopes,
            token_expires_at=token_expires_at,
        )

        # 7. Determine grant status.
        grant_status = self._oauth_service.determine_grant_status(scopes)

        # 8. Revoke old refresh tokens (single active session).
        await self._token_service.revoke_user_tokens(user.id)

        # 9. Create new access token and refresh token.
        access_token = self._token_service.create_access_token(user.id, user.email)
        raw_refresh_token, token_hash = self._token_service.create_refresh_token(
            user.id
        )

        # 10. Store refresh token hash in repository.
        expires_at = datetime.now(UTC) + timedelta(
            days=self._settings.refresh_token_expire_days
        )
        await self._refresh_token_repository.store(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        return AuthResult(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            user=user,
            grant_status=grant_status,
        )

    async def logout(self, refresh_token: str) -> None:
        """Revoke a refresh token to end the user's session.

        Hashes the provided raw refresh token and marks it as revoked
        in the database.

        Args:
            refresh_token: The raw refresh token string from the client.
        """
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        record = await self._refresh_token_repository.find_by_token_hash(token_hash)
        if record is not None:
            await self._refresh_token_repository.revoke(token_hash)
