"""Redis cache client for active policy version caching.

Provides a thin async wrapper around Redis for storing and retrieving
the active policy version snapshot per tenant. Uses the key pattern
``policy:{tenant_id}:active`` with a configurable TTL (default 5 minutes).

On cache miss, callers should fall back to PostgreSQL. Redis connection
errors are handled gracefully — logged and treated as cache misses.
"""

import json
import logging
from typing import Any

import redis.asyncio as redis

from src.modules.policy.infrastructure.config import PolicySettings

logger = logging.getLogger(__name__)


class PolicyCacheClient:
    """Async Redis cache for active policy version snapshots.

    Stores the active (latest published) policy version snapshot as JSON
    per tenant. The cache is invalidated when a new version is published.

    Args:
        redis_client: An async Redis client instance.
        settings: PolicySettings containing cache_ttl configuration.

    Example:
        >>> cache = PolicyCacheClient(redis_client, settings)
        >>> snapshot = await cache.get_active_policy("tenant-123")
        >>> if snapshot is None:
        ...     snapshot = await fetch_from_db("tenant-123")
        ...     await cache.set_active_policy("tenant-123", snapshot)
    """

    def __init__(self, redis_client: redis.Redis, settings: PolicySettings) -> None:
        """Initialize the cache client.

        Args:
            redis_client: An async Redis client instance.
            settings: PolicySettings containing cache_ttl.
        """
        self._redis = redis_client
        self._ttl = settings.cache_ttl

    def _key(self, tenant_id: str) -> str:
        """Build the Redis key for a tenant's active policy cache.

        Args:
            tenant_id: The tenant identifier.

        Returns:
            The Redis key string in the format ``policy:{tenant_id}:active``.
        """
        return f"policy:{tenant_id}:active"

    async def get_active_policy(self, tenant_id: str) -> dict[str, Any] | None:
        """Retrieve the cached active policy snapshot for a tenant.

        Args:
            tenant_id: The tenant identifier.

        Returns:
            The cached snapshot as a dict, or None on cache miss or error.
        """
        try:
            data = await self._redis.get(self._key(tenant_id))
            if data is None:
                return None
            return json.loads(data)  # type: ignore[no-any-return]
        except redis.RedisError as exc:
            logger.warning(
                "Redis error reading active policy for tenant '%s': %s",
                tenant_id,
                exc,
            )
            return None
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning(
                "Failed to deserialize cached policy for tenant '%s': %s",
                tenant_id,
                exc,
            )
            return None

    async def set_active_policy(
        self, tenant_id: str, snapshot: dict[str, Any]
    ) -> None:
        """Store the active policy snapshot in cache with TTL.

        Args:
            tenant_id: The tenant identifier.
            snapshot: The policy version snapshot dict to cache.
        """
        try:
            data = json.dumps(snapshot, ensure_ascii=False, sort_keys=True)
            await self._redis.set(self._key(tenant_id), data, ex=self._ttl)
        except redis.RedisError as exc:
            logger.warning(
                "Redis error writing active policy for tenant '%s': %s",
                tenant_id,
                exc,
            )
        except (TypeError, ValueError) as exc:
            logger.warning(
                "Failed to serialize policy snapshot for tenant '%s': %s",
                tenant_id,
                exc,
            )

    async def invalidate(self, tenant_id: str) -> None:
        """Delete the cached active policy for a tenant.

        Called when a new policy version is published to ensure the next
        evaluation fetches the fresh version from PostgreSQL.

        Args:
            tenant_id: The tenant identifier.
        """
        try:
            await self._redis.delete(self._key(tenant_id))
        except redis.RedisError as exc:
            logger.warning(
                "Redis error invalidating cache for tenant '%s': %s",
                tenant_id,
                exc,
            )
