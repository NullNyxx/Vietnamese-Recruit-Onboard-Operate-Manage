"""Domain entities for the Identity & Auth module.

Defines the SQLModel table classes for User, OAuthGrant, and RefreshToken
that map to PostgreSQL tables used for authentication and authorization.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """Represents an authenticated HR user in the system.

    Users are auto-provisioned on first Google OAuth2 login when their
    email is present in the whitelist. Each user has a unique Google
    subject identifier and email address.
    """

    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(max_length=255, unique=True, nullable=False, index=True)
    name: str = Field(max_length=255, nullable=False)
    avatar_url: str | None = Field(default=None)
    google_sub: str = Field(max_length=255, unique=True, nullable=False, index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    last_login: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    is_active: bool = Field(default=True, nullable=False)


class OAuthGrant(SQLModel, table=True):
    """Stores encrypted Google OAuth2 tokens for a user.

    Access and refresh tokens are encrypted with AES-256-GCM before
    storage. Each user has at most one active grant. The grant tracks
    which scopes were authorized and whether the tokens are still valid.
    """

    __tablename__ = "oauth_grants"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", nullable=False, index=True)
    provider: str = Field(default="google", max_length=50, nullable=False)
    access_token_enc: str = Field(nullable=False)
    refresh_token_enc: str = Field(nullable=False)
    scopes: list[str] = Field(
        sa_column=Column(ARRAY(String), nullable=False)
    )
    token_expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    is_valid: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class RefreshToken(SQLModel, table=True):
    """Represents a system-issued refresh token for JWT session management.

    Only the SHA-256 hash of the token is stored. Each user should have
    at most one non-revoked refresh token at any time (single active
    session invariant). Old tokens are revoked on new login.
    """

    __tablename__ = "refresh_tokens"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", nullable=False, index=True)
    token_hash: str = Field(max_length=64, unique=True, nullable=False, index=True)
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    revoked_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    user_agent: str | None = Field(default=None)
