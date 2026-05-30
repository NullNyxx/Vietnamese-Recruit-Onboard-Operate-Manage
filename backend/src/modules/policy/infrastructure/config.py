"""Policy module configuration.

Loads policy engine settings from environment variables with the POLICY_ prefix.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PolicySettings(BaseSettings):
    """Policy module configuration loaded from environment variables.

    All environment variables are prefixed with ``POLICY_``. For example,
    ``cache_ttl`` maps to ``POLICY_CACHE_TTL``.

    Attributes:
        cache_ttl: TTL in seconds for Redis-cached active policy versions.
        custom_rule_limit: Maximum number of custom rules a tenant can create.
        evaluation_timeout: Maximum time in milliseconds for a policy evaluation.
    """

    model_config = SettingsConfigDict(env_prefix="POLICY_")

    cache_ttl: int = Field(
        default=300,
        gt=0,
        description="TTL in seconds for Redis-cached active policy versions.",
    )

    custom_rule_limit: int = Field(
        default=500,
        gt=0,
        description="Maximum number of custom rules per tenant.",
    )

    evaluation_timeout: int = Field(
        default=500,
        gt=0,
        description="Maximum time in milliseconds for a single policy evaluation.",
    )
