"""Domain exceptions for the Policy Engine module.

Defines the exception hierarchy used throughout the policy engine
to represent validation failures, access control violations, and
operational errors.
"""


class PolicyError(Exception):
    """Base exception for the policy engine module.

    All domain-specific exceptions inherit from this class, enabling
    a single exception handler to catch any policy-related error and
    return a consistent JSON error response.

    Attributes:
        status_code: HTTP status code to return to the client.
        error_code: Machine-readable error identifier.
        message: Human-readable error description.
    """

    status_code: int = 500
    error_code: str = "POLICY_ERROR"
    message: str = "A policy engine error occurred"

    def __init__(self, message: str | None = None) -> None:
        """Initialize PolicyError.

        Args:
            message: Optional custom message override. If not provided,
                the class-level default message is used.
        """
        if message is not None:
            self.message = message
        super().__init__(self.message)


class TenantNotFoundError(PolicyError):
    """Tenant identifier does not exist in the system.

    Raised when a request references a tenant_id that cannot be
    found in the database.
    """

    status_code = 404
    error_code = "TENANT_NOT_FOUND"
    message = "Tenant not found"


class PolicyRuleNotFoundError(PolicyError):
    """Policy rule does not exist or does not belong to the tenant.

    Raised when a rule_id cannot be found within the scope of the
    requesting tenant.
    """

    status_code = 404
    error_code = "POLICY_RULE_NOT_FOUND"
    message = "Policy rule not found"


class CrossTenantAccessError(PolicyError):
    """Attempt to access another tenant's resources.

    Raised when a request authenticated as one tenant tries to
    read, modify, or delete resources belonging to a different tenant.
    """

    status_code = 403
    error_code = "CROSS_TENANT_ACCESS"
    message = "Access to another tenant's resources is denied"


class InsufficientRoleError(PolicyError):
    """User lacks the required admin role.

    Raised when a user without the admin role attempts to access
    policy management endpoints.
    """

    status_code = 403
    error_code = "INSUFFICIENT_ROLE"
    message = "Admin role required for this operation"


class PolicyValidationError(PolicyError):
    """Policy rule definition fails validation.

    Raised when a rule is missing required fields, contains
    unsupported operator or action type values, or has fields
    outside permitted ranges.

    Attributes:
        fields: List of field-level validation errors.
    """

    status_code = 422
    error_code = "POLICY_VALIDATION_ERROR"
    message = "Policy rule validation failed"

    def __init__(
        self,
        message: str | None = None,
        fields: list[dict[str, str]] | None = None,
    ) -> None:
        """Initialize PolicyValidationError.

        Args:
            message: Optional custom message override.
            fields: Optional list of field-level error details, each
                containing 'field', 'reason', and optionally 'value'.
        """
        super().__init__(message)
        self.fields: list[dict[str, str]] = fields or []


class LegalMinimumViolationError(PolicyError):
    """Override value falls below a legally mandated minimum.

    Raised when a tenant attempts to set a rule value below the
    legal minimum defined in the policy template's legal_constraints.
    """

    status_code = 422
    error_code = "LEGAL_MINIMUM_VIOLATION"
    message = "Value is below the legally mandated minimum"


class CustomRuleLimitError(PolicyError):
    """Tenant has reached the maximum number of custom rules.

    Raised when a tenant attempts to create a new custom rule but
    has already reached the configured limit (default 500).
    """

    status_code = 422
    error_code = "CUSTOM_RULE_LIMIT"
    message = "Maximum number of custom rules reached (500)"


class TemplateRuleDeletionError(PolicyError):
    """Attempt to delete a template-based rule.

    Raised when a DELETE request targets a rule derived from a
    template. Template rules can only be disabled, not deleted.
    """

    status_code = 422
    error_code = "TEMPLATE_RULE_DELETION"
    message = "Template-based rules cannot be deleted; disable them instead"


class CustomRuleResetError(PolicyError):
    """Attempt to reset a custom rule to template default.

    Raised when a reset operation targets a custom rule that has
    no associated template default to revert to.
    """

    status_code = 422
    error_code = "CUSTOM_RULE_RESET"
    message = "Custom rules cannot be reset to template default; delete them instead"


class PolicySerializationError(PolicyError):
    """Serialization or parsing failure.

    Raised when a policy rule cannot be serialized to JSON or
    when a JSON string cannot be parsed into a valid PolicyRule.

    Attributes:
        position: Character position where the syntax failure was
            detected (for malformed JSON).
        field_errors: List of field-level schema violations.
    """

    status_code = 500
    error_code = "POLICY_SERIALIZATION_ERROR"
    message = "Policy rule serialization/parsing failed"

    def __init__(
        self,
        message: str | None = None,
        position: int | None = None,
        field_errors: list[dict[str, str]] | None = None,
    ) -> None:
        """Initialize PolicySerializationError.

        Args:
            message: Optional custom message override.
            position: Character position of syntax failure.
            field_errors: List of field-level schema violations.
        """
        super().__init__(message)
        self.position: int | None = position
        self.field_errors: list[dict[str, str]] = field_errors or []


class PolicyVersionNotFoundError(PolicyError):
    """Policy version does not exist.

    Raised when a requested version number cannot be found for
    the given tenant.
    """

    status_code = 404
    error_code = "POLICY_VERSION_NOT_FOUND"
    message = "Policy version not found"


class TemplateInitializationError(PolicyError):
    """Template assignment failed during tenant registration.

    Raised when the automatic provisioning of default policy
    templates for a new tenant fails.
    """

    status_code = 500
    error_code = "TEMPLATE_INITIALIZATION_ERROR"
    message = "Failed to initialize policy templates for tenant"
