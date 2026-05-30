"""Dependency injection container for the Policy Engine module.

Provides FastAPI dependency functions that wire together all services,
repositories, and infrastructure components using async database sessions
and Redis connections. Follows the same pattern as identity/container.py.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Annotated

import redis.asyncio as redis
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.container import get_current_user, get_db_session
from src.modules.identity.domain.entities import User, UserRole
from src.modules.policy.application.audit_service import PolicyAuditService
from src.modules.policy.application.evaluation_service import EvaluationService
from src.modules.policy.application.policy_service import PolicyService
from src.modules.policy.application.template_service import TemplateService
from src.modules.policy.application.version_service import VersionService
from src.modules.policy.infrastructure.cache_client import PolicyCacheClient
from src.modules.policy.infrastructure.config import PolicySettings
from src.modules.policy.infrastructure.policy_repository import PolicyRepository
from src.modules.policy.infrastructure.template_repository import TemplateRepository
from src.modules.policy.infrastructure.version_repository import VersionRepository

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Singletons (cached at process level)
# ---------------------------------------------------------------------------


@lru_cache
def get_policy_settings() -> PolicySettings:
    """Load and cache PolicySettings from environment variables.

    Returns:
        The PolicySettings singleton loaded from POLICY_* env vars.
    """
    return PolicySettings()  # type: ignore[call-arg]


@lru_cache
def _get_policy_redis_client() -> redis.Redis:
    """Create and cache the async Redis client for the policy module.

    Uses the same Redis instance as the identity module (redis://localhost:6379/0)
    but could be configured separately via POLICY_REDIS_URL if needed.

    Returns:
        An async Redis client connected to the configured Redis URL.
    """
    from src.modules.identity.container import get_settings as get_auth_settings

    auth_settings = get_auth_settings()
    return redis.from_url(auth_settings.redis_url, decode_responses=True)


# ---------------------------------------------------------------------------
# Request-scoped dependencies (repositories)
# ---------------------------------------------------------------------------


async def get_policy_repository(
    session: AsyncSession = Depends(get_db_session),
) -> PolicyRepository:
    """Provide a PolicyRepository instance.

    Args:
        session: The async database session from DI.

    Returns:
        A PolicyRepository bound to the current session.
    """
    return PolicyRepository(session)


async def get_template_repository(
    session: AsyncSession = Depends(get_db_session),
) -> TemplateRepository:
    """Provide a TemplateRepository instance.

    Args:
        session: The async database session from DI.

    Returns:
        A TemplateRepository bound to the current session.
    """
    return TemplateRepository(session)


async def get_version_repository(
    session: AsyncSession = Depends(get_db_session),
) -> VersionRepository:
    """Provide a VersionRepository instance.

    Args:
        session: The async database session from DI.

    Returns:
        A VersionRepository bound to the current session.
    """
    return VersionRepository(session)


# ---------------------------------------------------------------------------
# Infrastructure clients
# ---------------------------------------------------------------------------


def get_cache_client() -> PolicyCacheClient:
    """Provide a PolicyCacheClient instance.

    Returns:
        A PolicyCacheClient configured with Redis and policy settings.
    """
    return PolicyCacheClient(
        redis_client=_get_policy_redis_client(),
        settings=get_policy_settings(),
    )


# ---------------------------------------------------------------------------
# Application services
# ---------------------------------------------------------------------------


async def get_audit_service(
    session: AsyncSession = Depends(get_db_session),
) -> PolicyAuditService:
    """Provide a PolicyAuditService instance.

    Args:
        session: The async database session from DI.

    Returns:
        A PolicyAuditService bound to the current session.
    """
    return PolicyAuditService(session)


async def get_policy_service(
    policy_repo: PolicyRepository = Depends(get_policy_repository),
    template_repo: TemplateRepository = Depends(get_template_repository),
    session: AsyncSession = Depends(get_db_session),
) -> PolicyService:
    """Provide a PolicyService instance.

    Args:
        policy_repo: The policy repository from DI.
        template_repo: The template repository from DI.
        session: The async database session for audit logging.

    Returns:
        A PolicyService configured with repositories and audit service.
    """
    audit_service = PolicyAuditService(session)
    return PolicyService(
        policy_repo=policy_repo,
        template_repo=template_repo,
        audit_service=audit_service,
    )


async def get_version_service(
    policy_repo: PolicyRepository = Depends(get_policy_repository),
    version_repo: VersionRepository = Depends(get_version_repository),
) -> VersionService:
    """Provide a VersionService instance.

    Args:
        policy_repo: The policy repository from DI.
        version_repo: The version repository from DI.

    Returns:
        A VersionService configured with repositories and cache.
    """
    return VersionService(
        policy_repository=policy_repo,
        version_repository=version_repo,
        cache_client=get_cache_client(),
    )


async def get_evaluation_service(
    policy_repo: PolicyRepository = Depends(get_policy_repository),
    version_repo: VersionRepository = Depends(get_version_repository),
) -> EvaluationService:
    """Provide an EvaluationService instance.

    Args:
        policy_repo: The policy repository from DI.
        version_repo: The version repository from DI.

    Returns:
        An EvaluationService configured with repositories and cache.
    """
    return EvaluationService(
        policy_repository=policy_repo,
        version_repository=version_repo,
        cache_client=get_cache_client(),
    )


async def get_template_service(
    session: AsyncSession = Depends(get_db_session),
    template_repo: TemplateRepository = Depends(get_template_repository),
    policy_repo: PolicyRepository = Depends(get_policy_repository),
) -> TemplateService:
    """Provide a TemplateService instance.

    Args:
        session: The async database session for transaction management.
        template_repo: The template repository from DI.
        policy_repo: The policy repository from DI.

    Returns:
        A TemplateService configured with session and repositories.
    """
    return TemplateService(
        session=session,
        template_repo=template_repo,
        policy_repo=policy_repo,
    )


# ---------------------------------------------------------------------------
# Auth dependencies for policy module
# ---------------------------------------------------------------------------


async def require_policy_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Verify the current user has the Admin role for policy management.

    This dependency enforces admin-only access on all policy management
    endpoints. Returns a generic authorization error without revealing
    whether the requested resource exists.

    Args:
        current_user: The authenticated User entity from the JWT.

    Returns:
        The authenticated User entity if they have the Admin role.

    Raises:
        HTTPException: 403 Forbidden if the user does not have the Admin role.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "INSUFFICIENT_ROLE",
                "message": "Access denied",
                "fields": [],
            },
        )
    return current_user


# Type alias for use in endpoint signatures.
PolicyAdminDep = Annotated[User, Depends(require_policy_admin)]
AuthenticatedUserDep = Annotated[User, Depends(get_current_user)]
