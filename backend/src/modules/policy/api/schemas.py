"""Pydantic request/response schemas for the Policy Engine API.

Defines data transfer objects for policy rule CRUD, evaluation,
versioning, and diff endpoints.
"""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.modules.policy.domain.enums import ActionType, PolicyDomain, RuleOperator

# ---------------------------------------------------------------------------
# Shared / Nested Models
# ---------------------------------------------------------------------------


class RuleConditionSchema(BaseModel):
    """Schema for a rule condition in request/response payloads.

    Attributes:
        field: The context attribute to evaluate.
        operator: The comparison operator.
        value: The comparison operand.
    """

    field: str = Field(..., min_length=1, max_length=128)
    operator: RuleOperator
    value: Any


class RuleActionSchema(BaseModel):
    """Schema for a rule action in request/response payloads.

    Attributes:
        type: The action category.
        parameters: Action-specific configuration data.
    """

    type: ActionType
    parameters: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Policy Rule CRUD Schemas
# ---------------------------------------------------------------------------


class PolicyRuleCreateRequest(BaseModel):
    """Request schema for POST /api/policies/rules.

    Creates a new custom policy rule for the authenticated tenant.

    Attributes:
        domain: The policy domain this rule belongs to.
        rule_id: Unique rule identifier within the tenant (max 64 chars).
        name: Human-readable rule name (max 128 chars).
        description: Rule description (max 512 chars).
        rule_condition: The conditional expression for this rule.
        rule_action: The action triggered when the condition is met.
        priority: Evaluation priority (1-1000, lower = evaluated first).
        enabled: Whether the rule is active.
    """

    domain: PolicyDomain
    rule_id: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=128)
    description: str = Field(..., min_length=1, max_length=512)
    rule_condition: RuleConditionSchema
    rule_action: RuleActionSchema
    priority: int = Field(..., ge=1, le=1000)
    enabled: bool = Field(default=True)


class PolicyRuleUpdateRequest(BaseModel):
    """Request schema for PUT /api/policies/rules/{rule_id}.

    Updates an existing rule or creates an override for a template rule.
    All fields are optional — only provided fields are updated.

    Attributes:
        name: Updated rule name.
        description: Updated description.
        rule_condition: Updated condition.
        rule_action: Updated action.
        priority: Updated priority.
        enabled: Updated enabled status.
    """

    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, min_length=1, max_length=512)
    rule_condition: RuleConditionSchema | None = None
    rule_action: RuleActionSchema | None = None
    priority: int | None = Field(default=None, ge=1, le=1000)
    enabled: bool | None = None


class PolicyRuleResponse(BaseModel):
    """Response schema for a single policy rule.

    Attributes:
        id: The rule's unique database identifier.
        tenant_id: The owning tenant identifier.
        domain: The policy domain.
        rule_id: The rule's string identifier.
        name: Human-readable name.
        description: Rule description.
        rule_condition: The rule's condition.
        rule_action: The rule's action.
        priority: Evaluation priority.
        enabled: Whether the rule is active.
        template_rule_id: Source template ID if derived from a template.
        is_custom: Whether this is a custom (non-template) rule.
        is_deleted: Whether the rule has been soft-deleted.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
        created_by: ID of the user who created the rule.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: str
    domain: PolicyDomain
    rule_id: str
    name: str
    description: str
    rule_condition: dict[str, Any]
    rule_action: dict[str, Any]
    priority: int
    enabled: bool
    template_rule_id: UUID | None = None
    is_custom: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    created_by: UUID


# ---------------------------------------------------------------------------
# Policy Evaluation Schemas
# ---------------------------------------------------------------------------


_MAX_CONTEXT_SIZE = 1_048_576  # 1 MB


class PolicyEvaluateRequest(BaseModel):
    """Request schema for POST /api/policies/evaluate.

    Attributes:
        tenant_id: The tenant to evaluate rules for (max 64 chars).
        domain: The policy domain to evaluate.
        event_type: The type of event triggering evaluation (max 128 chars).
        context: Arbitrary context data for rule evaluation (max 1MB).
        evaluation_date: Optional date for version resolution (defaults to today).
    """

    tenant_id: str = Field(..., min_length=1, max_length=64)
    domain: PolicyDomain
    event_type: str = Field(..., min_length=1, max_length=128)
    context: dict[str, Any] = Field(default_factory=dict)
    evaluation_date: date | None = None

    @field_validator("context")
    @classmethod
    def validate_context_size(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Ensure context payload does not exceed 1MB when serialized."""
        import json

        serialized = json.dumps(v, default=str)
        if len(serialized.encode("utf-8")) > _MAX_CONTEXT_SIZE:
            msg = "Context payload exceeds maximum size of 1MB"
            raise ValueError(msg)
        return v


