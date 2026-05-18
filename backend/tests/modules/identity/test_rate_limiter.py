"""Unit tests for Redis-based sliding window rate limiter."""

from unittest.mock import AsyncMock, patch

import pytest

from src.modules.identity.infrastructure.config import AuthSettings
from src.modules.identity.infrastructure.rate_limiter import RateLimiter


@pytest.fixture
def auth_settings() -> AuthSettings:
    """Create AuthSettings with default rate limit values for testing."""
    return AuthSettings(
        google_client_id="test-client-id",
        google_client_secret="test-client-secret",
        google_redirect_uri="http://localhost:8000/api/auth/callback",
        jwt_secret_key="test-jwt-secret-key-at-least-32-chars-long",
        oauth_token_encryption_key="dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlcyE=",
        rate_limit_login_max=5,
        rate_limit_login_window_seconds=60,
    )


@pytest.fixture
def mock_redis() -> AsyncMock:
    """Create a mock async Redis client."""
    client = AsyncMock()
    return client


@pytest.fixture
def rate_limiter(mock_redis: AsyncMock, auth_settings: AuthSettings) -> RateLimiter:
    """Create a RateLimiter instance with mocked Redis."""
    return RateLimiter(mock_redis, auth_settings)


class TestRateLimiterInit:
    """Tests for RateLimiter initialization."""

    def test_stores_max_requests_from_settings(
        self, rate_limiter: RateLimiter, auth_settings: AuthSettings
    ) -> None:
        assert rate_limiter._max_requests == auth_settings.rate_limit_login_max

    def test_stores_window_seconds_from_settings(
        self, rate_limiter: RateLimiter, auth_settings: AuthSettings
    ) -> None:
        assert rate_limiter._window_seconds == auth_settings.rate_limit_login_window_seconds

    def test_stores_redis_client(
        self, rate_limiter: RateLimiter, mock_redis: AsyncMock
    ) -> None:
        assert rate_limiter._redis is mock_redis


class TestCheckRateLimit:
    """Tests for check_rate_limit method."""

    async def test_allows_request_when_under_limit(
        self, rate_limiter: RateLimiter, mock_redis: AsyncMock
    ) -> None:
        """First request from an IP should be allowed."""
        # Mock pipeline: zremrangebyscore returns 0 removed, zcard returns 0
        pipeline_mock = AsyncMock()
        pipeline_mock.execute = AsyncMock(side_effect=[[0, 0], [True, True]])
        pipeline_mock.zremrangebyscore = AsyncMock()
        pipeline_mock.zcard = AsyncMock()
        pipeline_mock.zadd = AsyncMock()
        pipeline_mock.expire = AsyncMock()
        mock_redis.pipeline = lambda: pipeline_mock

        result = await rate_limiter.check_rate_limit("192.168.1.1")

        assert result is True

    async def test_blocks_request_when_at_limit(
        self, rate_limiter: RateLimiter, mock_redis: AsyncMock
    ) -> None:
        """Request should be blocked when count equals max_requests."""
        pipeline_mock = AsyncMock()
        # zremrangebyscore removes expired, zcard returns 5 (at limit)
        pipeline_mock.execute = AsyncMock(return_value=[0, 5])
        pipeline_mock.zremrangebyscore = AsyncMock()
        pipeline_mock.zcard = AsyncMock()
        mock_redis.pipeline = lambda: pipeline_mock

        result = await rate_limiter.check_rate_limit("192.168.1.1")

        assert result is False

    async def test_blocks_request_when_over_limit(
        self, rate_limiter: RateLimiter, mock_redis: AsyncMock
    ) -> None:
        """Request should be blocked when count exceeds max_requests."""
        pipeline_mock = AsyncMock()
        pipeline_mock.execute = AsyncMock(return_value=[0, 10])
        pipeline_mock.zremrangebyscore = AsyncMock()
        pipeline_mock.zcard = AsyncMock()
        mock_redis.pipeline = lambda: pipeline_mock

        result = await rate_limiter.check_rate_limit("192.168.1.1")

        assert result is False

    async def test_allows_request_when_one_below_limit(
        self, rate_limiter: RateLimiter, mock_redis: AsyncMock
    ) -> None:
        """Request should be allowed when count is one below max."""
        pipeline_mock = AsyncMock()
        pipeline_mock.execute = AsyncMock(side_effect=[[0, 4], [True, True]])
        pipeline_mock.zremrangebyscore = AsyncMock()
        pipeline_mock.zcard = AsyncMock()
        pipeline_mock.zadd = AsyncMock()
        pipeline_mock.expire = AsyncMock()
        mock_redis.pipeline = lambda: pipeline_mock

        result = await rate_limiter.check_rate_limit("192.168.1.1")

        assert result is True

    async def test_uses_correct_key_format(
        self, rate_limiter: RateLimiter, mock_redis: AsyncMock
    ) -> None:
        """Rate limiter should use 'rate_limit:login:{ip}' key format."""
        pipeline_mock = AsyncMock()
        pipeline_mock.execute = AsyncMock(side_effect=[[0, 0], [True, True]])
        pipeline_mock.zremrangebyscore = AsyncMock()
        pipeline_mock.zcard = AsyncMock()
        pipeline_mock.zadd = AsyncMock()
        pipeline_mock.expire = AsyncMock()
        mock_redis.pipeline = lambda: pipeline_mock

        await rate_limiter.check_rate_limit("10.0.0.1")

        # Verify zremrangebyscore was called with the correct key
        pipeline_mock.zremrangebyscore.assert_called_once()
        call_args = pipeline_mock.zremrangebyscore.call_args
        assert call_args[0][0] == "rate_limit:login:10.0.0.1"

    @patch("src.modules.identity.infrastructure.rate_limiter.time.time")
    async def test_removes_expired_entries(
        self, mock_time: AsyncMock, rate_limiter: RateLimiter, mock_redis: AsyncMock
    ) -> None:
        """Should remove entries older than the sliding window."""
        mock_time.return_value = 1000.0
        pipeline_mock = AsyncMock()
        pipeline_mock.execute = AsyncMock(side_effect=[[0, 0], [True, True]])
        pipeline_mock.zremrangebyscore = AsyncMock()
        pipeline_mock.zcard = AsyncMock()
        pipeline_mock.zadd = AsyncMock()
        pipeline_mock.expire = AsyncMock()
        mock_redis.pipeline = lambda: pipeline_mock

        await rate_limiter.check_rate_limit("192.168.1.1")

        # Window is 60 seconds, so window_start = 1000.0 - 60 = 940.0
        pipeline_mock.zremrangebyscore.assert_called_once_with(
            "rate_limit:login:192.168.1.1", "-inf", 940.0
        )

    @patch("src.modules.identity.infrastructure.rate_limiter.time.time")
    async def test_adds_current_timestamp_on_allowed_request(
        self, mock_time: AsyncMock, rate_limiter: RateLimiter, mock_redis: AsyncMock
    ) -> None:
        """Should add current timestamp to sorted set when request is allowed."""
        mock_time.return_value = 1000.0
        pipeline_mock = AsyncMock()
        pipeline_mock.execute = AsyncMock(side_effect=[[0, 0], [True, True]])
        pipeline_mock.zremrangebyscore = AsyncMock()
        pipeline_mock.zcard = AsyncMock()
        pipeline_mock.zadd = AsyncMock()
        pipeline_mock.expire = AsyncMock()
        mock_redis.pipeline = lambda: pipeline_mock

        await rate_limiter.check_rate_limit("192.168.1.1")

        pipeline_mock.zadd.assert_called_once_with(
            "rate_limit:login:192.168.1.1", {"1000.0": 1000.0}
        )

    @patch("src.modules.identity.infrastructure.rate_limiter.time.time")
    async def test_sets_key_expiry_to_window_seconds(
        self, mock_time: AsyncMock, rate_limiter: RateLimiter, mock_redis: AsyncMock
    ) -> None:
        """Should set key TTL to window_seconds for automatic cleanup."""
        mock_time.return_value = 1000.0
        pipeline_mock = AsyncMock()
        pipeline_mock.execute = AsyncMock(side_effect=[[0, 0], [True, True]])
        pipeline_mock.zremrangebyscore = AsyncMock()
        pipeline_mock.zcard = AsyncMock()
        pipeline_mock.zadd = AsyncMock()
        pipeline_mock.expire = AsyncMock()
        mock_redis.pipeline = lambda: pipeline_mock

        await rate_limiter.check_rate_limit("192.168.1.1")

        pipeline_mock.expire.assert_called_once_with(
            "rate_limit:login:192.168.1.1", 60
        )

    async def test_does_not_add_entry_when_blocked(
        self, rate_limiter: RateLimiter, mock_redis: AsyncMock
    ) -> None:
        """Should not add a new entry when the request is rate-limited."""
        pipeline_mock = AsyncMock()
        # Only one execute call expected (the check pipeline)
        pipeline_mock.execute = AsyncMock(return_value=[0, 5])
        pipeline_mock.zremrangebyscore = AsyncMock()
        pipeline_mock.zcard = AsyncMock()
        pipeline_mock.zadd = AsyncMock()
        pipeline_mock.expire = AsyncMock()
        mock_redis.pipeline = lambda: pipeline_mock

        await rate_limiter.check_rate_limit("192.168.1.1")

        # zadd should not be called when request is blocked
        pipeline_mock.zadd.assert_not_called()


