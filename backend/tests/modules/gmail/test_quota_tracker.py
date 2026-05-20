"""Unit tests for Redis-based sliding window quota tracker."""

from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest

from src.modules.gmail.infrastructure.config import GmailSettings
from src.modules.gmail.infrastructure.quota_tracker import QuotaTracker


@pytest.fixture
def gmail_settings() -> GmailSettings:
    """Create GmailSettings with default values for testing."""
    return GmailSettings()


@pytest.fixture
def mock_redis() -> AsyncMock:
    """Create a mock async Redis client."""
    return AsyncMock()


@pytest.fixture
def quota_tracker(mock_redis: AsyncMock, gmail_settings: GmailSettings) -> QuotaTracker:
    """Create a QuotaTracker instance with mocked Redis."""
    return QuotaTracker(mock_redis, gmail_settings)


@pytest.fixture
def user_id() -> UUID:
    """A test user ID."""
    return UUID("12345678-1234-1234-1234-123456789abc")


class TestQuotaTrackerInit:
    """Tests for QuotaTracker initialization."""

    def test_stores_redis_client(
        self, quota_tracker: QuotaTracker, mock_redis: AsyncMock
    ) -> None:
        assert quota_tracker._redis is mock_redis

    def test_stores_quota_limit_from_settings(
        self, quota_tracker: QuotaTracker, gmail_settings: GmailSettings
    ) -> None:
        assert quota_tracker._quota_limit == gmail_settings.quota_units_per_second

    def test_default_quota_limit_is_250(self, quota_tracker: QuotaTracker) -> None:
        assert quota_tracker._quota_limit == 250

    def test_window_is_one_second(self, quota_tracker: QuotaTracker) -> None:
        assert quota_tracker._window_seconds == 1.0


class TestQuotaTrackerKey:
    """Tests for Redis key generation."""

    def test_key_format(self, quota_tracker: QuotaTracker, user_id: UUID) -> None:
        key = quota_tracker._key(user_id)
        assert key == f"gmail:quota:{user_id}"


class TestCanConsume:
    """Tests for can_consume method."""

    async def test_allows_when_no_usage(
        self, quota_tracker: QuotaTracker, mock_redis: AsyncMock, user_id: UUID
    ) -> None:
        """Should allow consumption when no prior usage exists."""
        pipeline_mock = AsyncMock()
        pipeline_mock.execute = AsyncMock(return_value=[0, []])
        pipeline_mock.zremrangebyscore = AsyncMock()
        pipeline_mock.zrangebyscore = AsyncMock()
        mock_redis.pipeline = lambda: pipeline_mock

        result = await quota_tracker.can_consume(user_id, 10)

        assert result is True

    async def test_allows_when_under_limit(
        self, quota_tracker: QuotaTracker, mock_redis: AsyncMock, user_id: UUID
    ) -> None:
        """Should allow when current usage + requested units <= 250."""
        pipeline_mock = AsyncMock()
        # Existing entries totaling 200 units
        pipeline_mock.execute = AsyncMock(
            return_value=[0, ["1000.0:100", "1000.1:100"]]
        )
        pipeline_mock.zremrangebyscore = AsyncMock()
        pipeline_mock.zrangebyscore = AsyncMock()
        mock_redis.pipeline = lambda: pipeline_mock

        result = await quota_tracker.can_consume(user_id, 50)

        assert result is True

    async def test_allows_when_exactly_at_limit(
        self, quota_tracker: QuotaTracker, mock_redis: AsyncMock, user_id: UUID
    ) -> None:
        """Should allow when current usage + requested units == 250."""
        pipeline_mock = AsyncMock()
        pipeline_mock.execute = AsyncMock(
            return_value=[0, ["1000.0:200"]]
        )
        pipeline_mock.zremrangebyscore = AsyncMock()
        pipeline_mock.zrangebyscore = AsyncMock()
        mock_redis.pipeline = lambda: pipeline_mock

        result = await quota_tracker.can_consume(user_id, 50)

        assert result is True

    async def test_blocks_when_over_limit(
        self, quota_tracker: QuotaTracker, mock_redis: AsyncMock, user_id: UUID
    ) -> None:
        """Should block when current usage + requested units > 250."""
        pipeline_mock = AsyncMock()
        pipeline_mock.execute = AsyncMock(
            return_value=[0, ["1000.0:250"]]
        )
        pipeline_mock.zremrangebyscore = AsyncMock()
        pipeline_mock.zrangebyscore = AsyncMock()
        mock_redis.pipeline = lambda: pipeline_mock

        result = await quota_tracker.can_consume(user_id, 1)

        assert result is False

    async def test_blocks_when_single_unit_exceeds(
        self, quota_tracker: QuotaTracker, mock_redis: AsyncMock, user_id: UUID
    ) -> None:
        """Should block when requesting more than remaining capacity."""
        pipeline_mock = AsyncMock()
        pipeline_mock.execute = AsyncMock(
            return_value=[0, ["1000.0:240"]]
        )
        pipeline_mock.zremrangebyscore = AsyncMock()
        pipeline_mock.zrangebyscore = AsyncMock()
        mock_redis.pipeline = lambda: pipeline_mock

        result = await quota_tracker.can_consume(user_id, 11)

        assert result is False


