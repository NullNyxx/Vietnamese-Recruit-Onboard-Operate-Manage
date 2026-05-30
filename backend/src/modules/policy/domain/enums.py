"""Domain enumerations for the Policy Engine module.

Defines the enums used across the policy engine for categorizing
policy domains, rule condition operators, and action types.
"""

from enum import Enum


class PolicyDomain(str, Enum):
    """Policy domain categories grouping related rules.

    Each domain represents a distinct area of HR policy enforcement:
    attendance tracking, leave management, overtime control, and
    disciplinary actions.
    """

    ATTENDANCE = "attendance"
    LEAVE = "leave"
    OVERTIME = "overtime"
    DISCIPLINARY = "disciplinary"


class RuleOperator(str, Enum):
    """Supported operators for rule condition evaluation.

    These operators define how a field value in the evaluation context
    is compared against the rule's configured threshold or value set.
    """

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    IN_LIST = "in_list"
    NOT_IN_LIST = "not_in_list"
    BETWEEN = "between"
    IS_NULL = "is_null"


class ActionType(str, Enum):
    """Supported action types triggered when a rule condition is met.

    Each action type defines a category of response the engine can
    produce when a rule matches the evaluation context.
    """

    FLAG = "flag"
    NOTIFY = "notify"
    CALCULATE = "calculate"
    RESTRICT = "restrict"
    ESCALATE = "escalate"
