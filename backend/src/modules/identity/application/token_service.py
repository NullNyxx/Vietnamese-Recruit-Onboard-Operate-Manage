"""Token service for JWT access and refresh token management.

Handles creation, verification, refresh, and revocation of JWT access
tokens and opaque refresh tokens for the Identity & Auth module.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

from src.modules.identity.api.schemas import TokenPayload
from src.modules.identity.domain.exceptions import InvalidTokenError
from src.modules.identity.infrastructure.config import AuthSettings
from src.modules.identity.infrastructure.jwt_utils import JWTUtils


class RefreshTokenRepository(Protocol):
    """Protocol defining the interface for refresh token persistence.

    Implementations handle storage and retrieval of hashed refresh
    tokens in the database.
    """

    async def find_by_token_hash(self, token_hash: str) -> "RefreshTokenRecord | None":
        """Look up a refresh token record by its SHA-256 hash.

        Args:
            token_hash: The SHA-256 hex digest of the raw token.

        Returns:
            The refresh token record if found, None otherwise.
        """
        ...

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        """Revoke all active refresh tokens for a user.

        Sets revoked_at on all non-revoked tokens belonging to the user.

        Args:
            user_id: The UUID of the user whose tokens to revoke.
        """
        ...

    async def store(self, user_id: UUID, token_hash: str, expires_at: datetime) -> None:
        """Store a new refresh token hash in the database.

        Args:
            user_id: The UUID of the user who owns the token.
            token_hash: The SHA-256 hex digest of the raw token.
            expires_at: When the token expires.
        """
        ...

    async def revoke(self, token_hash: str) -> None:
        """Revoke a single refresh token by its hash.

        Sets revoked_at to the current time on the token record.

        Args:
            token_hash: The SHA-256 hex digest of the token to revoke.
        """
        ...


class RefreshTokenRecord(Protocol):
    """Protocol representing a stored refresh token record.

    Attributes:
        user_id: The UUID of the user who owns this token.
        token_hash: The SHA-256 hex digest of the raw token.
        expires_at: When the token expires.
        revoked_at: When the token was revoked, or None if active.
    """

    @property
    def user_id(self) -> UUID: ...

    @property
    def token_hash(self) -> str: ...

    @property
    def expires_at(self) -> datetime: ...

    @property
    def revoked_at(self) -> datetime | None: ...

    @property
    def email(self) -> str: ...


class TokenService:
    """Manages JWT access tokens and opaque refresh tokens.

    Coordinates between JWTUtils for JWT operations and the
    RefreshTokenRepository for refresh token persistence.

    Args:
        jwt_utils: Utility for JWT encode/decode operations.
        settings: Auth configuration with token expiry settings.
        refresh_token_repository: Repository for refresh token CRUD.
    """

    def __init__(
        self,
        jwt_utils: JWTUtils,
        settings: AuthSettings,
        refresh_token_repository: RefreshTokenRepository,
    ) -> None:
        """Initialize TokenService with its dependencies.

        Args:
            jwt_utils: JWTUtils instance for JWT operations.
            settings: AuthSettings with token expiry configuration.
            refresh_token_repository: Repository for refresh token storage.
        """
        self._jwt_utils = jwt_utils
        self._settings = settings
        self._refresh_token_repo = refresh_token_repository

    def create_access_token(
        self, user_id: UUID, email: str, employee_id: UUID | None = None
    ) -> str:
        """Issue a JWT access token with user claims.

        Creates a signed JWT containing the user's ID, email, and
        optionally the linked employee_id with a 15-minute expiry
        (configurable via settings).

        Args:
            user_id: The unique identifier of the authenticated user.
            email: The user's email address.
            employee_id: The linked employee's UUID, if a
                User_Employee_Link exists. Included in claims when provided.

        Returns:
            The encoded JWT access token string.
        """
        payload = {
            "sub": str(user_id),
            "email": email,
        }
        if employee_id:
            payload["employee_id"] = str(employee_id)
        expires_delta = timedelta(minutes=self._settings.access_token_expire_minutes)
        return self._jwt_utils.encode(payload, expires_delta)

    def create_refresh_token(self, user_id: UUID) -> tuple[str, str]:
        """Generate a secure opaque refresh token.

        Creates a cryptographically random token and computes its
        SHA-256 hash for secure storage. Only the hash is persisted;
        the raw token is returned to the client.

        Args:
            user_id: The unique identifier of the user (for context).

        Returns:
            A tuple of (raw_token, token_hash) where raw_token is the
            value sent to the client and token_hash is the SHA-256 hex
            digest stored in the database.
        """
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        return raw_token, token_hash

    def verify_access_token(self, token: str) -> TokenPayload:
        """Decode and validate a JWT access token.

        Verifies the token signature and expiry, then converts the
        decoded claims into a structured TokenPayload.

        Args:
            token: The JWT access token string to verify.

        Returns:
            A TokenPayload containing the decoded claims.

        Raises:
            InvalidTokenError: If the token is expired, has an invalid
                signature, or is otherwise malformed.
        """
        decoded = self._jwt_utils.decode(token)
        try:
            employee_id_raw = decoded.get("employee_id")
            employee_id = UUID(employee_id_raw) if employee_id_raw else None
            return TokenPayload(
                sub=decoded["sub"],
                email=decoded["email"],
                employee_id=employee_id,
                exp=decoded["exp"],
                iat=decoded["iat"],
            )
        except (KeyError, ValueError) as e:
            raise InvalidTokenError() from e

    async def refresh_access_token(self, refresh_token: str) -> str:
        """Validate a refresh token and issue a new access token.

        Hashes the provided raw refresh token, looks it up in the
        database, validates it is not expired or revoked, and issues
        a fresh access token for the associated user.

        Args:
            refresh_token: The raw refresh token string from the client.

        Returns:
            A new JWT access token string.

        Raises:
            InvalidTokenError: If the refresh token is not found,
                expired, or has been revoked.
        """
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        record = await self._refresh_token_repo.find_by_token_hash(token_hash)

        if record is None:
            raise InvalidTokenError()

        if record.revoked_at is not None:
            raise InvalidTokenError()

        if record.expires_at <= datetime.now(UTC):
            raise InvalidTokenError()

        return self.create_access_token(record.user_id, record.email)

    async def revoke_user_tokens(self, user_id: UUID) -> None:
        """Revoke all active refresh tokens for a user.

        Sets revoked_at on all non-revoked refresh tokens belonging
        to the specified user, effectively terminating all sessions.

        Args:
            user_id: The UUID of the user whose tokens to revoke.
        """
        await self._refresh_token_repo.revoke_all_for_user(user_id)
