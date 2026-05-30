"""Domain entities for the Policy Engine module.

Defines SQLModel table classes for policy templates, rules, versions,
and audit logs, as well as Pydantic value objects for rule conditions
and actions.
"""

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import Column, Date, DateTime, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from src.modules.policy.domain.enums import ActionType, PolicyDomain, RuleOperator

# ---------------------------------------------------------------------------
# Value Objects (Pydantic models, not database tables)
# ---------------------------------------------------------------------------


class RuleCondition(BaseModel):
    """Represents the conditional expression within a policy rule.

    Defines when a rule applies by specifying a context field, a
    comparison operator, and a threshold value.

    Attributes:
        field: The context attribute to evaluate (e.g., "check_in_time").
        operator: The comparison operator to apply.
        value: The comparison operand; type depends on the operator.
    """

    field: str
    operator: RuleOperator
    value: Any


class RuleAction(BaseModel):
    """Represents the outcome triggered when a rule condition is met.

    Defines what happens when a rule matches, including the action
    category and type-specific parameters.

    Attributes:
        type: The category of action to perform.
        parameters: Action-specific configuration data.
    """

    type: ActionType
    parameters: dict[str, Any]


# ---------------------------------------------------------------------------
# SQLModel Table Entities
# ---------------------------------------------------------------------------


class PolicyTemplate(SQLModel, table=True):
    """System-level default policy rule template.

    Templates are pre-defined rules based on the Vietnamese Labor Code
    2019 that serve as defaults for new tenants. They are read-only
    at runtime and shared across all tenants.
    """

    __tablename__ = "policy_templates"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    domain: PolicyDomain = Field(
        sa_column=Column(String(20), nullable=False, index=True),
    )
    rule_id: str = Field(max_length=64, unique=True, nullable=False, index=True)
    name: str = Field(max_length=128, nullable=False)
    description: str = Field(max_length=512, nullable=False)
    rule_condition: dict = Field(sa_column=Column(JSONB, nullable=False))
    rule_action: dict = Field(sa_column=Column(JSONB, nullable=False))
    priority: int = Field(ge=1, le=1000, nullable=False)
    enabled: bool = Field(default=True, nullable=False)
    legal_constraints: dict | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class PolicyRule(SQLModel, table=True):
    """Tenant-specific policy rule.

    Each rule belongs to exactly one tenant and may be derived from a
    template (via template_rule_id) or be a fully custom rule. Rules
    use soft-delete (is_deleted flag) and can be disabled without
    removal.
    """

    __tablename__ = "policy_rules"
    __table_args__ = (UniqueConstraint("tenant_id", "rule_id", name="uq_policy_rules_tenant_rule"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: str = Field(max_length=64, nullable=False, index=True)
    domain: PolicyDomain = Field(
        sa_column=Column(String(20), nullable=False, index=True),
    )
    rule_id: str = Field(max_length=64, nullable=False)
    name: str = Field(max_length=128, nullable=False)
    description: str = Field(max_length=512, nullable=False)
    rule_condition: dict = Field(sa_column=Column(JSONB, nullable=False))
    rule_action: dict = Field(sa_column=Column(JSONB, nullable=False))
    priority: int = Field(ge=1, le=1000, nullable=False)
    enabled: bool = Field(default=True, nullable=False)
    template_rule_id: UUID | None = Field(default=None, foreign_key="policy_templates.id")
    is_custom: bool = Field(default=False, nullable=False)
    is_deleted: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    created_by: UUID = Field(foreign_key="users.id", nullable=False)


class PolicyVersion(SQLModel, table=True):
    """Immutable snapshot of a tenant's policy rules at a point in time.

    Each version captures the complete rule set as a JSONB snapshot,
    enabling historical evaluation and rollback. Version numbers are
    monotonically increasing per tenant.
    """

    __tablename__ = "policy_versions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "version_number", name="uq_policy_versions_tenant_version"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: str = Field(max_length=64, nullable=False, index=True)
    version_number: int = Field(nullable=False)
    snapshot: dict = Field(sa_column=Column(JSONB, nullable=False))
    change_summary: str = Field(max_length=512, nullable=False)
    rules_added: int = Field(default=0, nullable=False)
    rules_removed: int = Field(default=0, nullable=False)
    rules_modified: int = Field(default=0, nullable=False)
    effective_date: date = Field(sa_column=Column(Date, nullable=False))
    published_by: UUID = Field(foreign_key="users.id", nullable=False)
    published_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class PolicyAuditLog(SQLModel, table=True):
    """Audit trail entry for policy-related actions.

    Records every significant policy operation including rule changes,
    version publications, and cross-tenant access attempts for
    compliance and debugging purposes.
    """

    __tablename__ = "policy_audit_logs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: str = Field(max_length=64, nullable=False, index=True)
    user_id: UUID = Field(foreign_key="users.id", nullable=False)
    action_type: str = Field(max_length=50, nullable=False)
    details: dict = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
