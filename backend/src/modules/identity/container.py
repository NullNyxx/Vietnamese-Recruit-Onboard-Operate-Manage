"""Dependency injection container for the Identity & Auth module.

Provides FastAPI dependency functions that wire together all services,
repositories, and infrastructure components using async database sessions
and Redis connections.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from functools import lru_cache

import redis.asyncio as redis
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.modules.employee.infrastructure.employee_repository import (
    EmployeeRepository as EmployeeRepo,
)
from src.modules.identity.application.audit_service import AuditService
from src.modules.identity.application.auth_service import AuthService
from src.modules.identity.application.oauth_config_manager import OAuthConfigManager
from src.modules.identity.application.oauth_service import OAuthService
from src.modules.identity.application.role_service import RoleService
from src.modules.identity.application.token_service import TokenService
from src.modules.identity.application.whitelist_manager import WhitelistManager
from src.modules.identity.application.whitelist_service import WhitelistService
from src.modules.identity.domain.entities import User
from src.modules.identity.domain.exceptions import InvalidTokenError
from src.modules.identity.infrastructure.audit_log_repository import AuditLogRepository
from src.modules.identity.infrastructure.config import AuthSettings
from src.modules.identity.infrastructure.crypto_utils import CryptoUtils
from src.modules.identity.infrastructure.jwt_utils import JWTUtils
from src.modules.identity.infrastructure.oauth_config_repository import OAuthConfigRepository
from src.modules.identity.infrastructure.oauth_grant_repository import OAuthGrantRepository
from src.modules.identity.infrastructure.rate_limiter import RateLimiter
from src.modules.identity.infrastructure.refresh_token_repository import RefreshTokenRepository
from src.modules.identity.infrastructure.user_repository import UserRepository
from src.modules.identity.infrastructure.whitelist_loader import WhitelistLoader
from src.modules.identity.infrastructure.whitelist_repository import WhitelistRepository

logger = logging.getLogger(__name__)


@lru_cache
def get_settings() -> AuthSettings:
    """Load and cache AuthSettings from environment variables.

    Returns:
        The AuthSettings singleton loaded from AUTH_* env vars.
    """
    return AuthSettings()  # type: ignore[call-arg]


@lru_cache
def get_jwt_utils() -> JWTUtils:
    """Create and cache the JWTUtils singleton.

    Returns:
        JWTUtils configured with the JWT secret key and algorithm.
    """
    settings = get_settings()
    return JWTUtils(secret_key=settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


@lru_cache
def get_crypto_utils() -> CryptoUtils:
    """Create and cache the CryptoUtils singleton.

    Returns:
        CryptoUtils configured with the OAuth token encryption key.
    """
    settings = get_settings()
    return CryptoUtils(settings.oauth_token_encryption_key)


@lru_cache
def get_whitelist_service() -> WhitelistService:
    """Create and cache the WhitelistService singleton.

    Returns:
        WhitelistService configured with the whitelist file path.
    """
    settings = get_settings()
    return WhitelistService(settings.whitelist_file_path)


@lru_cache
def get_redis_client() -> redis.Redis:
    """Create and cache the async Redis client singleton.

    Returns:
        An async Redis client connected to the configured Redis URL.
    """
    settings = get_settings()
    return redis.from_url(settings.redis_url, decode_responses=True)


@lru_cache
def get_rate_limiter() -> RateLimiter:
    """Create and cache the RateLimiter singleton.

    Returns:
        RateLimiter configured with Redis client and rate limit settings.
    """
    settings = get_settings()
    redis_client = get_redis_client()
    return RateLimiter(redis_client=redis_client, settings=settings)


@lru_cache
def _get_async_session_maker() -> async_sessionmaker[AsyncSession]:
    """Create and cache the async session factory.

    Returns:
        An async_sessionmaker bound to the configured database engine.
    """
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional async database session.

    Yields an AsyncSession that commits on success or rolls back on
    exception. Used as a FastAPI dependency.

    Yields:
        An AsyncSession for database operations.
    """
    session_maker = _get_async_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_user_repository(
    session: AsyncSession = Depends(get_db_session),
) -> UserRepository:
    """Provide a UserRepository instance.

    Args:
        session: The async database session from DI.

    Returns:
        A UserRepository bound to the current session.
    """
    return UserRepository(session)


async def get_oauth_grant_repository(
    session: AsyncSession = Depends(get_db_session),
) -> OAuthGrantRepository:
    """Provide an OAuthGrantRepository instance.

    Args:
        session: The async database session from DI.

    Returns:
        An OAuthGrantRepository bound to the current session.
    """
    return OAuthGrantRepository(session)


async def get_refresh_token_repository(
    session: AsyncSession = Depends(get_db_session),
) -> RefreshTokenRepository:
    """Provide a RefreshTokenRepository instance.

    Args:
        session: The async database session from DI.

    Returns:
        A RefreshTokenRepository bound to the current session.
    """
    return RefreshTokenRepository(session)


async def get_token_service(
    refresh_token_repo: RefreshTokenRepository = Depends(get_refresh_token_repository),
) -> TokenService:
    """Provide a TokenService instance.

    Args:
        refresh_token_repo: The refresh token repository from DI.

    Returns:
        A TokenService configured with JWT utils and settings.
    """
    return TokenService(
        jwt_utils=get_jwt_utils(),
        settings=get_settings(),
        refresh_token_repository=refresh_token_repo,
    )


async def get_oauth_service(
    oauth_grant_repo: OAuthGrantRepository = Depends(get_oauth_grant_repository),
) -> OAuthService:
    """Provide an OAuthService instance.

    Args:
        oauth_grant_repo: The OAuth grant repository from DI.

    Returns:
        An OAuthService configured with settings, crypto, and repository.
    """
    return OAuthService(
        settings=get_settings(),
        crypto=get_crypto_utils(),
        grant_repository=oauth_grant_repo,
    )


