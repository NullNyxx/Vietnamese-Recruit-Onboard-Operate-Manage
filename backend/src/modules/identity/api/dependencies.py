"""FastAPI dependencies for the Identity & Auth module.

Provides dependency injection functions for extracting and validating
the current authenticated user from incoming requests.
"""

from fastapi import HTTPException, Request

from src.modules.identity.application.token_service import TokenService
from src.modules.identity.domain.entities import User
from src.modules.identity.domain.exceptions import InvalidTokenError
from src.modules.identity.infrastructure.user_repository import UserRepository


async def get_current_user(
    request: Request,
    token_service: TokenService,
    user_repository: UserRepository,
) -> User:
    """Extract and validate the current authenticated user from the request.

    Reads the JWT access token from the ``access_token`` cookie, decodes
    and validates it using the TokenService, then looks up the corresponding
    user in the database via UserRepository.

    This function is designed to be used as a FastAPI dependency with
    ``Depends(get_current_user)``.

    Args:
        request: The incoming FastAPI request object.
        token_service: Service for JWT token verification.
        user_repository: Repository for user lookup by ID.

    Returns:
        The authenticated User entity.

    Raises:
        HTTPException: 401 Unauthorized if the token is missing, invalid,
            expired, or the user cannot be found.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    try:
        payload = token_service.verify_access_token(token)
    except InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    user = await user_repository.get_by_id(payload.sub)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    return user