class MatchedRuleSchema(BaseModel):
    """A rule that matched during evaluation.

    Attributes:
        rule_id: The rule's string identifier.
        name: Human-readable rule name.
        priority: The rule's priority value.
    """

    rule_id: str
    name: str
    priority: int


class EvaluationResultSchema(BaseModel):
    """Evaluation result for a single rule.

    Attributes:
        rule_id: The rule's string identifier.
        passed: Whether the rule condition was satisfied.
        condition: The evaluated condition details.
    """

    rule_id: str
    passed: bool
    condition: dict[str, Any]


class TriggeredActionSchema(BaseModel):
    """An action triggered by a matched rule.

    Attributes:
        rule_id: The rule that triggered this action.
        action_type: The type of action triggered.
        parameters: Action-specific parameters.
    """

    rule_id: str
    action_type: ActionType
    parameters: dict[str, Any]


class PolicyEvaluateResponse(BaseModel):
    """Response schema for POST /api/policies/evaluate.

    Attributes:
        matched_rules: List of rules that matched the context.
        evaluation_results: Pass/fail result per evaluated rule.
        triggered_actions: Actions triggered by matched rules.
    """

    matched_rules: list[MatchedRuleSchema]
    evaluation_results: list[EvaluationResultSchema]
    triggered_actions: list[TriggeredActionSchema]


# ---------------------------------------------------------------------------
# Policy Version Schemas
# ---------------------------------------------------------------------------


class PolicyVersionResponse(BaseModel):
    """Response schema for a single policy version.

    Attributes:
        id: The version's unique database identifier.
        tenant_id: The owning tenant identifier.
        version_number: Monotonically increasing version number.
        change_summary: Human-readable summary of changes.
        rules_added: Count of rules added in this version.
        rules_removed: Count of rules removed in this version.
        rules_modified: Count of rules modified in this version.
        effective_date: Date from which this version is active.
        published_by: ID of the user who published.
        published_at: Publication timestamp.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: str
    version_number: int
    change_summary: str
    rules_added: int
    rules_removed: int
    rules_modified: int
    effective_date: date
    published_by: UUID
    published_at: datetime


class PolicyVersionListResponse(BaseModel):
    """Paginated response for GET /api/policies/versions.

    Attributes:
        items: List of policy versions for the current page.
        total: Total number of versions available.
        page: Current page number (1-indexed).
        page_size: Number of items per page.
    """

    items: list[PolicyVersionResponse]
    total: int
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)


# ---------------------------------------------------------------------------
# Policy Diff Schemas
# ---------------------------------------------------------------------------


class RuleDiffEntry(BaseModel):
    """A single rule entry in a version diff.

    Attributes:
        rule_id: The rule's string identifier.
        name: Human-readable rule name.
        details: Optional change details (old/new values for modified rules).
    """

    rule_id: str
    name: str
    details: dict[str, Any] | None = None


class PolicyDiffResponse(BaseModel):
    """Response schema for version diff endpoint.

    Attributes:
        version_a: The first version number in the comparison.
        version_b: The second version number in the comparison.
        rules_added: Rules present in version_b but not version_a.
        rules_removed: Rules present in version_a but not version_b.
        rules_modified: Rules present in both but with different values.
        rules_unchanged: Rules identical in both versions.
    """

    version_a: int
    version_b: int
    rules_added: list[RuleDiffEntry]
    rules_removed: list[RuleDiffEntry]
    rules_modified: list[RuleDiffEntry]
    rules_unchanged: list[RuleDiffEntry]


# ---------------------------------------------------------------------------
# Publish Schemas
# ---------------------------------------------------------------------------


class PublishRequest(BaseModel):
    """Request schema for POST /api/policies/publish.

    Attributes:
        effective_date: Date from which the new version becomes active.
            Defaults to today if not provided.
        change_summary: Human-readable summary of changes (max 512 chars).
    """

    effective_date: date | None = None
    change_summary: str = Field(..., min_length=1, max_length=512)
