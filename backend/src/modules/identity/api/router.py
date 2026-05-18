"""FastAPI router for the Identity & Auth module.

Defines the /api/auth/* endpoints for Google OAuth2 login, callback,
token refresh, logout, and user profile retrieval.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse

from src.modules.identity.api.schemas import GrantStatusResponse, UserResponse
from src.modules.identity.application.auth_service import AuthService
from src.modules.identity.application.oauth_service import OAuthService
from src.modules.identity.application.token_service import TokenService
from src.modules.identity.domain.entities import User
from src.modules.identity.domain.exceptions import (
    InvalidTokenError,
    RateLimitExceededError,
)
from src.modules.identity.infrastructure.config import AuthSettings
from src.modules.identity.infrastructure.rate_limiter import RateLimiter

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Cookie configuration constants.
_ACCESS_TOKEN_MAX_AGE = 15 * 60  # 15 minutes
_REFRESH_TOKEN_MAX_AGE = 7 * 24 * 60 * 60  # 7 days
_CODE_VERIFIER_MAX_AGE = 10 * 60  # 10 minutes


# ---------------------------------------------------------------------------
# Placeholder dependency functions
# ---------------------------------------------------------------------------
# These will be wired up to real instances via FastAPI's dependency override
# or a proper DI container in a later task.


async def get_auth_service() -> AuthService:
    """Provide the AuthService instance.

    Returns:
        The AuthService singleton for the application.

    Raises:
        NotImplementedError: Placeholder until DI wiring is complete.
    """
    raise NotImplementedError("AuthService dependency not wired")


async def get_token_service() -> TokenService:
    """Provide the TokenService instance.

    Returns:
        The TokenService singleton for the application.

    Raises:
        NotImplementedError: Placeholder until DI wiring is complete.
    """
    raise NotImplementedError("TokenService dependency not wired")


async def get_oauth_service() -> OAuthService:
    """Provide the OAuthService instance.

    Returns:
        The OAuthService singleton for the application.

    Raises:
        NotImplementedError: Placeholder until DI wiring is complete.
    """
    raise NotImplementedError("OAuthService dependency not wired")


async def get_rate_limiter() -> RateLimiter:
    """Provide the RateLimiter instance.

    Returns:
        The RateLimiter singleton for the application.

    Raises:
        NotImplementedError: Placeholder until DI wiring is complete.
    """
    raise NotImplementedError("RateLimiter dependency not wired")


async def get_settings() -> AuthSettings:
    """Provide the AuthSettings instance.

    Returns:
        The AuthSettings loaded from environment variables.

    Raises:
        NotImplementedError: Placeholder until DI wiring is complete.
    """
    raise NotImplementedError("AuthSettings dependency not wired")


async def get_current_user(request: Request) -> User:
    """Extract and validate the current authenticated user from the request.

    Reads the JWT access token from the ``access_token`` cookie, decodes
    and validates it, then looks up the corresponding user.

    Args:
        request: The incoming FastAPI request object.

    Returns:
        The authenticated User entity.

    Raises:
        NotImplementedError: Placeholder until DI wiring is complete.
    """
    raise NotImplementedError("get_current_user dependency not wired")


# ---------------------------------------------------------------------------
# Type aliases for injected dependencies
# ---------------------------------------------------------------------------

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
TokenServiceDep = Annotated[TokenService, Depends(get_token_service)]
OAuthServiceDep = Annotated[OAuthService, Depends(get_oauth_service)]
RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]
SettingsDep = Annotated[AuthSettings, Depends(get_settings)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/login")
async def login(
    request: Request,
    auth_service: AuthServiceDep,
    rate_limiter: RateLimiterDep,
    settings: SettingsDep,
) -> RedirectResponse:
    """Initiate the Google OAuth2 login flow.

    Generates a PKCE code verifier and challenge, creates a signed CSRF
    state token, and redirects the user to Google's consent screen. The
    code_verifier is stored in a short-lived httpOnly cookie for retrieval
    during the callback.

    Args:
        request: The incoming FastAPI request object.
        auth_service: The AuthService for login initiation.
        rate_limiter: The RateLimiter to check request rate.
        settings: Application auth settings.

    Returns:
        A 302 redirect response to Google's OAuth2 authorization URL.

    Raises:
        RateLimitExceededError: If the client IP has exceeded the login
            rate limit.
    """
    client_ip = request.client.host if request.client else "unknown"
    allowed = await rate_limiter.check_rate_limit(client_ip)
    if not allowed:
        raise RateLimitExceededError()

    login_redirect = await auth_service.initiate_login()

    response = RedirectResponse(url=login_redirect.redirect_url, status_code=302)

    # Store code_verifier in a short-lived httpOnly cookie.
    response.set_cookie(
        key="code_verifier",
        value=login_redirect.code_verifier,
        max_age=_CODE_VERIFIER_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="lax",
    )

    return response


@router.get("/callback")
async def callback(
    request: Request,
    code: str,
    state: str,
    auth_service: AuthServiceDep,
    rate_limiter: RateLimiterDep,
    settings: SettingsDep,
) -> RedirectResponse:
    """Handle the Google OAuth2 callback after user consent.

    Validates the CSRF state token, exchanges the authorization code for
    tokens using the stored PKCE code_verifier, sets session cookies, and
    redirects to the frontend application.

    Args:
        request: The incoming FastAPI request object.
        code: The authorization code from Google.
        state: The CSRF state token to validate.
        auth_service: The AuthService for callback handling.
        rate_limiter: The RateLimiter to check request rate.
        settings: Application auth settings.

    Returns:
        A 302 redirect response to the frontend with session cookies set.

    Raises:
        RateLimitExceededError: If the client IP has exceeded the login
            rate limit.
        InvalidStateError: If the CSRF state token is invalid or expired.
        GoogleAuthError: If the token exchange with Google fails.
        AccessDeniedError: If the user's email is not whitelisted.
    """
    client_ip = request.client.host if request.client else "unknown"
    allowed = await rate_limiter.check_rate_limit(client_ip)
    if not allowed:
        raise RateLimitExceededError()

    auth_result = await auth_service.handle_callback(code=code, state=state)

    response = RedirectResponse(url=settings.frontend_url, status_code=302)

    # Set access_token cookie.
    response.set_cookie(
        key="access_token",
        value=auth_result.access_token,
        max_age=_ACCESS_TOKEN_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="lax",
    )

    # Set refresh_token cookie.
    response.set_cookie(
        key="refresh_token",
        value=auth_result.refresh_token,
        max_age=_REFRESH_TOKEN_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="lax",
    )

    # Clear the code_verifier cookie as it's no longer needed.
    response.delete_cookie(key="code_verifier")

    return response


@router.post("/refresh")
async def refresh(
    request: Request,
    token_service: TokenServiceDep,
) -> JSONResponse:
    """Refresh the access token using the refresh token cookie.

    Extracts the refresh_token from the request cookies, validates it,
    and issues a new access_token cookie if the refresh token is valid.

    Args:
        request: The incoming FastAPI request object.
        token_service: The TokenService for token refresh.

    Returns:
        A JSON response with a success message and a new access_token
        cookie set.

    Raises:
        InvalidTokenError: If the refresh token is missing, expired,
            or revoked.
    """
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise InvalidTokenError()

    new_access_token = await token_service.refresh_access_token(refresh_token)

    response = JSONResponse(content={"message": "Token refreshed"})

    response.set_cookie(
        key="access_token",
        value=new_access_token,
        max_age=_ACCESS_TOKEN_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="lax",
    )

    return response


@router.post("/logout")
async def logout(
    request: Request,
    auth_service: AuthServiceDep,
) -> JSONResponse:
    """Revoke the refresh token and clear session cookies.

    Extracts the refresh_token from the request cookies, revokes it
    in the database, and clears both the access_token and refresh_token
    cookies.

    Args:
        request: The incoming FastAPI request object.
        auth_service: The AuthService for logout handling.

    Returns:
        A JSON response confirming logout with cookies cleared.
    """
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        await auth_service.logout(refresh_token)

    response = JSONResponse(content={"message": "Logged out"})

    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")

    return response


@router.get("/me")
async def me(
    current_user: CurrentUserDep,
    oauth_service: OAuthServiceDep,
) -> UserResponse:
    """Get the current authenticated user's profile with grant status.

    Combines the user entity data with the current OAuth grant status
    to provide a complete profile response including Gmail and Calendar
    grant validity.

    Args:
        current_user: The authenticated User entity from the JWT.
        oauth_service: The OAuthService for grant status lookup.

    Returns:
        A UserResponse containing user profile and grant status.
    """
    grant_status = await _get_user_grant_status(current_user, oauth_service)

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        avatar_url=current_user.avatar_url,
        gmail_grant_valid=grant_status.gmail_grant_valid,
        calendar_grant_valid=grant_status.calendar_grant_valid,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
    )


@router.get("/grant-status")
async def grant_status(
    current_user: CurrentUserDep,
    oauth_service: OAuthServiceDep,
) -> GrantStatusResponse:
    """Check the current Gmail and Calendar grant validity.

    Retrieves the user's OAuth grant from the database and determines
    whether the required Gmail and Calendar scopes are still valid.

    Args:
        current_user: The authenticated User entity from the JWT.
        oauth_service: The OAuthService for grant status lookup.

    Returns:
        A GrantStatusResponse indicating grant validity.
    """
    status = await _get_user_grant_status(current_user, oauth_service)

    return GrantStatusResponse(
        gmail_grant_valid=status.gmail_grant_valid,
        calendar_grant_valid=status.calendar_grant_valid,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_user_grant_status(
    user: User, oauth_service: OAuthService
) -> GrantStatusResponse:
    """Retrieve the OAuth grant status for a user.

    Looks up the user's OAuth grant and determines which scopes are
    currently valid. If no grant exists or the grant is marked invalid,
    both gmail and calendar grants are reported as invalid.

    Args:
        user: The User entity to check grants for.
        oauth_service: The OAuthService with grant repository access.

    Returns:
        A GrantStatusResponse with the current grant validity.
    """
    grant = await oauth_service._grant_repository.get_by_user_id(user.id)

    if grant is None or not grant.is_valid:
        return GrantStatusResponse(
            gmail_grant_valid=False,
            calendar_grant_valid=False,
        )

    status = oauth_service.determine_grant_status(grant.scopes)
    return GrantStatusResponse(
        gmail_grant_valid=status.gmail_grant_valid,
        calendar_grant_valid=status.calendar_grant_valid,
    )
