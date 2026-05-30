"""Policy service for the Policy Engine module.

Provides validation logic for PolicyRule definitions and full CRUD
operations for policy rules including creation, update, disable,
and reset with legal minimum enforcement and type validation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from src.modules.policy.domain.entities import PolicyRule
from src.modules.policy.domain.enums import ActionType, PolicyDomain, RuleOperator
from src.modules.policy.domain.exceptions import (
    CustomRuleLimitError,
    CustomRuleResetError,
    LegalMinimumViolationError,
    PolicyRuleNotFoundError,
    PolicyValidationError,
)
from src.modules.policy.infrastructure.policy_repository import PolicyRepository
from src.modules.policy.infrastructure.template_repository import TemplateRepository

if TYPE_CHECKING:
    from src.modules.policy.application.audit_service import PolicyAuditService

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REQUIRED_RULE_FIELDS: list[str] = [
    "rule_id",
    "domain",
    "name",
    "description",
    "rule_condition",
    "rule_action",
    "priority",
    "enabled",
]

_REQUIRED_CONDITION_FIELDS: list[str] = ["field", "operator", "value"]
_REQUIRED_ACTION_FIELDS: list[str] = ["type", "parameters"]

_MAX_RULE_ID_LENGTH: int = 64
_MAX_NAME_LENGTH: int = 128
_MAX_DESCRIPTION_LENGTH: int = 512
_MIN_PRIORITY: int = 1
_MAX_PRIORITY: int = 1000

_SUPPORTED_OPERATORS: set[str] = {op.value for op in RuleOperator}
_SUPPORTED_ACTION_TYPES: set[str] = {at.value for at in ActionType}
_SUPPORTED_DOMAINS: set[str] = {d.value for d in PolicyDomain}


# ---------------------------------------------------------------------------
# Validation Service
# ---------------------------------------------------------------------------


def validate_policy_rule(data: dict[str, Any]) -> None:
    """Validate a PolicyRule definition for structural completeness.

    Checks that all required fields are present, correctly typed, use
    supported enum values, and fall within permitted ranges. Collects
    ALL validation errors before raising.

    Args:
        data: Dictionary representing the PolicyRule to validate.

    Raises:
        PolicyValidationError: If one or more validation errors are found.
            The exception's ``fields`` attribute contains a list of dicts
            with 'field', 'reason', and optionally 'value' keys.
    """
    errors: list[dict[str, Any]] = []

    # --- Required top-level fields ---
    for field_name in _REQUIRED_RULE_FIELDS:
        if field_name not in data:
            errors.append(
                {
                    "field": field_name,
                    "reason": f"Required field '{field_name}' is missing",
                }
            )

    # --- rule_id validation ---
    if "rule_id" in data:
        rule_id = data["rule_id"]
        if not isinstance(rule_id, str):
            errors.append(
                {
                    "field": "rule_id",
                    "reason": "Must be a string",
                    "value": rule_id,
                }
            )
        elif len(rule_id) == 0:
            errors.append(
                {
                    "field": "rule_id",
                    "reason": "Must not be empty",
                    "value": rule_id,
                }
            )
        elif len(rule_id) > _MAX_RULE_ID_LENGTH:
            errors.append(
                {
                    "field": "rule_id",
                    "reason": f"Must not exceed {_MAX_RULE_ID_LENGTH} characters",
                    "value": rule_id,
                }
            )

    # --- domain validation ---
    if "domain" in data:
        domain = data["domain"]
        if not isinstance(domain, str):
            errors.append(
                {
                    "field": "domain",
                    "reason": "Must be a string",
                    "value": domain,
                }
            )
        elif domain not in _SUPPORTED_DOMAINS:
            errors.append(
                {
                    "field": "domain",
                    "reason": (
                        f"Unsupported domain '{domain}'. Supported: {sorted(_SUPPORTED_DOMAINS)}"
                    ),
                    "value": domain,
                }
            )

    # --- name validation ---
    if "name" in data:
        name = data["name"]
        if not isinstance(name, str):
            errors.append(
                {
                    "field": "name",
                    "reason": "Must be a string",
                    "value": name,
                }
            )
        elif len(name) == 0:
            errors.append(
                {
                    "field": "name",
                    "reason": "Must not be empty",
                    "value": name,
                }
            )
        elif len(name) > _MAX_NAME_LENGTH:
            errors.append(
                {
                    "field": "name",
                    "reason": f"Must not exceed {_MAX_NAME_LENGTH} characters",
                    "value": name,
                }
            )

    # --- description validation ---
    if "description" in data:
        description = data["description"]
        if not isinstance(description, str):
            errors.append(
                {
                    "field": "description",
                    "reason": "Must be a string",
                    "value": description,
                }
            )
        elif len(description) > _MAX_DESCRIPTION_LENGTH:
            errors.append(
                {
                    "field": "description",
                    "reason": (f"Must not exceed {_MAX_DESCRIPTION_LENGTH} characters"),
                    "value": description,
                }
            )

    # --- priority validation ---
    if "priority" in data:
        priority = data["priority"]
        if not isinstance(priority, int) or isinstance(priority, bool):
            errors.append(
                {
                    "field": "priority",
                    "reason": "Must be an integer",
                    "value": priority,
                }
            )
        elif priority < _MIN_PRIORITY or priority > _MAX_PRIORITY:
            errors.append(
                {
                    "field": "priority",
                    "reason": (f"Must be between {_MIN_PRIORITY} and {_MAX_PRIORITY} inclusive"),
                    "value": priority,
                }
            )

    # --- enabled validation ---
    if "enabled" in data:
        enabled = data["enabled"]
        if not isinstance(enabled, bool):
            errors.append(
                {
                    "field": "enabled",
                    "reason": "Must be a boolean",
                    "value": enabled,
                }
            )

    # --- rule_condition validation ---
    if "rule_condition" in data:
        condition = data["rule_condition"]
        if not isinstance(condition, dict):
            errors.append(
                {
                    "field": "rule_condition",
                    "reason": "Must be an object",
                    "value": condition,
                }
            )
        else:
            _validate_rule_condition(condition, errors)

    # --- rule_action validation ---
    if "rule_action" in data:
        action = data["rule_action"]
        if not isinstance(action, dict):
            errors.append(
                {
                    "field": "rule_action",
                    "reason": "Must be an object",
                    "value": action,
                }
            )
        else:
            _validate_rule_action(action, errors)

    # --- Raise if any errors collected ---
    if errors:
        raise PolicyValidationError(
            message="Policy rule validation failed",
            fields=errors,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _validate_rule_condition(
    condition: dict[str, Any],
    errors: list[dict[str, Any]],
) -> None:
    """Validate the rule_condition sub-object.

    Checks for required fields (field, operator, value) and validates
    that the operator is a supported RuleOperator value.
    """
    for field_name in _REQUIRED_CONDITION_FIELDS:
        if field_name not in condition:
            errors.append(
                {
                    "field": f"rule_condition.{field_name}",
                    "reason": (f"Required field '{field_name}' is missing from rule_condition"),
                }
            )

    # Validate field is a string
    if "field" in condition:
        field_val = condition["field"]
        if not isinstance(field_val, str):
            errors.append(
                {
                    "field": "rule_condition.field",
                    "reason": "Must be a string",
                    "value": field_val,
                }
            )
        elif len(field_val) == 0:
            errors.append(
                {
                    "field": "rule_condition.field",
                    "reason": "Must not be empty",
                    "value": field_val,
                }
            )

    # Validate operator
    if "operator" in condition:
        operator = condition["operator"]
        if not isinstance(operator, str):
            errors.append(
                {
                    "field": "rule_condition.operator",
                    "reason": "Must be a string",
                    "value": operator,
                }
            )
        elif operator not in _SUPPORTED_OPERATORS:
            errors.append(
                {
                    "field": "rule_condition.operator",
                    "reason": (
                        f"Unsupported operator '{operator}'. "
                        f"Supported: {sorted(_SUPPORTED_OPERATORS)}"
                    ),
                    "value": operator,
                }
            )


def _validate_rule_action(
    action: dict[str, Any],
    errors: list[dict[str, Any]],
) -> None:
    """Validate the rule_action sub-object.

    Checks for required fields (type, parameters) and validates
    that the type is a supported ActionType value and parameters
    is a dict.
    """
    for field_name in _REQUIRED_ACTION_FIELDS:
        if field_name not in action:
            errors.append(
                {
                    "field": f"rule_action.{field_name}",
                    "reason": (f"Required field '{field_name}' is missing from rule_action"),
                }
            )

    # Validate type
    if "type" in action:
        action_type = action["type"]
        if not isinstance(action_type, str):
            errors.append(
                {
                    "field": "rule_action.type",
                    "reason": "Must be a string",
                    "value": action_type,
                }
            )
        elif action_type not in _SUPPORTED_ACTION_TYPES:
            errors.append(
                {
                    "field": "rule_action.type",
                    "reason": (
                        f"Unsupported action type '{action_type}'. "
                        f"Supported: {sorted(_SUPPORTED_ACTION_TYPES)}"
                    ),
                    "value": action_type,
                }
            )

    # Validate parameters
    if "parameters" in action:
        parameters = action["parameters"]
        if not isinstance(parameters, dict):
            errors.append(
                {
                    "field": "rule_action.parameters",
                    "reason": "Must be an object (dict)",
                    "value": parameters,
                }
            )


# ---------------------------------------------------------------------------
# Constants for CRUD operations
# ---------------------------------------------------------------------------

_MAX_CUSTOM_RULES_PER_TENANT: int = 500

# Fields that can be updated on a policy rule
_UPDATABLE_FIELDS: set[str] = {
    "name",
    "description",
    "rule_condition",
    "rule_action",
    "priority",
    "enabled",
}


# ---------------------------------------------------------------------------
# Policy CRUD Service
# ---------------------------------------------------------------------------


class PolicyService:
    """Service for managing policy rule CRUD operations.

    Handles creation, update, disable, and reset of policy rules
    with enforcement of legal minimums, type validation, and
    custom rule limits.

    Attributes:
        policy_repo: Repository for PolicyRule persistence.
        template_repo: Repository for PolicyTemplate retrieval.
        audit_service: Optional audit logging service.
    """

    def __init__(
        self,
        policy_repo: PolicyRepository,
        template_repo: TemplateRepository,
        audit_service: PolicyAuditService | None = None,
    ) -> None:
        """Initialize PolicyService with required repositories.

        Args:
            policy_repo: Repository for PolicyRule CRUD operations.
            template_repo: Repository for PolicyTemplate read-only queries.
            audit_service: Optional audit logging service for CRUD operations.
        """
        self.policy_repo = policy_repo
        self.template_repo = template_repo
        self._audit_service = audit_service

    async def create_custom_rule(
        self,
        tenant_id: str,
        rule_data: dict[str, Any],
        user_id: UUID,
    ) -> PolicyRule:
        """Create a new custom policy rule for a tenant.

        Validates the rule structure, enforces the 500 custom rule limit,
        and persists the rule with is_custom=True.

        Args:
            tenant_id: The tenant identifier.
            rule_data: Dictionary containing the rule definition fields.
            user_id: The UUID of the user creating the rule.

        Returns:
            The created PolicyRule entity.

        Raises:
            CustomRuleLimitError: If the tenant has reached 500 custom rules.
            PolicyValidationError: If the rule data fails validation.
        """
        # Validate rule structure
        validate_policy_rule(rule_data)

        # Enforce custom rule limit
        current_count = await self.policy_repo.count_custom_rules(tenant_id)
        if current_count >= _MAX_CUSTOM_RULES_PER_TENANT:
            raise CustomRuleLimitError()

        # Create the PolicyRule entity
        rule = PolicyRule(
            tenant_id=tenant_id,
            domain=PolicyDomain(rule_data["domain"]),
            rule_id=rule_data["rule_id"],
            name=rule_data["name"],
            description=rule_data["description"],
            rule_condition=rule_data["rule_condition"],
            rule_action=rule_data["rule_action"],
            priority=rule_data["priority"],
            enabled=rule_data["enabled"],
            template_rule_id=None,
            is_custom=True,
            is_deleted=False,
            created_by=user_id,
        )

        created_rule = await self.policy_repo.create_rule(rule)

        # Audit log: rule created
        if self._audit_service:
            await self._audit_service.log_rule_created(
                tenant_id=tenant_id,
                user_id=user_id,
                rule_id=rule_data["rule_id"],
                domain=rule_data["domain"],
                rule_name=rule_data["name"],
            )

        return created_rule

    async def update_rule(
        self,
        tenant_id: str,
        rule_id: str,
        updates: dict[str, Any],
        user_id: UUID,
    ) -> PolicyRule:
        """Update an existing policy rule.

        For template-based rules, updates the tenant's copy of the rule
        (which was created during template provisioning). For custom rules,
        performs a direct update. Enforces legal minimum constraints and
        type validation on value changes.

        Args:
            tenant_id: The tenant identifier.
            rule_id: The rule identifier to update.
            updates: Dictionary of field names to new values.
            user_id: The UUID of the user performing the update.

        Returns:
            The updated PolicyRule entity.

        Raises:
            PolicyRuleNotFoundError: If the rule does not exist for the tenant.
            LegalMinimumViolationError: If an update violates legal minimums.
            PolicyValidationError: If update values fail type validation.
        """
        # Retrieve the existing rule
        rule = await self.policy_repo.get_rule(tenant_id, rule_id)
        if rule is None:
            raise PolicyRuleNotFoundError()

        # Filter to only updatable fields
        filtered_updates: dict[str, Any] = {
            k: v for k, v in updates.items() if k in _UPDATABLE_FIELDS
        }

        if not filtered_updates:
            return rule

        # Validate types of update values
        self._validate_update_types(filtered_updates)

        # For template-based rules, enforce legal minimum constraints
        if rule.template_rule_id is not None:
            await self._enforce_legal_minimums(rule.template_rule_id, filtered_updates)

        # Perform the update
        updated_rule = await self.policy_repo.update_rule(
            tenant_id, rule_id, filtered_updates
        )
        if updated_rule is None:
            raise PolicyRuleNotFoundError()

        # Audit log: rule updated
        if self._audit_service:
            await self._audit_service.log_rule_updated(
                tenant_id=tenant_id,
                user_id=user_id,
                rule_id=rule_id,
                changes=filtered_updates,
            )

        return updated_rule

    async def disable_rule(
        self,
        tenant_id: str,
        rule_id: str,
        user_id: UUID | None = None,
    ) -> PolicyRule:
        """Disable a policy rule.

        For custom rules, performs a soft delete (is_deleted=True).
        For template-based rules, sets enabled=False.

        Args:
            tenant_id: The tenant identifier.
            rule_id: The rule identifier to disable.
            user_id: Optional UUID of the user performing the action.

        Returns:
            The updated PolicyRule entity.

        Raises:
            PolicyRuleNotFoundError: If the rule does not exist for the tenant.
        """
        rule = await self.policy_repo.get_rule(tenant_id, rule_id)
        if rule is None:
            raise PolicyRuleNotFoundError()

        if rule.is_custom:
            # Soft delete for custom rules
            deleted_rule = await self.policy_repo.soft_delete_rule(tenant_id, rule_id)
            if deleted_rule is None:
                raise PolicyRuleNotFoundError()
            result = deleted_rule
        else:
            # Set enabled=False for template-based rules
            updated_rule = await self.policy_repo.update_rule(
                tenant_id, rule_id, {"enabled": False}
            )
            if updated_rule is None:
                raise PolicyRuleNotFoundError()
            result = updated_rule

        # Audit log: rule disabled
        if self._audit_service and user_id:
            await self._audit_service.log_rule_disabled(
                tenant_id=tenant_id,
                user_id=user_id,
                rule_id=rule_id,
                is_custom=rule.is_custom,
            )

        return result

    async def reset_override(
        self,
        tenant_id: str,
        rule_id: str,
        user_id: UUID | None = None,
    ) -> PolicyRule:
        """Reset a template-based rule to its original template default values.

        Restores the rule's fields from the associated PolicyTemplate.
        Rejects the operation for custom rules that have no template.

        Args:
            tenant_id: The tenant identifier.
            rule_id: The rule identifier to reset.
            user_id: Optional UUID of the user performing the action.

        Returns:
            The reset PolicyRule entity with template default values.

        Raises:
            PolicyRuleNotFoundError: If the rule does not exist for the tenant.
            CustomRuleResetError: If the rule is a custom rule with no template.
        """
        rule = await self.policy_repo.get_rule(tenant_id, rule_id)
        if rule is None:
            raise PolicyRuleNotFoundError()

        if rule.is_custom:
            raise CustomRuleResetError()

        if rule.template_rule_id is None:
            raise CustomRuleResetError()

        # Retrieve the original template
        template = await self.template_repo.get_template_by_uuid(rule.template_rule_id)
        if template is None:
            raise PolicyRuleNotFoundError(
                message="Associated policy template not found"
            )

        # Restore template default values
        reset_data: dict[str, Any] = {
            "name": template.name,
            "description": template.description,
            "rule_condition": template.rule_condition,
            "rule_action": template.rule_action,
            "priority": template.priority,
            "enabled": template.enabled,
        }

        updated_rule = await self.policy_repo.update_rule(
            tenant_id, rule_id, reset_data
        )
        if updated_rule is None:
            raise PolicyRuleNotFoundError()

        # Audit log: rule reset
        if self._audit_service and user_id:
            await self._audit_service.log_rule_reset(
                tenant_id=tenant_id,
                user_id=user_id,
                rule_id=rule_id,
            )

        return updated_rule

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _validate_update_types(self, updates: dict[str, Any]) -> None:
        """Validate that update values match expected types.

        Args:
            updates: Dictionary of field names to new values.

        Raises:
            PolicyValidationError: If any value has an incorrect type.
        """
        errors: list[dict[str, Any]] = []

        if "name" in updates:
            if not isinstance(updates["name"], str):
                errors.append({
                    "field": "name",
                    "reason": "Must be a string",
                    "value": updates["name"],
                })
            elif len(updates["name"]) == 0:
                errors.append({
                    "field": "name",
                    "reason": "Must not be empty",
                    "value": updates["name"],
                })
            elif len(updates["name"]) > _MAX_NAME_LENGTH:
                errors.append({
                    "field": "name",
                    "reason": f"Must not exceed {_MAX_NAME_LENGTH} characters",
                    "value": updates["name"],
                })

        if "description" in updates:
            if not isinstance(updates["description"], str):
                errors.append({
                    "field": "description",
                    "reason": "Must be a string",
                    "value": updates["description"],
                })
            elif len(updates["description"]) > _MAX_DESCRIPTION_LENGTH:
                errors.append({
                    "field": "description",
                    "reason": (
                        f"Must not exceed {_MAX_DESCRIPTION_LENGTH} characters"
                    ),
                    "value": updates["description"],
                })

        if "priority" in updates:
            priority = updates["priority"]
            if not isinstance(priority, int) or isinstance(priority, bool):
                errors.append({
                    "field": "priority",
                    "reason": "Must be an integer",
                    "value": priority,
                })
            elif priority < _MIN_PRIORITY or priority > _MAX_PRIORITY:
                errors.append({
                    "field": "priority",
                    "reason": (
                        f"Must be between {_MIN_PRIORITY} and "
                        f"{_MAX_PRIORITY} inclusive"
                    ),
                    "value": priority,
                })

        if "enabled" in updates:
            if not isinstance(updates["enabled"], bool):
                errors.append({
                    "field": "enabled",
                    "reason": "Must be a boolean",
                    "value": updates["enabled"],
                })

        if "rule_condition" in updates:
            if not isinstance(updates["rule_condition"], dict):
                errors.append({
                    "field": "rule_condition",
                    "reason": "Must be an object",
                    "value": updates["rule_condition"],
                })

        if "rule_action" in updates:
            if not isinstance(updates["rule_action"], dict):
                errors.append({
                    "field": "rule_action",
                    "reason": "Must be an object",
                    "value": updates["rule_action"],
                })

        if errors:
            raise PolicyValidationError(
                message="Update validation failed",
                fields=errors,
            )

    async def _enforce_legal_minimums(
        self,
        template_rule_id: UUID,
        updates: dict[str, Any],
    ) -> None:
        """Enforce legal minimum constraints from the template.

        Checks the template's legal_constraints and ensures that
        any numeric values in the update do not fall below the
        legally mandated minimums.

        Args:
            template_rule_id: UUID of the associated template.
            updates: Dictionary of field names to new values.

        Raises:
            LegalMinimumViolationError: If a value is below the legal minimum.
        """
        template = await self.template_repo.get_template_by_uuid(template_rule_id)
        if template is None or template.legal_constraints is None:
            return

        legal_constraints = template.legal_constraints

        # Check rule_action parameters for legal minimums
        if "rule_action" in updates and isinstance(updates["rule_action"], dict):
            action_params = updates["rule_action"].get("parameters", {})
            if isinstance(action_params, dict):
                self._check_params_against_constraints(
                    action_params, legal_constraints
                )

        # Check rule_condition value for legal minimums
        if "rule_condition" in updates and isinstance(updates["rule_condition"], dict):
            condition_value = updates["rule_condition"].get("value")
            if condition_value is not None and "min_value" in legal_constraints:
                min_val = legal_constraints["min_value"]
                if (
                    isinstance(condition_value, (int, float))
                    and isinstance(min_val, (int, float))
                    and condition_value < min_val
                ):
                    raise LegalMinimumViolationError(
                        message=(
                            f"Value {condition_value} is below the legally "
                            f"mandated minimum of {min_val}"
                        )
                    )

    def _check_params_against_constraints(
        self,
        params: dict[str, Any],
        legal_constraints: dict[str, Any],
    ) -> None:
        """Check action parameters against legal constraint minimums.

        Args:
            params: The action parameters to validate.
            legal_constraints: The legal constraints from the template.

        Raises:
            LegalMinimumViolationError: If a parameter is below its minimum.
        """
        # Check for minimum values defined in legal_constraints
        min_values = legal_constraints.get("min_values", {})
        if isinstance(min_values, dict):
            for param_key, min_val in min_values.items():
                if param_key in params:
                    param_val = params[param_key]
                    if (
                        isinstance(param_val, (int, float))
                        and isinstance(min_val, (int, float))
                        and param_val < min_val
                    ):
                        raise LegalMinimumViolationError(
                            message=(
                                f"Parameter '{param_key}' value {param_val} "
                                f"is below the legally mandated minimum "
                                f"of {min_val}"
                            )
                        )

        # Check top-level min_value constraint
        if "min_value" in legal_constraints:
            min_val = legal_constraints["min_value"]
            # Check common parameter names for threshold values
            for key in ("multiplier", "threshold", "value", "rate"):
                if key in params:
                    param_val = params[key]
                    if (
                        isinstance(param_val, (int, float))
                        and isinstance(min_val, (int, float))
                        and param_val < min_val
                    ):
                        raise LegalMinimumViolationError(
                            message=(
                                f"Parameter '{key}' value {param_val} is "
                                f"below the legally mandated minimum "
                                f"of {min_val}"
                            )
                        )
