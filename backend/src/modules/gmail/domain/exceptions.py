"""Domain exceptions for the Gmail Integration module.

This module defines the exception hierarchy used throughout the Gmail
module to represent business rule violations, API errors, and
connection state issues.
"""


class GmailError(Exception):
    """Base exception for the Gmail module.

    All domain-specific exceptions inherit from this class, enabling
    a single exception handler to catch any Gmail-related error and
    return a consistent JSON error response.

    Attributes:
        status_code: HTTP status code to return to the client.
        error_code: Machine-readable error identifier.
        message: Human-readable error description.
    """

    status_code: int = 500
    error_code: str = "GMAIL_ERROR"
    message: str = "A Gmail module error occurred"

    def __init__(self, message: str | None = None) -> None:
        """Initialize GmailError.

        Args:
            message: Optional custom message override. If not provided,
                the class-level default message is used.
        """
        if message is not None:
            self.message = message
        super().__init__(self.message)


class UnauthorizedException(GmailError):
    """Missing or invalid authentication session.

    Raised when a request lacks valid authentication credentials
    or the session has expired.
    """

    status_code = 401
    error_code = "UNAUTHORIZED"
    message = "Missing or invalid authentication session"


class GmailNotConnectedException(GmailError):
    """Gmail is not connected when an operation requires it.

    Raised when an API operation (fetch body, send, sync, label modify)
    is attempted but the user's Gmail connection status is not "connected".
    """

    status_code = 403
    error_code = "GMAIL_NOT_CONNECTED"
    message = "Gmail is not connected"


class GmailConnectFailedException(GmailError):
    """Gmail OAuth2 connection attempt failed.

    Raised when the OAuth2 callback fails, the user denies Gmail scopes,
    or only a subset of required scopes is granted.
    """

    status_code = 400
    error_code = "GMAIL_CONNECT_FAILED"
    message = "Gmail connection failed"


class LabelNamespaceViolationException(GmailError):
    """Attempted to modify a label outside the VroomHR/ namespace.

    Raised when a label removal or modification request targets a label
    that does not start with the "VroomHR/" prefix.
    """

    status_code = 400
    error_code = "LABEL_NAMESPACE_VIOLATION"
    message = "Label must be within the VroomHR/ namespace"


class GmailFetchError(GmailError):
    """Gmail API call failed when fetching message data.

    Raised when the Gmail API returns an error during message body
    fetch or other read operations after all retries are exhausted.
    """

    status_code = 502
    error_code = "GMAIL_FETCH_ERROR"
    message = "Failed to fetch data from Gmail API"


class MessageNotFoundException(GmailError):
    """Gmail message ID does not exist.

    Raised when a requested Gmail message cannot be found, either
    because the ID is invalid or the message has been deleted.
    """

    status_code = 404
    error_code = "MESSAGE_NOT_FOUND"
    message = "Gmail message not found"


class GmailLabelRemoveFailedException(GmailError):
    """Label removal failed after all retries.

    Raised when a label removal operation on the Gmail API fails
    after exhausting all retry attempts.
    """

    status_code = 502
    error_code = "GMAIL_LABEL_REMOVE_FAILED"
    message = "Failed to remove label from Gmail message"


class GmailSendFailedException(GmailError):
    """Email send via Gmail API failed.

    Raised when the Gmail API messages.send call fails after all
    retry attempts (for 5xx errors) or immediately (for non-retryable 4xx).
    """

    status_code = 502
    error_code = "GMAIL_SEND_FAILED"
    message = "Failed to send email via Gmail"


class RateLimitedException(GmailError):
    """Manual sync rate limit exceeded.

    Raised when a user attempts a manual sync within the cooldown
    period (default 30 seconds) of their previous manual sync.
    """

    status_code = 429
    error_code = "RATE_LIMITED"
    message = "Rate limit exceeded, please try again later"

    def __init__(self, message: str | None = None, retry_after: int = 0) -> None:
        """Initialize RateLimitedException.

        Args:
            message: Optional custom message override.
            retry_after: Seconds remaining until the next request is allowed.
        """
        self.retry_after = retry_after
        if message is None and retry_after > 0:
            message = f"Rate limit exceeded, retry after {retry_after} seconds"
        super().__init__(message)