async def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
    oauth_grant_repo: OAuthGrantRepository = Depends(get_oauth_grant_repository),
    refresh_token_repo: RefreshTokenRepository = Depends(get_refresh_token_repository),
    oauth_service: OAuthService = Depends(get_oauth_service),
    token_service: TokenService = Depends(get_token_service),
    session: AsyncSession = Depends(get_db_session),
) -> AuthService:
    """Provide an AuthService instance with all dependencies.

    Args:
        user_repo: The user repository from DI.
        oauth_grant_repo: The OAuth grant repository from DI.
        refresh_token_repo: The refresh token repository from DI.
        oauth_service: The OAuth service from DI.
        token_service: The token service from DI.
        session: The async database session for employee lookup.

    Returns:
        A fully configured AuthService orchestrator.
    """
    employee_repo = EmployeeRepo(session)
    return AuthService(
        settings=get_settings(),
        jwt_utils=get_jwt_utils(),
        crypto=get_crypto_utils(),
        whitelist_service=get_whitelist_service(),
        oauth_service=oauth_service,
        token_service=token_service,
        user_repository=user_repo,
        oauth_grant_repository=oauth_grant_repo,
        refresh_token_repository=refresh_token_repo,
        employee_repository=employee_repo,
    )


async def get_current_user(
    request: Request,
    token_service: TokenService = Depends(get_token_service),
    user_repo: UserRepository = Depends(get_user_repository),
) -> User:
    """Extract and validate the current authenticated user from the request.

    Reads the JWT access token from the ``access_token`` cookie, decodes
    and validates it, then looks up the corresponding user in the database.

    Args:
        request: The incoming FastAPI request object.
        token_service: Service for JWT token verification.
        user_repo: Repository for user lookup by ID.

    Returns:
        The authenticated User entity.

    Raises:
        InvalidTokenError: If the token is missing, invalid, expired,
            or the user cannot be found.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise InvalidTokenError()

    try:
        payload = token_service.verify_access_token(token)
    except InvalidTokenError:
        raise

    user = await user_repo.get_by_id(payload.sub)
    if user is None:
        raise InvalidTokenError()

    return user


# ---------------------------------------------------------------------------
# Admin module dependencies
# ---------------------------------------------------------------------------


async def get_whitelist_repository(
    session: AsyncSession = Depends(get_db_session),
) -> WhitelistRepository:
    """Provide a WhitelistRepository instance.

    Args:
        session: The async database session from DI.

    Returns:
        A WhitelistRepository bound to the current session.
    """
    return WhitelistRepository(session)


async def get_oauth_config_repository(
    session: AsyncSession = Depends(get_db_session),
) -> OAuthConfigRepository:
    """Provide an OAuthConfigRepository instance.

    Args:
        session: The async database session from DI.

    Returns:
        An OAuthConfigRepository bound to the current session.
    """
    return OAuthConfigRepository(session)


async def get_audit_log_repository(
    session: AsyncSession = Depends(get_db_session),
) -> AuditLogRepository:
    """Provide an AuditLogRepository instance.

    Args:
        session: The async database session from DI.

    Returns:
        An AuditLogRepository bound to the current session.
    """
    return AuditLogRepository(session)


async def get_role_service(
    session: AsyncSession = Depends(get_db_session),
) -> RoleService:
    """Provide a RoleService instance.

    Args:
        session: The async database session from DI.

    Returns:
        A RoleService configured with the super admin email from settings.
    """
    settings = get_settings()
    return RoleService(session=session, super_admin_email=settings.super_admin_email)


def _get_whitelist_loader() -> WhitelistLoader | None:
    """Create a WhitelistLoader if the whitelist file exists.

    Returns:
        A WhitelistLoader instance, or None if the file does not exist
        or the path is not configured.
    """
    settings = get_settings()
    try:
        return WhitelistLoader(settings.whitelist_file_path)
    except FileNotFoundError:
        logger.warning(
            "Whitelist file not found at '%s'. Operating with database-only whitelist.",
            settings.whitelist_file_path,
        )
        return None


async def get_whitelist_manager(
    whitelist_repo: WhitelistRepository = Depends(get_whitelist_repository),
) -> WhitelistManager:
    """Provide a WhitelistManager instance.

    Combines the database-backed WhitelistRepository with the optional
    file-based WhitelistLoader for a unified whitelist.

    Args:
        whitelist_repo: The whitelist repository from DI.

    Returns:
        A WhitelistManager merging file and database whitelist sources.
    """
    file_loader = _get_whitelist_loader()
    return WhitelistManager(repo=whitelist_repo, file_loader=file_loader)


async def get_oauth_config_manager(
    oauth_config_repo: OAuthConfigRepository = Depends(get_oauth_config_repository),
) -> OAuthConfigManager:
    """Provide an OAuthConfigManager instance.

    Args:
        oauth_config_repo: The OAuth config repository from DI.

    Returns:
        An OAuthConfigManager configured with crypto utils and env fallback values.
    """
    settings = get_settings()
    return OAuthConfigManager(
        repository=oauth_config_repo,
        crypto=get_crypto_utils(),
        google_client_id=settings.google_client_id,
        google_client_secret=settings.google_client_secret,
        google_redirect_uri=settings.google_redirect_uri,
    )


async def get_audit_service(
    audit_log_repo: AuditLogRepository = Depends(get_audit_log_repository),
) -> AuditService:
    """Provide an AuditService instance.

    Args:
        audit_log_repo: The audit log repository from DI.

    Returns:
        An AuditService for recording and querying admin actions.
    """
    return AuditService(repository=audit_log_repo)
