"""Pydantic request/response schemas for the Identity & Auth API.

Defines data transfer objects used by the auth router endpoints and
internal services for structured data validation and serialization.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TokenPayload(BaseModel):
    """JWT access token payload.

    Represents the decoded claims from a JWT access token issued
    by the TokenService.

    Attributes:
        sub: The user's unique identifier (user_id).
        email: The user's email address.
        exp: Token expiration timestamp.
        iat: Token issued-at timestamp.
    """

    sub: UUID
    email: str
    exp: datetime
    iat: datetime


class GoogleTokens(BaseModel):
    """Tokens received from Google OAuth2 token exchange.

    Contains the full set of tokens returned by Google's token
    endpoint after exchanging an authorization code.

    Attributes:
        access_token: Short-lived token for Google API calls.
        refresh_token: Long-lived token for obtaining new access tokens.
            May be None if the user has previously authorized the app.
        id_token: JWT containing user identity claims.
        expires_in: Access token lifetime in seconds.
        scope: Space-separated list of granted scopes.
    """

    access_token: str
    refresh_token: str | None = None
    id_token: str
    expires_in: int
    scope: str


class GoogleUserInfo(BaseModel):
    """User profile extracted from a Google ID token.

    Contains the essential identity fields needed for user
    provisioning and profile display.

    Attributes:
        sub: Google's unique subject identifier for the user.
        email: The user's primary email address.
        name: The user's display name.
        picture: URL to the user's profile picture, if available.
    """

    sub: str
    email: str
    name: str
    picture: str | None = None


class GrantStatus(BaseModel):
    """OAuth grant validity status.

    Indicates whether the user has granted the required Google API
    scopes for Gmail and Calendar integrations.

    Attributes:
        gmail_grant_valid: True if all Gmail scopes are granted.
        calendar_grant_valid: True if the Calendar scope is granted.
    """

    gmail_grant_valid: bool
    calendar_grant_valid: bool


class UserResponse(BaseModel):
    """Response schema for GET /api/auth/me.

    Returns the authenticated user's profile along with their
    current grant status for Gmail and Calendar.

    Attributes:
        id: The user's unique identifier.
        email: The user's email address.
        name: The user's display name.
        avatar_url: URL to the user's avatar image, if available.
        gmail_grant_valid: True if Gmail scopes are active.
        calendar_grant_valid: True if Calendar scope is active.
        created_at: When the user account was created.
        last_login: When the user last authenticated.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    name: str
    avatar_url: str | None = None
    gmail_grant_valid: bool
    calendar_grant_valid: bool
    created_at: datetime
    last_login: datetime


class GrantStatusResponse(BaseModel):
    """Response schema for GET /api/auth/grant-status.

    Returns the current validity of the user's Gmail and Calendar
    OAuth grants.

    Attributes:
        gmail_grant_valid: True if all Gmail scopes are granted.
        calendar_grant_valid: True if the Calendar scope is granted.
    """

    model_config = ConfigDict(from_attributes=True)

    gmail_grant_valid: bool
    calendar_grant_valid: bool


class LoginRedirect(BaseModel):
    """Internal model for OAuth2 redirect data.

    Used by AuthService to pass redirect information back to the
    router for constructing the HTTP 302 response.

    Attributes:
        redirect_url: The full Google OAuth2 authorization URL.
        state_token: Signed CSRF state token for callback validation.
        code_verifier: PKCE code verifier to store for token exchange.
    """

    redirect_url: str
    state_token: str
    code_verifier: str
