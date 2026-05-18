"""JWT token utilities for the Identity & Auth module.

Provides JWT encoding, decoding, and CSRF state token operations
using python-jose with HMAC-SHA signing algorithms.
"""

from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from src.modules.identity.domain.exceptions import InvalidStateError, InvalidTokenError


class JWTUtils:
    """JWT token operations using python-jose.

    Handles encoding and decoding of JWT access tokens and CSRF state
    tokens with configurable secret key and algorithm.

    Args:
        secret_key: The secret key used for signing tokens.
        algorithm: The signing algorithm (default: HS256).
    """

    def __init__(self, secret_key: str, algorithm: str = "HS256") -> None:
        """Initialize JWTUtils with signing credentials.

        Args:
            secret_key: The secret key used for signing tokens.
            algorithm: The JWT signing algorithm (HS256, HS384, or HS512).
        """
        self._secret_key = secret_key
        self._algorithm = algorithm

    def encode(self, payload: dict, expires_delta: timedelta) -> str:
        """Encode a payload into a signed JWT.

        Adds standard time claims (exp, iat) to the provided payload
        and signs the token using the configured algorithm.

        Args:
            payload: The claims to include in the token.
            expires_delta: Duration until the token expires.

        Returns:
            The encoded JWT string.
        """
        now = datetime.now(UTC)
        to_encode = payload.copy()
        to_encode["exp"] = now + expires_delta
        to_encode["iat"] = now
        return jwt.encode(to_encode, self._secret_key, algorithm=self._algorithm)

    def decode(self, token: str) -> dict:
        """Decode and validate a JWT token.

        Verifies the token signature and checks that the token has not
        expired. Returns the decoded payload on success.

        Args:
            token: The JWT string to decode.

        Returns:
            The decoded token payload as a dictionary.

        Raises:
            InvalidTokenError: If the token is expired, has an invalid
                signature, or is otherwise malformed.
        """
        try:
            return jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
        except JWTError as e:
            raise InvalidTokenError() from e

    def create_state_token(self, data: dict) -> str:
        """Create a signed CSRF state token with a 10-minute expiry.

        State tokens include a ``purpose`` claim set to ``"state"`` to
        distinguish them from access tokens.

        Args:
            data: The payload data to embed in the state token.

        Returns:
            The encoded state token string.
        """
        now = datetime.now(UTC)
        to_encode = data.copy()
        to_encode["purpose"] = "state"
        to_encode["exp"] = now + timedelta(minutes=10)
        to_encode["iat"] = now
        return jwt.encode(to_encode, self._secret_key, algorithm=self._algorithm)

    def verify_state_token(self, token: str) -> dict:
        """Verify a CSRF state token.

        Decodes the token, validates the signature and expiry, and
        confirms the ``purpose`` claim is ``"state"``.

        Args:
            token: The state token string to verify.

        Returns:
            The decoded state token payload (excluding internal claims).

        Raises:
            InvalidStateError: If the token is expired, has an invalid
                signature, is malformed, or has an incorrect purpose claim.
        """
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
        except JWTError as e:
            raise InvalidStateError() from e

        if payload.get("purpose") != "state":
            raise InvalidStateError("Token is not a valid state token")

        return payload
