"""OAuth configuration management service.

Manages OAuth provider credentials stored encrypted in the database,
with fallback to environment variables and validation against the
Google OAuth discovery endpoint before persisting new credentials.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse
from uuid import uuid4

import httpx

from src.modules.identity.domain.entities import OAuthConfig, User
from src.modules.identity.infrastructure.crypto_utils import CryptoUtils
from src.modules.identity.infrastructure.oauth_config_repository import OAuthConfigRepository

logger = logging.getLogger(__name__)

GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"


@dataclass
class OAuthConfigResponse:
    """Response DTO for OAuth configuration with masked secret.

    Attributes:
        client_id: The OAuth client ID.
        client_secret_masked: The client secret with only last 4 chars visible.
        redirect_uri: The OAuth redirect URI.
        updated_at: When the config was last updated.
        updated_by_email: Email of the admin who last updated the config.
        source: Whether the config comes from "database" or "environment".
    """

    client_id: str
    client_secret_masked: str
    redirect_uri: str
    updated_at: datetime | None
    updated_by_email: str | None
    source: str  # "database" or "environment"


@dataclass
class EffectiveCredentials:
    """The effective OAuth credentials for use by the auth system.

    Attributes:
        client_id: The OAuth client ID.
        client_secret: The decrypted OAuth client secret.
        redirect_uri: The OAuth redirect URI.
    """

    client_id: str
    client_secret: str
    redirect_uri: str


class OAuthConfigValidationError(Exception):
    """Raised when OAuth credential validation fails."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class OAuthConfigManager:
    """Manages OAuth provider credentials with encryption and validation.

    Provides methods to retrieve, update, and validate OAuth configuration.
    Credentials are encrypted at rest using AES-256-GCM via CryptoUtils.
    Falls back to environment variables when no database configuration exists.
    New credentials are validated against the Google OAuth discovery endpoint
    before being persisted, retaining previous working credentials on failure.

    Args:
        repository: The OAuthConfig repository for database operations.
        crypto: CryptoUtils instance for encrypting/decrypting secrets.
        google_client_id: Fallback Google client ID from environment.
        google_client_secret: Fallback Google client secret from environment.
        google_redirect_uri: Fallback Google redirect URI from environment.
    """

    def __init__(
        self,
        repository: OAuthConfigRepository,
        crypto: CryptoUtils,
        google_client_id: str,
        google_client_secret: str,
        google_redirect_uri: str,
    ) -> None:
        self._repository = repository
        self._crypto = crypto
        self._env_client_id = google_client_id
        self._env_client_secret = google_client_secret
        self._env_redirect_uri = google_redirect_uri

    @staticmethod
    def mask_secret(secret: str) -> str:
        """Mask a secret string, showing only the last 4 characters.

        Args:
            secret: The secret string to mask.

        Returns:
            A masked string with asterisks and the last 4 characters visible.
            If the secret is shorter than 4 characters, returns all asterisks.
        """
        if len(secret) <= 4:
            return "*" * len(secret)
        return "*" * (len(secret) - 4) + secret[-4:]

    @staticmethod
    def _validate_redirect_uri(redirect_uri: str) -> bool:
        """Validate that a redirect URI is a well-formed URL.

        Args:
            redirect_uri: The URI to validate.

        Returns:
            True if the URI has a valid scheme and netloc, False otherwise.
        """
        try:
            parsed = urlparse(redirect_uri)
            return bool(parsed.scheme in ("http", "https") and parsed.netloc)
        except Exception:
            return False

    async def get_active_config(self) -> OAuthConfigResponse:
        """Retrieve the current active OAuth configuration with masked secret.

        Returns the database-stored configuration if one exists, otherwise
        returns the environment variable configuration. The client_secret
        is always masked (showing only the last 4 characters).

        Returns:
            An OAuthConfigResponse with the current configuration details.
        """
        db_config = await self._repository.get_active()

        if db_config is not None:
            decrypted_secret = self._crypto.decrypt(db_config.client_secret_enc)
            return OAuthConfigResponse(
                client_id=db_config.client_id,
                client_secret_masked=self.mask_secret(decrypted_secret),
                redirect_uri=db_config.redirect_uri,
                updated_at=db_config.updated_at,
                updated_by_email=None,  # Caller can enrich with user lookup
                source="database",
            )

        return OAuthConfigResponse(
            client_id=self._env_client_id,
            client_secret_masked=self.mask_secret(self._env_client_secret),
            redirect_uri=self._env_redirect_uri,
            updated_at=None,
            updated_by_email=None,
            source="environment",
        )

    async def update_config(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        admin: User,
    ) -> OAuthConfigResponse:
        """Update OAuth credentials after validation.

        Validates that client_id is non-empty, redirect_uri is a valid URL,
        and the credentials pass Google OAuth discovery endpoint validation.
        If validation succeeds, encrypts the secret and persists the config.
        Previous credentials are retained until new ones are validated.

        Args:
            client_id: The new OAuth client ID.
            client_secret: The new OAuth client secret (plaintext).
            redirect_uri: The new OAuth redirect URI.
            admin: The admin user performing the update.

        Returns:
            An OAuthConfigResponse with the updated configuration.

        Raises:
            OAuthConfigValidationError: If validation fails (empty client_id,
                invalid redirect_uri, or Google discovery validation failure).
        """
        # Validate client_id is non-empty
        if not client_id or not client_id.strip():
            raise OAuthConfigValidationError("client_id must not be empty")

        # Validate redirect_uri is a valid URL
        if not self._validate_redirect_uri(redirect_uri):
            raise OAuthConfigValidationError("redirect_uri must be a valid URL")

        # Validate against Google OAuth discovery endpoint
        is_valid = await self.validate_credentials(client_id)
        if not is_valid:
            raise OAuthConfigValidationError(
                "Could not verify credentials with Google"
            )

        # Encrypt the client secret
        encrypted_secret = self._crypto.encrypt(client_secret)

        # Check if there's an existing active config to update
        existing = await self._repository.get_active()

        if existing is not None:
            existing.client_id = client_id
            existing.client_secret_enc = encrypted_secret
            existing.redirect_uri = redirect_uri
            existing.updated_by_user_id = admin.id
            existing.updated_at = datetime.now(UTC)
            saved = await self._repository.upsert(existing)
        else:
            new_config = OAuthConfig(
                id=uuid4(),
                provider="google",
                client_id=client_id,
                client_secret_enc=encrypted_secret,
                redirect_uri=redirect_uri,
                is_active=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                updated_by_user_id=admin.id,
            )
            saved = await self._repository.upsert(new_config)

        return OAuthConfigResponse(
            client_id=saved.client_id,
            client_secret_masked=self.mask_secret(client_secret),
            redirect_uri=saved.redirect_uri,
            updated_at=saved.updated_at,
            updated_by_email=admin.email,
            source="database",
        )

    async def validate_credentials(self, client_id: str) -> bool:
        """Validate OAuth client_id against Google's discovery endpoint.

        Makes a request to the Google OpenID Connect discovery endpoint
        to verify that the endpoint is reachable and the configuration
        is valid. This serves as a basic connectivity and sanity check.

        Args:
            client_id: The OAuth client ID to validate.

        Returns:
            True if the discovery endpoint is reachable and returns valid
            configuration, False otherwise.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(GOOGLE_DISCOVERY_URL)
                if response.status_code != 200:
                    logger.warning(
                        "Google discovery endpoint returned status %d",
                        response.status_code,
                    )
                    return False

                discovery = response.json()
                # Verify the discovery document has expected fields
                if "authorization_endpoint" not in discovery:
                    logger.warning("Google discovery document missing authorization_endpoint")
                    return False
                if "token_endpoint" not in discovery:
                    logger.warning("Google discovery document missing token_endpoint")
                    return False

                return True

        except httpx.TimeoutException:
            logger.warning("Timeout connecting to Google discovery endpoint")
            return False
        except httpx.RequestError as exc:
            logger.warning("Error connecting to Google discovery endpoint: %s", exc)
            return False
        except Exception as exc:
            logger.warning("Unexpected error validating OAuth credentials: %s", exc)
            return False

    async def get_effective_credentials(self) -> EffectiveCredentials:
        """Get the effective OAuth credentials for use by the auth system.

        Returns the database-stored credentials if an active configuration
        exists, otherwise falls back to environment variable values.

        Returns:
            An EffectiveCredentials instance with the active client_id,
            decrypted client_secret, and redirect_uri.
        """
        db_config = await self._repository.get_active()

        if db_config is not None:
            decrypted_secret = self._crypto.decrypt(db_config.client_secret_enc)
            return EffectiveCredentials(
                client_id=db_config.client_id,
                client_secret=decrypted_secret,
                redirect_uri=db_config.redirect_uri,
            )

        return EffectiveCredentials(
            client_id=self._env_client_id,
            client_secret=self._env_client_secret,
            redirect_uri=self._env_redirect_uri,
        )
