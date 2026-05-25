"""Pydantic request/response schemas for the Identity & Auth API.

Defines data transfer objects used by the auth router endpoints and
internal services for structured data validation and serialization.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.modules.identity.domain.entities import UserRole, WhitelistEntryType


class TokenPayload(BaseModel):
    """JWT access token payload.

    Represents the decoded claims from a JWT access token issued
    by the TokenService.

    Attributes:
        sub: The user's unique identifier (user_id).
        email: The user's email address.
        employee_id: The linked employee's UUID, if a User_Employee_Link exists.
        exp: Token expiration timestamp.
        iat: Token issued-at timestamp.
    """

    sub: UUID
    email: str
    employee_id: UUID | None = None
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
        employee_id: Linked employee record ID if one exists.
        role: The user's role (admin or user).
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
    employee_id: UUID | None = None
    role: UserRole
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


# --- Admin Whitelist Schemas ---


class WhitelistAddRequest(BaseModel):
    """Request schema for adding a whitelist entry.

    The value can be either a full email address (e.g., user@example.com)
    or a domain pattern (e.g., @example.com). The entry type is auto-detected
    from the value format.

    Attributes:
        value: The email address or domain pattern to whitelist.
    """

    value: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Email address or domain pattern (@domain.com) to whitelist",
    )


class WhitelistEntrySchema(BaseModel):
    """Response schema for a single whitelist entry.

    Represents a merged view of whitelist entries from both database
    and file sources. File-based entries are marked as read-only.

    Attributes:
        id: Unique identifier (None for file-based entries).
        value: The email or domain pattern value.
        entry_type: Whether this is an exact email or domain pattern.
        added_by_email: Email of the admin who added the entry.
        created_at: When the entry was created (None for file-based).
        source: Origin of the entry ('database' or 'file').
        is_readonly: Whether the entry can be modified via the API.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID | None
    value: str
    entry_type: WhitelistEntryType
    added_by_email: str
    created_at: datetime | None
    source: Literal["database", "file"]
    is_readonly: bool


class WhitelistEntryCreatedResponse(BaseModel):
    """Response schema for a newly created whitelist entry.

    Returned after successfully adding a new whitelist entry.

    Attributes:
        id: The unique identifier of the new entry.
        value: The email or domain pattern value.
        entry_type: The detected entry type.
        created_at: When the entry was created.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    value: str
    entry_type: WhitelistEntryType
    created_at: datetime


class WhitelistListResponse(BaseModel):
    """Response schema for listing all whitelist entries.

    Attributes:
        items: The list of all whitelist entries (merged file + DB).
        total: The total number of entries.
    """

    items: list[WhitelistEntrySchema]
    total: int


# --- Admin OAuth Config Schemas ---


class OAuthConfigUpdateRequest(BaseModel):
    """Request schema for updating OAuth credentials.

    All fields are required. The client_secret is provided in plaintext
    and will be encrypted before storage. The redirect_uri must be a
    valid HTTP or HTTPS URL.

    Attributes:
        client_id: The OAuth client ID (must be non-empty).
        client_secret: The OAuth client secret (plaintext).
        redirect_uri: The OAuth redirect URI (must be a valid URL).
    """

    client_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="OAuth client ID",
    )
    client_secret: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="OAuth client secret (plaintext)",
    )
    redirect_uri: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="OAuth redirect URI (must be a valid URL)",
    )


class OAuthConfigResponse(BaseModel):
    """Response schema for OAuth configuration with masked secret.

    The client_secret is always masked, showing only the last 4 characters.
    The source field indicates whether the config comes from the database
    or from environment variables (fallback).

    Attributes:
        client_id: The OAuth client ID.
        client_secret_masked: The masked client secret (e.g., '****abcd').
        redirect_uri: The OAuth redirect URI.
        updated_at: When the config was last updated (None for env source).
        source: Origin of the config ('database' or 'environment').
    """

    model_config = ConfigDict(from_attributes=True)

    client_id: str
    client_secret_masked: str
    redirect_uri: str
    updated_at: datetime | None
    source: str
