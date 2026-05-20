"""Redis-based sliding window quota tracker for Gmail API rate limiting.

Uses Redis sorted sets to implement a sliding window counter that tracks
quota unit consumption per user within a 1-second window. Each Gmail API
call consumes a certain number of quota units; the tracker ensures the
per-user rate does not exceed 250 units/second.
"""

import asyncio
import time
from uuid import UUID

import redis.asyncio as redis

from src.modules.gmail.infrastructure.config import GmailSettings


class QuotaTracker:
    """Tracks Gmail API quota consumption per user using Redis sliding window.

    Each Gmail API call consumes quota units. This tracker uses a Redis sorted
    set per user to record consumption timestamps and unit counts, enforcing
    the configured per-second limit (default 250 units/second).

    The sliding window is 1 second wide. Entries older than 1 second are
    pruned on each check. Each entry in the sorted set uses the timestamp
    as the score and a unique member string encoding the timestamp and units.

    Args:
        redis_client: An async Redis client instance.
        settings: GmailSettings containing quota_units_per_second.

    Example:
        >>> tracker = QuotaTracker(redis_client, settings)
        >>> await tracker.wait_if_needed(user_id, units=5)
        >>> await tracker.consume(user_id, units=5)
    """

    def __init__(self, redis_client: redis.Redis, settings: GmailSettings) -> None:
        """Initialize the quota tracker.

        Args:
            redis_client: An async Redis client instance.
            settings: GmailSettings containing quota configuration.
        """
        self._redis = redis_client
        self._quota_limit = settings.quota_units_per_second
        self._window_seconds = 1.0

    def _key(self, user_id: UUID) -> str:
        """Build the Redis key for a user's quota tracking sorted set.

        Args:
            user_id: The user whose quota is being tracked.

        Returns:
            The Redis key string.
        """
        return f"gmail:quota:{user_id}"

    async def _get_current_usage(self, user_id: UUID) -> int:
        """Get the current quota usage within the sliding window.

        Removes expired entries and counts remaining units.

        Args:
            user_id: The user to check.

        Returns:
            Total quota units consumed in the current 1-second window.
        """
        key = self._key(user_id)
        now = time.time()
        window_start = now - self._window_seconds

        pipe = self._redis.pipeline()
        # Remove entries outside the sliding window
        pipe.zremrangebyscore(key, "-inf", window_start)
        # Get all entries within the window
        pipe.zrangebyscore(key, window_start, "+inf")
        results = await pipe.execute()

        # Each member is formatted as "{timestamp}:{units}"
        members: list[str] = results[1]
        total_units = 0
        for member in members:
            parts = member.rsplit(":", 1)
            if len(parts) == 2:
                total_units += int(parts[1])

        return total_units

    async def can_consume(self, user_id: UUID, units: int) -> bool:
        """Check whether consuming the given units would exceed the quota limit.

        Args:
            user_id: The user to check.
            units: Number of quota units to check.

        Returns:
            True if consuming the units would stay within the limit,
            False if it would exceed the per-second quota.
        """
        current_usage = await self._get_current_usage(user_id)
        return (current_usage + units) <= self._quota_limit

    async def consume(self, user_id: UUID, units: int) -> None:
        """Record consumption of quota units for a user.

        Adds an entry to the user's sorted set with the current timestamp
        as the score and a unique member encoding the units consumed.

        Args:
            user_id: The user consuming quota.
            units: Number of quota units consumed.
        """
        key = self._key(user_id)
        now = time.time()
        # Use a unique member: "{timestamp}:{units}" to avoid collisions
        member = f"{now}:{units}"

        pipe = self._redis.pipeline()
        pipe.zadd(key, {member: now})
        # Set TTL to 2 seconds to auto-cleanup stale keys
        pipe.expire(key, 2)
        await pipe.execute()

    async def wait_if_needed(self, user_id: UUID, units: int) -> None:
        """Wait until the user has enough quota headroom to consume the given units.

        Polls the current usage and sleeps in small increments until the
        sliding window has enough capacity. This ensures no API call is made
        that would exceed the per-user rate limit.

        Args:
            user_id: The user to throttle.
            units: Number of quota units needed for the next API call.
        """
        while not await self.can_consume(user_id, units):
            # Sleep a short interval and re-check; the window slides
            # continuously so capacity frees up quickly.
            await asyncio.sleep(0.05)