class TestConsume:
    """Tests for consume method."""

    @patch("src.modules.gmail.infrastructure.quota_tracker.time.time")
    async def test_adds_entry_to_sorted_set(
        self, mock_time: AsyncMock, quota_tracker: QuotaTracker, mock_redis: AsyncMock, user_id: UUID
    ) -> None:
        """Should add a member with timestamp:units format."""
        mock_time.return_value = 1000.5
        pipeline_mock = AsyncMock()
        pipeline_mock.execute = AsyncMock(return_value=[True, True])
        pipeline_mock.zadd = AsyncMock()
        pipeline_mock.expire = AsyncMock()
        mock_redis.pipeline = lambda: pipeline_mock

        await quota_tracker.consume(user_id, 5)

        pipeline_mock.zadd.assert_called_once_with(
            f"gmail:quota:{user_id}", {"1000.5:5": 1000.5}
        )

    @patch("src.modules.gmail.infrastructure.quota_tracker.time.time")
    async def test_sets_key_expiry(
        self, mock_time: AsyncMock, quota_tracker: QuotaTracker, mock_redis: AsyncMock, user_id: UUID
    ) -> None:
        """Should set TTL of 2 seconds on the key."""
        mock_time.return_value = 1000.0
        pipeline_mock = AsyncMock()
        pipeline_mock.execute = AsyncMock(return_value=[True, True])
        pipeline_mock.zadd = AsyncMock()
        pipeline_mock.expire = AsyncMock()
        mock_redis.pipeline = lambda: pipeline_mock

        await quota_tracker.consume(user_id, 10)

        pipeline_mock.expire.assert_called_once_with(
            f"gmail:quota:{user_id}", 2
        )


class TestWaitIfNeeded:
    """Tests for wait_if_needed method."""

    async def test_returns_immediately_when_under_limit(
        self, quota_tracker: QuotaTracker, mock_redis: AsyncMock, user_id: UUID
    ) -> None:
        """Should not sleep when quota is available."""
        pipeline_mock = AsyncMock()
        pipeline_mock.execute = AsyncMock(return_value=[0, []])
        pipeline_mock.zremrangebyscore = AsyncMock()
        pipeline_mock.zrangebyscore = AsyncMock()
        mock_redis.pipeline = lambda: pipeline_mock

        # Should return without sleeping
        await quota_tracker.wait_if_needed(user_id, 10)

    @patch("src.modules.gmail.infrastructure.quota_tracker.asyncio.sleep")
    async def test_sleeps_when_at_limit_then_proceeds(
        self, mock_sleep: AsyncMock, quota_tracker: QuotaTracker, mock_redis: AsyncMock, user_id: UUID
    ) -> None:
        """Should sleep and retry when quota is exhausted."""
        pipeline_mock = AsyncMock()
        # First call: at limit (250 used), second call: under limit (0 used)
        pipeline_mock.execute = AsyncMock(
            side_effect=[[0, ["1000.0:250"]], [0, []]]
        )
        pipeline_mock.zremrangebyscore = AsyncMock()
        pipeline_mock.zrangebyscore = AsyncMock()
        mock_redis.pipeline = lambda: pipeline_mock

        await quota_tracker.wait_if_needed(user_id, 5)

        mock_sleep.assert_called_once_with(0.05)

    @patch("src.modules.gmail.infrastructure.quota_tracker.asyncio.sleep")
    async def test_sleeps_multiple_times_until_capacity(
        self, mock_sleep: AsyncMock, quota_tracker: QuotaTracker, mock_redis: AsyncMock, user_id: UUID
    ) -> None:
        """Should keep sleeping until quota frees up."""
        pipeline_mock = AsyncMock()
        # Three calls: first two at limit, third under limit
        pipeline_mock.execute = AsyncMock(
            side_effect=[
                [0, ["1000.0:250"]],
                [0, ["1000.0:250"]],
                [0, ["1000.0:100"]],
            ]
        )
        pipeline_mock.zremrangebyscore = AsyncMock()
        pipeline_mock.zrangebyscore = AsyncMock()
        mock_redis.pipeline = lambda: pipeline_mock

        await quota_tracker.wait_if_needed(user_id, 5)

        assert mock_sleep.call_count == 2


class TestQuotaTrackerWithCustomSettings:
    """Tests with non-default quota settings."""

    async def test_custom_quota_limit(self, mock_redis: AsyncMock) -> None:
        """Should respect custom quota_units_per_second setting."""
        settings = GmailSettings(quota_units_per_second=100)
        tracker = QuotaTracker(mock_redis, settings)

        pipeline_mock = AsyncMock()
        # 90 units used, requesting 11 more → exceeds 100 limit
        pipeline_mock.execute = AsyncMock(
            return_value=[0, ["1000.0:90"]]
        )
        pipeline_mock.zremrangebyscore = AsyncMock()
        pipeline_mock.zrangebyscore = AsyncMock()
        mock_redis.pipeline = lambda: pipeline_mock

        user_id = UUID("12345678-1234-1234-1234-123456789abc")
        result = await tracker.can_consume(user_id, 11)

        assert result is False

    async def test_custom_quota_limit_allows_under(self, mock_redis: AsyncMock) -> None:
        """Should allow when under custom limit."""
        settings = GmailSettings(quota_units_per_second=100)
        tracker = QuotaTracker(mock_redis, settings)

        pipeline_mock = AsyncMock()
        # 90 units used, requesting 10 more → exactly at 100 limit
        pipeline_mock.execute = AsyncMock(
            return_value=[0, ["1000.0:90"]]
        )
        pipeline_mock.zremrangebyscore = AsyncMock()
        pipeline_mock.zrangebyscore = AsyncMock()
        mock_redis.pipeline = lambda: pipeline_mock

        user_id = UUID("12345678-1234-1234-1234-123456789abc")
        result = await tracker.can_consume(user_id, 10)

        assert result is True
