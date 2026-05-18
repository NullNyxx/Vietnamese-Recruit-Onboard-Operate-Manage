"""Domain exceptions for the Identity & Auth module.

This module defines the exception hierarchy used throughout the identity
module to represent authentication and authorization failures.
"""


class AuthError(Exception):
    """Base exception for the identity module.

    All domain-specific exceptions inherit from this class, enabling
    a single exception handler to catch any auth-related error and
    return a consistent JSON error response.

    Attributes:
        status_code: HTTP status code to return to the client.
        error_code: Machine-readable error identifier.
        message: Human-readable error description.
    """

    status_code: int = 500
    error_code: str = "AUTH_ERROR"
    message: str = "An authentication error occurred"

    def __init__(self, message: str | None = None) -> None:
        """Initialize AuthError.

        Args:
            message: Optional custom message override. If not provided,
                the class-level default message is used.
        """
        if message is not None:
            self.message = message
        super().__init__(self.message)


class InvalidStateError(AuthError):
    """CSRF state token is invalid or expired.

    Raised when the OAuth2 callback receives a state parameter that
    cannot be verified (bad signature, expired, or missing).
    """

    status_code = 400
    error_code = "AUTH_INVALID_STATE"
    message = "Invalid authentication state"


class GoogleAuthError(AuthError):
    """Google token exchange or API call failed.

    Raised when the system cannot complete the OAuth2 token exchange
    with Google, or when a Google API call returns an error.
    """

    status_code = 502
    error_code = "AUTH_GOOGLE_ERROR"
    message = "Failed to authenticate with Google"


class AccessDeniedError(AuthError):
    """Email is not in the whitelist.

    Raised when a user authenticates successfully with Google but
    their email address is not present in the access whitelist.
    """

    status_code = 403
    error_code = "AUTH_ACCESS_DENIED"
    message = "Access denied. Contact administrator."


class InsufficientScopeError(AuthError):
    """User did not grant all required OAuth scopes.

    Raised when the user completes OAuth consent but declines one
    or more of the requested permissions (Gmail, Calendar).
    """

    status_code = 400
    error_code = "AUTH_INSUFFICIENT_SCOPE"
    message = "Please grant all requested permissions"


class InvalidTokenError(AuthError):
    """JWT access or refresh token is invalid.

    Raised when a token cannot be decoded, has an invalid signature,
    is expired, or has been revoked.
    """

    status_code = 401
    error_code = "AUTH_INVALID_TOKEN"
    message = "Invalid or expired token"


class RateLimitExceededError(AuthError):
    """Too many login attempts from a single IP.

    Raised when the per-IP rate limit (5 requests per minute) is
    exceeded on login-related endpoints.
    """

    status_code = 429
    error_code = "AUTH_RATE_LIMITED"
    message = "Too many login attempts. Please try again later."
