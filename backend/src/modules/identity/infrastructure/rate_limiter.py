"""Redis-based sliding window rate limiter for login attempts.

Uses Redis sorted sets to implement a sliding window counter that tracks
requests per IP address within a configurable time window.
"""

import time

import redis.asyncio as redis

from src.modules.identity.infrastructure.config import AuthSettings


class RateLimiter:
    """Redis-based sliding window rate limiter.

    Tracks login attempts per IP address using Redis sorted sets. Each request
    is stored as a member with its timestamp as the score, enabling efficient
    sliding window calculations.

    Args:
        redis_client: An async Redis client instance.
        settings: AuthSettings containing rate_limit_login_max and
            rate_limit_login_window_seconds.

    Example:
        >>> limiter = RateLimiter(redis_client, settings)
        >>> allowed = await limiter.check_rate_limit("192.168.1.1")
        >>> if not allowed:
        ...     raise RateLimitExceededError()
    """

    def __init__(self, redis_client: redis.Redis, settings: AuthSettings) -> None:
        """Initialize the rate limiter.

        Args:
            redis_client: An async Redis client instance.
            settings: AuthSettings containing rate limit configuration.
        """
        self._redis = redis_client
        self._max_requests = settings.rate_limit_login_max
        self._window_seconds = settings.rate_limit_login_window_seconds

    async def check_rate_limit(self, ip: str) -> bool:
        """Check whether a request from the given IP is within the rate limit.

        Uses a sliding window algorithm with Redis sorted sets:
        1. Remove expired entries outside the current window.
        2. Count remaining entries in the window.
        3. If under the limit, add the current request timestamp.

        Args:
            ip: The client IP address to check.

        Returns:
            True if the request is allowed (under the limit), False if the
            rate limit has been exceeded.
        """
        key = f"rate_limit:login:{ip}"
        now = time.time()
        window_start = now - self._window_seconds

        pipe = self._redis.pipeline()

        # Remove entries outside the sliding window
        pipe.zremrangebyscore(key, "-inf", window_start)

        # Count entries within the current window
        pipe.zcard(key)

        results = await pipe.execute()
        current_count: int = results[1]

        if current_count >= self._max_requests:
            return False

        # Add the current request and set key expiry
        pipe = self._redis.pipeline()
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, self._window_seconds)
        await pipe.execute()

        return True
