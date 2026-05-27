"""FastAPI router for admin-only endpoints.

Defines the /api/admin/* endpoints for managing whitelist entries,
OAuth configuration, user roles, and audit logs. All endpoints require
the authenticated user to have the Admin role.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.modules.identity.api.admin_schemas import (
    AdminUserResponse,
    AuditLogResponse,
    PaginatedAuditLogsResponse,
    RoleUpdateRequest,
)
from src.modules.identity.api.schemas import (
    OAuthConfigResponse,
    OAuthConfigUpdateRequest,
    WhitelistAddRequest,
    WhitelistEntryCreatedResponse,
    WhitelistEntrySchema,
    WhitelistListResponse,
)
from src.modules.identity.application.audit_service import AuditService
from src.modules.identity.application.oauth_config_manager import (
    OAuthConfigManager,
    OAuthConfigValidationError,
)
from src.modules.identity.application.role_service import (
    LastAdminError,
    RoleService,
    SuperAdminProtectedError,
    UserNotFoundError,
)
from src.modules.identity.application.whitelist_manager import WhitelistManager
from src.modules.identity.container import (
    get_current_user,
    get_db_session,
    get_oauth_config_manager,
    get_settings,
    get_whitelist_manager,
)
from src.modules.identity.domain.entities import AuditActionType, User, UserRole
from src.modules.identity.infrastructure.audit_log_repository import AuditLogRepository

admin_router = APIRouter(prefix="/api/admin", tags=["admin"])


async def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Verify the current user has the Admin role.

    This dependency should be used on all admin endpoints to enforce
    role-based access control. It first resolves the authenticated user
    via ``get_current_user``, then checks that the user's role is ADMIN.

    Args:
        current_user: The authenticated User entity from the JWT.

    Returns:
        The authenticated User entity if they have the Admin role.

    Raises:
        HTTPException: 403 Forbidden if the user does not have the Admin role.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail={"code": "ADMIN_ACCESS_DENIED", "message": "Admin access required"},
        )
    return current_user


# Type alias for use in endpoint signatures.
AdminUserDep = Annotated[User, Depends(require_admin)]


# --- Dependency providers for admin services ---


async def get_role_service(
    session: AsyncSession = Depends(get_db_session),
) -> RoleService:
    """Provide a RoleService instance with the current session.

    Args:
        session: The async database session from DI.

    Returns:
        A RoleService bound to the current session and super admin config.
    """
    settings = get_settings()
    return RoleService(session=session, super_admin_email=settings.super_admin_email)


async def get_audit_service(
    session: AsyncSession = Depends(get_db_session),
) -> AuditService:
    """Provide an AuditService instance with the current session.

    Args:
        session: The async database session from DI.

    Returns:
        An AuditService bound to the current session's audit log repository.
    """
    repository = AuditLogRepository(session)
    return AuditService(repository=repository)


# --- Whitelist Endpoints ---


@admin_router.get("/whitelist", response_model=WhitelistListResponse)
async def list_whitelist(
    admin_user: AdminUserDep,
    whitelist_manager: WhitelistManager = Depends(get_whitelist_manager),
) -> WhitelistListResponse:
    """List all whitelist entries (merged file + database).

    Returns all whitelist entries from both the file-based whitelist and
    the database. File-based entries are marked as read-only.

    Args:
        admin_user: The authenticated admin user (enforced by require_admin).
        whitelist_manager: The WhitelistManager for querying entries.

    Returns:
        A list of all whitelist entries with metadata.
    """
    entries = await whitelist_manager.list_entries()
    items = [
        WhitelistEntrySchema(
            id=e.id,
            value=e.value,
            entry_type=e.entry_type,
            added_by_email=e.added_by_email,
            created_at=e.created_at,
            source=e.source,
            is_readonly=e.is_readonly,
        )
        for e in entries
    ]
    return WhitelistListResponse(items=items, total=len(items))


@admin_router.post("/whitelist", response_model=WhitelistEntryCreatedResponse, status_code=201)
async def add_whitelist_entry(
    body: WhitelistAddRequest,
    admin_user: AdminUserDep,
    whitelist_manager: WhitelistManager = Depends(get_whitelist_manager),
    audit_service: AuditService = Depends(get_audit_service),
) -> WhitelistEntryCreatedResponse:
    """Add a new whitelist entry.

    Validates the input format (email or domain pattern), checks for
    duplicates, and persists the entry. Logs an audit trail entry.

    Args:
        body: The request body containing the value to whitelist.
        admin_user: The authenticated admin user performing the action.
        whitelist_manager: The WhitelistManager for entry management.
        audit_service: The AuditService for audit logging.

    Returns:
        The newly created whitelist entry.

    Raises:
        HTTPException: 422 if format is invalid, 409 if duplicate.
    """
    entry = await whitelist_manager.add_entry(value=body.value, admin=admin_user)

    # Log the whitelist addition in the audit trail.
    await audit_service.log_action(
        admin=admin_user,
        action_type=AuditActionType.WHITELIST_ADD,
        details={
            "entry_id": str(entry.id),
            "value": entry.value,
            "entry_type": entry.entry_type.value,
        },
    )

    return WhitelistEntryCreatedResponse.model_validate(entry)


@admin_router.delete("/whitelist/{entry_id}", status_code=204)
async def remove_whitelist_entry(
    entry_id: UUID,
    admin_user: AdminUserDep,
    whitelist_manager: WhitelistManager = Depends(get_whitelist_manager),
    audit_service: AuditService = Depends(get_audit_service),
) -> None:
    """Remove a whitelist entry by ID.

    Only database-sourced entries can be removed. File-based entries
    are read-only and cannot be deleted via the API.

    Args:
        entry_id: The UUID of the entry to remove.
        admin_user: The authenticated admin user performing the action.
        whitelist_manager: The WhitelistManager for entry management.
        audit_service: The AuditService for audit logging.

    Raises:
        HTTPException: 404 if the entry does not exist.
    """
    await whitelist_manager.remove_entry(entry_id=entry_id, admin=admin_user)

    # Log the whitelist removal in the audit trail.
    await audit_service.log_action(
        admin=admin_user,
        action_type=AuditActionType.WHITELIST_REMOVE,
        details={
            "entry_id": str(entry_id),
        },
    )


# --- User Management Endpoints ---


@admin_router.get("/users", response_model=list[AdminUserResponse])
async def list_users(
    admin_user: AdminUserDep,
    session: AsyncSession = Depends(get_db_session),
) -> list[AdminUserResponse]:
    """List all users with their roles.

    Returns all users in the system with their profile information
    and current role assignment.

    Args:
        admin_user: The authenticated admin user (enforced by require_admin).
        session: The async database session.

    Returns:
        A list of all users with their roles and profile data.
    """
    statement = select(User).order_by(User.email)
    result = await session.execute(statement)
    users = result.scalars().all()
    return [AdminUserResponse.model_validate(user) for user in users]


@admin_router.patch("/users/{user_id}/role", response_model=AdminUserResponse)
async def change_user_role(
    user_id: UUID,
    body: RoleUpdateRequest,
    admin_user: AdminUserDep,
    role_service: RoleService = Depends(get_role_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> AdminUserResponse:
    """Change a user's role.

    Promotes a user to admin or demotes an admin to regular user.
    Logs an audit entry for the role change. Protects against demoting
    the last admin or the super admin.

    Args:
        user_id: The UUID of the target user.
        body: The request body containing the new role.
        admin_user: The authenticated admin user performing the change.
        role_service: The RoleService for role management.
        audit_service: The AuditService for audit logging.

    Returns:
        The updated user with their new role.

    Raises:
        HTTPException: 404 if user not found, 400 if last admin or super admin protected.
    """
    try:
        if body.role == UserRole.ADMIN:
            updated_user = await role_service.promote_to_admin(user_id, admin_user)
        else:
            updated_user = await role_service.demote_to_user(user_id, admin_user)
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": exc.error_code, "message": exc.message},
        ) from exc
    except LastAdminError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": exc.error_code, "message": exc.message},
        ) from exc
    except SuperAdminProtectedError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": exc.error_code, "message": exc.message},
        ) from exc

    # Log the role change in the audit trail.
    await audit_service.log_action(
        admin=admin_user,
        action_type=AuditActionType.ROLE_CHANGE,
        details={
            "target_user_id": str(updated_user.id),
            "target_user_email": updated_user.email,
            "old_role": UserRole.USER.value
            if body.role == UserRole.ADMIN
            else UserRole.ADMIN.value,
            "new_role": body.role.value,
        },
    )

    return AdminUserResponse.model_validate(updated_user)


# --- Audit Log Endpoints ---


@admin_router.get("/audit-logs", response_model=PaginatedAuditLogsResponse)
async def get_audit_logs(
    admin_user: AdminUserDep,
    audit_service: AuditService = Depends(get_audit_service),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    action_type: str | None = Query(default=None, description="Filter by action type"),
    start_date: datetime | None = Query(
        default=None, description="Filter entries on or after this date"
    ),
    end_date: datetime | None = Query(
        default=None, description="Filter entries on or before this date"
    ),
) -> PaginatedAuditLogsResponse:
    """Retrieve paginated audit logs with optional filters.

    Returns audit log entries ordered by most recent first, with
    support for filtering by action type and date range.

    Args:
        admin_user: The authenticated admin user (enforced by require_admin).
        audit_service: The AuditService for querying logs.
        page: The page number to retrieve (1-indexed).
        page_size: The number of entries per page (1-100).
        action_type: Optional filter by action type string value.
        start_date: Optional filter for entries on or after this date.
        end_date: Optional filter for entries on or before this date.

    Returns:
        Paginated audit log entries with metadata.
    """
    paginated = await audit_service.get_logs(
        page=page,
        page_size=page_size,
        action_type=action_type,
        start_date=start_date,
        end_date=end_date,
    )

    return PaginatedAuditLogsResponse(
        items=[AuditLogResponse.model_validate(log) for log in paginated.items],
        total=paginated.total,
        page=paginated.page,
        page_size=page_size,
    )


# --- OAuth Config Endpoints ---


@admin_router.get("/oauth/config", response_model=OAuthConfigResponse)
async def get_oauth_config(
    admin_user: AdminUserDep,
    oauth_manager: OAuthConfigManager = Depends(get_oauth_config_manager),
) -> OAuthConfigResponse:
    """Get the current OAuth configuration with masked secret.

    Returns the active OAuth configuration from the database if one exists,
    otherwise returns the environment variable configuration. The client_secret
    is always masked, showing only the last 4 characters.

    Args:
        admin_user: The authenticated admin user (enforced by require_admin).
        oauth_manager: The OAuthConfigManager for retrieving configuration.

    Returns:
        The current OAuth configuration with masked secret.
    """
    config = await oauth_manager.get_active_config()
    return OAuthConfigResponse(
        client_id=config.client_id,
        client_secret_masked=config.client_secret_masked,
        redirect_uri=config.redirect_uri,
        updated_at=config.updated_at,
        source=config.source,
    )


@admin_router.post("/oauth/config", response_model=OAuthConfigResponse)
async def update_oauth_config(
    body: OAuthConfigUpdateRequest,
    admin_user: AdminUserDep,
    oauth_manager: OAuthConfigManager = Depends(get_oauth_config_manager),
    audit_service: AuditService = Depends(get_audit_service),
) -> OAuthConfigResponse:
    """Update OAuth credentials with validation.

    Validates the submitted credentials (non-empty client_id, valid redirect_uri,
    and Google discovery endpoint check) before encrypting and persisting them.
    Previous credentials are retained until new ones are validated. An audit log
    entry is created recording the update.

    Args:
        body: The request body containing client_id, client_secret, and redirect_uri.
        admin_user: The authenticated admin user performing the update.
        oauth_manager: The OAuthConfigManager for credential management.
        audit_service: The AuditService for audit logging.

    Returns:
        The updated OAuth configuration with masked secret.

    Raises:
        HTTPException: 400 if credential validation fails (invalid format or
            Google discovery check failure).
    """
    try:
        config = await oauth_manager.update_config(
            client_id=body.client_id,
            client_secret=body.client_secret,
            redirect_uri=body.redirect_uri,
            admin=admin_user,
        )
    except OAuthConfigValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "OAUTH_VALIDATION_FAILED", "message": exc.message},
        ) from exc

    # Log the OAuth config update in the audit trail.
    await audit_service.log_action(
        admin=admin_user,
        action_type=AuditActionType.OAUTH_UPDATE,
        details={
            "client_id": body.client_id,
            "redirect_uri": body.redirect_uri,
            # Never log the client_secret value
        },
    )

    return OAuthConfigResponse(
        client_id=config.client_id,
        client_secret_masked=config.client_secret_masked,
        redirect_uri=config.redirect_uri,
        updated_at=config.updated_at,
        source=config.source,
    )
