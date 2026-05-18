"""Tests for domain exceptions in the Identity & Auth module."""

from src.modules.identity.domain.exceptions import (
    AccessDeniedError,
    AuthError,
    GoogleAuthError,
    InsufficientScopeError,
    InvalidStateError,
    InvalidTokenError,
    RateLimitExceededError,
)


class TestAuthErrorBase:
    """Tests for the base AuthError exception."""

    def test_default_message(self) -> None:
        err = AuthError()
        assert str(err) == "An authentication error occurred"
        assert err.message == "An authentication error occurred"

    def test_custom_message_override(self) -> None:
        err = AuthError("Custom error message")
        assert str(err) == "Custom error message"
        assert err.message == "Custom error message"

    def test_default_attributes(self) -> None:
        err = AuthError()
        assert err.status_code == 500
        assert err.error_code == "AUTH_ERROR"

    def test_is_exception(self) -> None:
        assert issubclass(AuthError, Exception)


class TestInvalidStateError:
    """Tests for InvalidStateError."""

    def test_attributes(self) -> None:
        err = InvalidStateError()
        assert err.status_code == 400
        assert err.error_code == "AUTH_INVALID_STATE"
        assert err.message == "Invalid authentication state"

    def test_inherits_auth_error(self) -> None:
        assert issubclass(InvalidStateError, AuthError)

    def test_custom_message(self) -> None:
        err = InvalidStateError("State expired")
        assert err.message == "State expired"
        assert str(err) == "State expired"


class TestGoogleAuthError:
    """Tests for GoogleAuthError."""

    def test_attributes(self) -> None:
        err = GoogleAuthError()
        assert err.status_code == 502
        assert err.error_code == "AUTH_GOOGLE_ERROR"
        assert err.message == "Failed to authenticate with Google"

    def test_inherits_auth_error(self) -> None:
        assert issubclass(GoogleAuthError, AuthError)


class TestAccessDeniedError:
    """Tests for AccessDeniedError."""

    def test_attributes(self) -> None:
        err = AccessDeniedError()
        assert err.status_code == 403
        assert err.error_code == "AUTH_ACCESS_DENIED"
        assert err.message == "Access denied. Contact administrator."

    def test_inherits_auth_error(self) -> None:
        assert issubclass(AccessDeniedError, AuthError)


class TestInsufficientScopeError:
    """Tests for InsufficientScopeError."""

    def test_attributes(self) -> None:
        err = InsufficientScopeError()
        assert err.status_code == 400
        assert err.error_code == "AUTH_INSUFFICIENT_SCOPE"
        assert err.message == "Please grant all requested permissions"

    def test_inherits_auth_error(self) -> None:
        assert issubclass(InsufficientScopeError, AuthError)


class TestInvalidTokenError:
    """Tests for InvalidTokenError."""

    def test_attributes(self) -> None:
        err = InvalidTokenError()
        assert err.status_code == 401
        assert err.error_code == "AUTH_INVALID_TOKEN"
        assert err.message == "Invalid or expired token"

    def test_inherits_auth_error(self) -> None:
        assert issubclass(InvalidTokenError, AuthError)


class TestRateLimitExceededError:
    """Tests for RateLimitExceededError."""

    def test_attributes(self) -> None:
        err = RateLimitExceededError()
        assert err.status_code == 429
        assert err.error_code == "AUTH_RATE_LIMITED"
        assert err.message == "Too many login attempts. Please try again later."

    def test_inherits_auth_error(self) -> None:
        assert issubclass(RateLimitExceededError, AuthError)


class TestExceptionCatching:
    """Tests that all exceptions can be caught by the base class."""

    def test_catch_all_with_auth_error(self) -> None:
        exceptions = [
            InvalidStateError(),
            GoogleAuthError(),
            AccessDeniedError(),
            InsufficientScopeError(),
            InvalidTokenError(),
            RateLimitExceededError(),
        ]
        for exc in exceptions:
            try:
                raise exc
            except AuthError as caught:
                assert caught.status_code > 0
                assert caught.error_code.startswith("AUTH_")
                assert len(caught.message) > 0
