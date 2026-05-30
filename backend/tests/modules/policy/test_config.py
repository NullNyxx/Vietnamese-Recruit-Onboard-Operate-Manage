"""Tests for PolicySettings configuration."""

import pytest
from pydantic import ValidationError

from src.modules.policy.infrastructure.config import PolicySettings


class TestPolicySettingsDefaults:
    """Verify default values are applied correctly."""

    def test_loads_with_defaults(self) -> None:
        settings = PolicySettings()

        assert settings.cache_ttl == 300
        assert settings.custom_rule_limit == 500
        assert settings.evaluation_timeout == 500

    def test_cache_ttl_default_is_5_minutes(self) -> None:
        settings = PolicySettings()

        assert settings.cache_ttl == 300  # 5 minutes in seconds


class TestPolicySettingsEnvPrefix:
    """Verify POLICY_ prefix is used for environment variable mapping."""

    def test_env_prefix_applied(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("POLICY_CACHE_TTL", "600")
        monkeypatch.setenv("POLICY_CUSTOM_RULE_LIMIT", "1000")
        monkeypatch.setenv("POLICY_EVALUATION_TIMEOUT", "750")

        settings = PolicySettings()

        assert settings.cache_ttl == 600
        assert settings.custom_rule_limit == 1000
        assert settings.evaluation_timeout == 750


class TestPolicySettingsValidation:
    """Verify field validation rules."""

    def test_cache_ttl_must_be_positive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("POLICY_CACHE_TTL", "0")

        with pytest.raises(ValidationError):
            PolicySettings()

    def test_cache_ttl_negative_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("POLICY_CACHE_TTL", "-1")

        with pytest.raises(ValidationError):
            PolicySettings()

    def test_custom_rule_limit_must_be_positive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("POLICY_CUSTOM_RULE_LIMIT", "0")

        with pytest.raises(ValidationError):
            PolicySettings()

    def test_evaluation_timeout_must_be_positive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("POLICY_EVALUATION_TIMEOUT", "0")

        with pytest.raises(ValidationError):
            PolicySettings()

    def test_accepts_custom_positive_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("POLICY_CACHE_TTL", "60")
        monkeypatch.setenv("POLICY_CUSTOM_RULE_LIMIT", "100")
        monkeypatch.setenv("POLICY_EVALUATION_TIMEOUT", "1000")

        settings = PolicySettings()

        assert settings.cache_ttl == 60
        assert settings.custom_rule_limit == 100
        assert settings.evaluation_timeout == 1000
