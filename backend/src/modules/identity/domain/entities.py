"""Domain entities for the Identity & Auth module.

Defines the SQLModel table classes for User, OAuthGrant, and RefreshToken
that map to PostgreSQL tables used for authentication and authorization.
"""

from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlmodel import Field, SQLModel


class UserRole(str, Enum):
    """Enumeration of user roles for access control."""

    ADMIN = "admin"
    USER = "user"


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
    role: UserRole = Field(
        default=UserRole.USER,
        sa_column=Column(String(10), nullable=False, default="user", index=True),
    )


class WhitelistEntryType(str, Enum):
    """Enumeration of whitelist entry types."""

    EXACT_EMAIL = "exact_email"
    DOMAIN_PATTERN = "domain_pattern"


class WhitelistEntry(SQLModel, table=True):
    """Represents a whitelist entry for login access control.

    Entries can be either exact email addresses or domain patterns
    (e.g., @example.com) that allow all emails from that domain.
    """

    __tablename__ = "whitelist_entries"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    value: str = Field(max_length=255, unique=True, nullable=False, index=True)
    entry_type: WhitelistEntryType = Field(
        sa_column=Column(String(20), nullable=False),
    )
    added_by_user_id: UUID = Field(foreign_key="users.id", nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


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
    scopes: list[str] = Field(sa_column=Column(ARRAY(String), nullable=False))
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


class OAuthConfig(SQLModel, table=True):
    """Stores OAuth provider credentials for admin-managed configuration.

    The client_secret is encrypted with AES-256-GCM before storage using
    the existing CryptoUtils. Only one active configuration per provider
    is allowed (enforced by unique constraint on provider + is_active).
    Falls back to environment variables when no active DB config exists.
    """

    __tablename__ = "oauth_configs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    provider: str = Field(default="google", max_length=50, nullable=False)
    client_id: str = Field(max_length=255, nullable=False)
    client_secret_enc: str = Field(nullable=False)
    redirect_uri: str = Field(max_length=500, nullable=False)
    is_active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_by_user_id: UUID = Field(foreign_key="users.id", nullable=False)


class AuditActionType(str, Enum):
    """Enumeration of admin audit action types."""

    WHITELIST_ADD = "whitelist_add"
    WHITELIST_REMOVE = "whitelist_remove"
    OAUTH_UPDATE = "oauth_update"
    ROLE_CHANGE = "role_change"


class AuditLog(SQLModel, table=True):
    """Records admin actions for audit trail purposes.

    Each entry captures who performed the action, what type of action
    it was, and action-specific details stored as JSON. Secret values
    are never stored in the details field.
    """

    __tablename__ = "audit_logs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    admin_user_id: UUID = Field(foreign_key="users.id", nullable=False, index=True)
    admin_email: str = Field(max_length=255, nullable=False)
    action_type: AuditActionType = Field(
        sa_column=Column(String(50), nullable=False),
    )
    details: dict = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
