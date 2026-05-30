"""Error handler for the Policy Engine module.

Registers FastAPI exception handlers that map domain-specific
PolicyError exceptions to consistent JSON error responses following
the project's standard format:

    {"detail": {"code": "...", "message": "...", "fields": [...]}}

Authorization errors (403) intentionally do not reveal whether the
requested resource exists, returning a generic denial message.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.modules.policy.domain.exceptions import (
    CrossTenantAccessError,
    CustomRuleLimitError,
    CustomRuleResetError,
    InsufficientRoleError,
    LegalMinimumViolationError,
    PolicyError,
    PolicyRuleNotFoundError,
    PolicySerializationError,
    PolicyValidationError,
    PolicyVersionNotFoundError,
    TemplateInitializationError,
    TemplateRuleDeletionError,
    TenantNotFoundError,
)


def _build_error_response(exc: PolicyError) -> dict:
    """Build the standard error response body for a PolicyError.

    Args:
        exc: The PolicyError instance to convert.

    Returns:
        A dict matching the project's standard error format.
    """
    body: dict = {
        "detail": {
            "code": exc.error_code,
            "message": exc.message,
            "fields": [],
        }
    }

    # Attach field-level errors for validation exceptions
    if isinstance(exc, PolicyValidationError) and exc.fields:
        body["detail"]["fields"] = exc.fields

    # Attach field-level errors for serialization exceptions
    if isinstance(exc, PolicySerializationError) and exc.field_errors:
        body["detail"]["fields"] = exc.field_errors

    return body


def register_policy_error_handlers(app: FastAPI) -> None:
    """Register exception handlers for policy-related errors on the FastAPI app.

    Maps each PolicyError subclass to the appropriate HTTP status code
    and returns a uniform JSON error response. Authorization errors
    (CrossTenantAccessError, InsufficientRoleError) use a generic
    message to avoid revealing resource existence.

    Args:
        app: The FastAPI application instance to register handlers on.

    Error Mapping:
        - TenantNotFoundError → 404
        - PolicyRuleNotFoundError → 404
        - PolicyVersionNotFoundError → 404
        - CrossTenantAccessError → 403
        - InsufficientRoleError → 403
        - PolicyValidationError → 422 (with fields)
        - LegalMinimumViolationError → 422
        - CustomRuleLimitError → 422
        - TemplateRuleDeletionError → 422
        - CustomRuleResetError → 422
        - PolicySerializationError → 500
        - TemplateInitializationError → 500
    """

    @app.exception_handler(CrossTenantAccessError)
    async def _cross_tenant_access_handler(
        request: Request, exc: CrossTenantAccessError
    ) -> JSONResponse:
        """Handle cross-tenant access errors without revealing resource existence."""
        return JSONResponse(
            status_code=403,
            content={
                "detail": {
                    "code": exc.error_code,
                    "message": "Access denied",
                    "fields": [],
                }
            },
        )

    @app.exception_handler(InsufficientRoleError)
    async def _insufficient_role_handler(
        request: Request, exc: InsufficientRoleError
    ) -> JSONResponse:
        """Handle insufficient role errors without revealing resource existence."""
        return JSONResponse(
            status_code=403,
            content={
                "detail": {
                    "code": exc.error_code,
                    "message": "Access denied",
                    "fields": [],
                }
            },
        )

    @app.exception_handler(TenantNotFoundError)
    async def _tenant_not_found_handler(request: Request, exc: TenantNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=_build_error_response(exc),
        )

    @app.exception_handler(PolicyRuleNotFoundError)
    async def _rule_not_found_handler(
        request: Request, exc: PolicyRuleNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=_build_error_response(exc),
        )

    @app.exception_handler(PolicyVersionNotFoundError)
    async def _version_not_found_handler(
        request: Request, exc: PolicyVersionNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=_build_error_response(exc),
        )

    @app.exception_handler(PolicyValidationError)
    async def _validation_error_handler(
        request: Request, exc: PolicyValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_build_error_response(exc),
        )

    @app.exception_handler(LegalMinimumViolationError)
    async def _legal_minimum_handler(
        request: Request, exc: LegalMinimumViolationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_build_error_response(exc),
        )

    @app.exception_handler(CustomRuleLimitError)
    async def _custom_rule_limit_handler(
        request: Request, exc: CustomRuleLimitError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_build_error_response(exc),
        )

    @app.exception_handler(TemplateRuleDeletionError)
    async def _template_deletion_handler(
        request: Request, exc: TemplateRuleDeletionError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_build_error_response(exc),
        )

    @app.exception_handler(CustomRuleResetError)
    async def _custom_rule_reset_handler(
        request: Request, exc: CustomRuleResetError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_build_error_response(exc),
        )

    @app.exception_handler(PolicySerializationError)
    async def _serialization_error_handler(
        request: Request, exc: PolicySerializationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=_build_error_response(exc),
        )

    @app.exception_handler(TemplateInitializationError)
    async def _template_init_handler(
        request: Request, exc: TemplateInitializationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=_build_error_response(exc),
        )

    @app.exception_handler(PolicyError)
    async def _policy_error_fallback(request: Request, exc: PolicyError) -> JSONResponse:
        """Fallback handler for any PolicyError subclass not explicitly handled."""
        return JSONResponse(
            status_code=exc.status_code,
            content=_build_error_response(exc),
        )
