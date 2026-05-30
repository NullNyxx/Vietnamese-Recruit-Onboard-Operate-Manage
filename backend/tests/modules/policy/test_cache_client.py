"""Unit tests for the Redis-based policy cache client."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.modules.policy.infrastructure.cache_client import PolicyCacheClient
from src.modules.policy.infrastructure.config import PolicySettings


@pytest.fixture
def policy_settings() -> PolicySettings:
    """Create PolicySettings with default values."""
    return PolicySettings()  # type: ignore[call-arg]


@pytest.fixture
def mock_redis() -> AsyncMock:
    """Create a mock async Redis client."""
    return AsyncMock()


@pytest.fixture
def cache_client(mock_redis: AsyncMock, policy_settings: PolicySettings) -> PolicyCacheClient:
    """Create a PolicyCacheClient with mocked Redis."""
    return PolicyCacheClient(mock_redis, policy_settings)


class TestPolicyCacheClientInit:
    """Tests for PolicyCacheClient initialization."""

    def test_stores_redis_client(
        self, cache_client: PolicyCacheClient, mock_redis: AsyncMock
    ) -> None:
        assert cache_client._redis is mock_redis

    def test_stores_ttl_from_settings(
        self, cache_client: PolicyCacheClient, policy_settings: PolicySettings
    ) -> None:
        assert cache_client._ttl == policy_settings.cache_ttl

    def test_default_ttl_is_300(self, cache_client: PolicyCacheClient) -> None:
        assert cache_client._ttl == 300


class TestPolicyCacheClientKey:
    """Tests for Redis key generation."""

    def test_key_format(self, cache_client: PolicyCacheClient) -> None:
        key = cache_client._key("tenant-abc")
        assert key == "policy:tenant-abc:active"

    def test_key_with_different_tenant(self, cache_client: PolicyCacheClient) -> None:
        key = cache_client._key("company-xyz-123")
        assert key == "policy:company-xyz-123:active"


class TestGetActivePolicy:
    """Tests for get_active_policy method."""

    async def test_returns_snapshot_on_cache_hit(
        self, cache_client: PolicyCacheClient, mock_redis: AsyncMock
    ) -> None:
        """Should return deserialized snapshot when cache has data."""
        snapshot = {"version": 1, "rules": [{"id": "rule-1"}]}
        mock_redis.get = AsyncMock(return_value=json.dumps(snapshot))

        result = await cache_client.get_active_policy("tenant-1")

        assert result == snapshot
        mock_redis.get.assert_called_once_with("policy:tenant-1:active")

    async def test_returns_none_on_cache_miss(
        self, cache_client: PolicyCacheClient, mock_redis: AsyncMock
    ) -> None:
        """Should return None when key does not exist in Redis."""
        mock_redis.get = AsyncMock(return_value=None)

        result = await cache_client.get_active_policy("tenant-1")

        assert result is None

    async def test_returns_none_on_redis_error(
        self, cache_client: PolicyCacheClient, mock_redis: AsyncMock
    ) -> None:
        """Should return None and log warning on Redis connection error."""
        import redis.asyncio as redis

        mock_redis.get = AsyncMock(side_effect=redis.RedisError("Connection refused"))

        with patch(
            "src.modules.policy.infrastructure.cache_client.logger"
        ) as mock_logger:
            result = await cache_client.get_active_policy("tenant-1")

        assert result is None
        mock_logger.warning.assert_called_once()

    async def test_returns_none_on_invalid_json(
        self, cache_client: PolicyCacheClient, mock_redis: AsyncMock
    ) -> None:
        """Should return None when cached data is not valid JSON."""
        mock_redis.get = AsyncMock(return_value="not-valid-json{{{")

        result = await cache_client.get_active_policy("tenant-1")

        assert result is None


class TestSetActivePolicy:
    """Tests for set_active_policy method."""

    async def test_stores_snapshot_with_ttl(
        self, cache_client: PolicyCacheClient, mock_redis: AsyncMock
    ) -> None:
        """Should store JSON-serialized snapshot with configured TTL."""
        snapshot = {"version": 2, "rules": []}
        mock_redis.set = AsyncMock()

        await cache_client.set_active_policy("tenant-1", snapshot)

        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "policy:tenant-1:active"
        # Verify the stored data is valid JSON matching the snapshot
        stored_data = json.loads(call_args[0][1])
        assert stored_data == snapshot
        assert call_args[1]["ex"] == 300

    async def test_handles_redis_error_gracefully(
        self, cache_client: PolicyCacheClient, mock_redis: AsyncMock
    ) -> None:
        """Should not raise on Redis error, just log warning."""
        import redis.asyncio as redis

        mock_redis.set = AsyncMock(side_effect=redis.RedisError("Connection refused"))

        # Should not raise
        await cache_client.set_active_policy("tenant-1", {"version": 1})

    async def test_preserves_unicode_characters(
        self, cache_client: PolicyCacheClient, mock_redis: AsyncMock
    ) -> None:
        """Should preserve Vietnamese/Unicode text without escaping."""
        snapshot = {"name": "Chính sách nghỉ phép", "rules": []}
        mock_redis.set = AsyncMock()

        await cache_client.set_active_policy("tenant-1", snapshot)

        call_args = mock_redis.set.call_args
        stored_json = call_args[0][1]
        # Vietnamese characters should not be escaped
        assert "Chính sách nghỉ phép" in stored_json


class TestInvalidate:
    """Tests for invalidate method."""

    async def test_deletes_cache_key(
        self, cache_client: PolicyCacheClient, mock_redis: AsyncMock
    ) -> None:
        """Should delete the tenant's cache key."""
        mock_redis.delete = AsyncMock()

        await cache_client.invalidate("tenant-1")

        mock_redis.delete.assert_called_once_with("policy:tenant-1:active")

    async def test_handles_redis_error_gracefully(
        self, cache_client: PolicyCacheClient, mock_redis: AsyncMock
    ) -> None:
        """Should not raise on Redis error, just log warning."""
        import redis.asyncio as redis

        mock_redis.delete = AsyncMock(side_effect=redis.RedisError("Connection refused"))

        # Should not raise
        await cache_client.invalidate("tenant-1")