class TestRateLimiterWithCustomSettings:
    """Tests with non-default rate limit settings."""

    async def test_custom_max_requests(self, mock_redis: AsyncMock) -> None:
        """Should respect custom max_requests setting."""
        settings = AuthSettings(
            google_client_id="test-client-id",
            google_client_secret="test-client-secret",
            jwt_secret_key="test-jwt-secret-key-at-least-32-chars-long",
            oauth_token_encryption_key="dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlcyE=",
            rate_limit_login_max=10,
            rate_limit_login_window_seconds=120,
        )
        limiter = RateLimiter(mock_redis, settings)

        pipeline_mock = AsyncMock()
        # 9 requests — still under limit of 10
        pipeline_mock.execute = AsyncMock(side_effect=[[0, 9], [True, True]])
        pipeline_mock.zremrangebyscore = AsyncMock()
        pipeline_mock.zcard = AsyncMock()
        pipeline_mock.zadd = AsyncMock()
        pipeline_mock.expire = AsyncMock()
        mock_redis.pipeline = lambda: pipeline_mock

        result = await limiter.check_rate_limit("10.0.0.1")

        assert result is True

    async def test_custom_max_requests_at_limit(self, mock_redis: AsyncMock) -> None:
        """Should block at custom max_requests threshold."""
        settings = AuthSettings(
            google_client_id="test-client-id",
            google_client_secret="test-client-secret",
            jwt_secret_key="test-jwt-secret-key-at-least-32-chars-long",
            oauth_token_encryption_key="dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlcyE=",
            rate_limit_login_max=10,
            rate_limit_login_window_seconds=120,
        )
        limiter = RateLimiter(mock_redis, settings)

        pipeline_mock = AsyncMock()
        pipeline_mock.execute = AsyncMock(return_value=[0, 10])
        pipeline_mock.zremrangebyscore = AsyncMock()
        pipeline_mock.zcard = AsyncMock()
        mock_redis.pipeline = lambda: pipeline_mock

        result = await limiter.check_rate_limit("10.0.0.1")

        assert result is False
