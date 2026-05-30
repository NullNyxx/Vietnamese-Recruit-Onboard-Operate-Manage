"""FastAPI router for policy evaluation endpoint.

Defines the POST /api/policies/evaluate endpoint that allows any
authenticated module or service to request policy decisions from
the engine. Validates inputs, evaluates rules, and logs every
request for audit purposes.
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends

from src.modules.policy.api.schemas import (
    EvaluationResultSchema,
    MatchedRuleSchema,
    PolicyEvaluateRequest,
    PolicyEvaluateResponse,
    TriggeredActionSchema,
)
from src.modules.policy.application.evaluation_service import EvaluationService
from src.modules.policy.container import (
    AuthenticatedUserDep,
    get_evaluation_service,
)
from src.modules.policy.domain.enums import ActionType

logger = logging.getLogger(__name__)

evaluation_router = APIRouter(prefix="/api/policies", tags=["policy-evaluation"])


@evaluation_router.post("/evaluate", response_model=PolicyEvaluateResponse)
async def evaluate_policy(
    body: PolicyEvaluateRequest,
    current_user: AuthenticatedUserDep,
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> PolicyEvaluateResponse:
    """Evaluate policy rules against the provided context.

    Accepts a Policy_Evaluation_Context payload and returns matched rules,
    evaluation results (pass/fail per rule), and triggered actions.
    The endpoint targets a 500ms response time.

    Validation:
    - Required fields (tenant_id, domain, event_type) are enforced by
      the Pydantic schema.
    - Domain must be one of the supported PolicyDomains (enforced by enum).
    - Authenticated caller is verified via the AuthenticatedUserDep dependency.

    Every evaluation request is logged for audit purposes.

    Args:
        body: The evaluation request payload with tenant_id, domain,
            event_type, context, and optional evaluation_date.
        current_user: The authenticated user making the request.
        evaluation_service: The EvaluationService for rule evaluation.

    Returns:
        A PolicyEvaluateResponse with matched rules, evaluation results,
        and triggered actions.

    Raises:
        TenantNotFoundError: If the tenant_id does not exist (404).
        PolicyValidationError: If the request fails validation (422).
    """
    start_time = time.monotonic()

    result = await evaluation_service.evaluate(
        tenant_id=body.tenant_id,
        domain=body.domain,
        event_type=body.event_type,
        context=body.context,
        evaluation_date=body.evaluation_date,
        user_id=current_user.id,
    )

    elapsed_ms = (time.monotonic() - start_time) * 1000

    if elapsed_ms > 500:
        logger.warning(
            "Policy evaluation exceeded 500ms target: %.1fms (tenant=%s, domain=%s, event_type=%s)",
            elapsed_ms,
            body.tenant_id,
            body.domain.value,
            body.event_type,
        )

    # Build response from EvaluationResult dataclass
    matched_rules: list[MatchedRuleSchema] = []
    triggered_actions: list[TriggeredActionSchema] = []

    for i, match in enumerate(result.matched_rules):
        # Find the priority from evaluation_results or use index-based lookup
        priority = 0
        for detail in result.evaluation_results:
            if detail.rule_id == match.rule_id and detail.passed:
                # Priority isn't stored in RuleMatch, derive from position
                priority = i + 1
                break

        matched_rules.append(
            MatchedRuleSchema(
                rule_id=match.rule_id,
                name=match.name,
                priority=priority,
            )
        )

    # triggered_actions is a list of action dicts from the evaluation service
    for i, action_dict in enumerate(result.triggered_actions):
        # Each action_dict has "type" and "parameters" keys
        action_type_val = action_dict.get("type", "flag")
        parameters = action_dict.get("parameters", {})

        # Determine the rule_id for this action (matched_rules and
        # triggered_actions are in the same order)
        action_rule_id = result.matched_rules[i].rule_id if i < len(result.matched_rules) else ""

        triggered_actions.append(
            TriggeredActionSchema(
                rule_id=action_rule_id,
                action_type=ActionType(action_type_val)
                if isinstance(action_type_val, str)
                else action_type_val,
                parameters=parameters,
            )
        )

    evaluation_results = [
        EvaluationResultSchema(
            rule_id=detail.rule_id,
            passed=detail.passed,
            condition=detail.condition,
        )
        for detail in result.evaluation_results
    ]

    return PolicyEvaluateResponse(
        matched_rules=matched_rules,
        evaluation_results=evaluation_results,
        triggered_actions=triggered_actions,
    )
