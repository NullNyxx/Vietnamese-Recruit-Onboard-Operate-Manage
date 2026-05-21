"""Unit tests for admin user management and audit log endpoints.

Tests cover:
- GET /api/admin/users - list all users with roles
- PATCH /api/admin/users/{id}/role - change user role
- GET /api/admin/audit-logs - paginated audit logs with filters
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.modules.identity.api.admin_router import (
    admin_router,
    get_audit_service,
    get_role_service,
    require_admin,
)
from src.modules.identity.api.admin_schemas import (
    AdminUserResponse,
    AuditLogResponse,
    PaginatedAuditLogsResponse,
    RoleUpdateRequest,
)
from src.modules.identity.application.audit_service import AuditService, PaginatedAuditLogs
from src.modules.identity.application.role_service import (
    LastAdminError,
    RoleService,
    SuperAdminProtectedError,
    UserNotFoundError,
)
from src.modules.identity.domain.entities import (
    AuditActionType,
    AuditLog,
    User,
    UserRole,
)


def _make_user(
    email: str = "user@example.com",
    role: UserRole = UserRole.USER,
    name: str = "Test User",
) -> User:
    """Create a User entity for testing."""
    return User(
        id=uuid4(),
        email=email,
        name=name,
        avatar_url=None,
        google_sub=f"google-sub-{uuid4().hex[:8]}",
        created_at=datetime.now(UTC),
        last_login=datetime.now(UTC),
        is_active=True,
        role=role,
    )


def _make_audit_log(
    admin_email: str = "admin@example.com",
    action_type: AuditActionType = AuditActionType.ROLE_CHANGE,
    details: dict | None = None,
) -> AuditLog:
    """Create an AuditLog entity for testing."""
    return AuditLog(
        id=uuid4(),
        admin_user_id=uuid4(),
        admin_email=admin_email,
        action_type=action_type,
        details=details or {"target_user_email": "user@example.com"},
        created_at=datetime.now(UTC),
    )


def _create_test_app(admin_user: User) -> FastAPI:
    """Create a test FastAPI app with the admin router and overridden deps."""
    app = FastAPI()
    app.include_router(admin_router)

    # Override require_admin to return our test admin user
    async def _override_require_admin() -> User:
        return admin_user

    app.dependency_overrides[require_admin] = _override_require_admin
    return app


class TestListUsers:
    """Tests for GET /api/admin/users."""

    def test_returns_all_users(self) -> None:
        admin = _make_user(email="admin@example.com", role=UserRole.ADMIN)
        user1 = _make_user(email="alice@example.com", role=UserRole.USER, name="Alice")
        user2 = _make_user(email="bob@example.com", role=UserRole.ADMIN, name="Bob")

        app = _create_test_app(admin)

        # Mock the database session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [user1, user2]
        mock_session.execute = AsyncMock(return_value=mock_result)

        from src.modules.identity.container import get_db_session

        async def _override_session():
            return mock_session

        app.dependency_overrides[get_db_session] = _override_session

        client = TestClient(app)
        response = client.get("/api/admin/users")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["email"] == "alice@example.com"
        assert data[1]["email"] == "bob@example.com"
        assert data[0]["role"] == "user"
        assert data[1]["role"] == "admin"

    def test_returns_empty_list_when_no_users(self) -> None:
        admin = _make_user(email="admin@example.com", role=UserRole.ADMIN)
        app = _create_test_app(admin)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        from src.modules.identity.container import get_db_session

        async def _override_session():
            return mock_session

        app.dependency_overrides[get_db_session] = _override_session

        client = TestClient(app)
        response = client.get("/api/admin/users")

        assert response.status_code == 200
        assert response.json() == []


class TestChangeUserRole:
    """Tests for PATCH /api/admin/users/{id}/role."""

    def test_promotes_user_to_admin(self) -> None:
        admin = _make_user(email="admin@example.com", role=UserRole.ADMIN)
        target = _make_user(email="target@example.com", role=UserRole.USER)

        app = _create_test_app(admin)

        # Mock RoleService
        mock_role_service = AsyncMock(spec=RoleService)
        promoted_target = _make_user(email="target@example.com", role=UserRole.ADMIN)
        promoted_target.id = target.id
        mock_role_service.promote_to_admin = AsyncMock(return_value=promoted_target)

        # Mock AuditService
        mock_audit_service = AsyncMock(spec=AuditService)
        mock_audit_service.log_action = AsyncMock(return_value=_make_audit_log())

        async def _override_role_service():
            return mock_role_service

        async def _override_audit_service():
            return mock_audit_service

        app.dependency_overrides[get_role_service] = _override_role_service
        app.dependency_overrides[get_audit_service] = _override_audit_service

        client = TestClient(app)
        response = client.patch(
            f"/api/admin/users/{target.id}/role",
            json={"role": "admin"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"
        assert data["email"] == "target@example.com"
        mock_role_service.promote_to_admin.assert_called_once()
        mock_audit_service.log_action.assert_called_once()

    def test_demotes_admin_to_user(self) -> None:
        admin = _make_user(email="admin@example.com", role=UserRole.ADMIN)
        target = _make_user(email="target@example.com", role=UserRole.ADMIN)

        app = _create_test_app(admin)

        mock_role_service = AsyncMock(spec=RoleService)
        demoted_target = _make_user(email="target@example.com", role=UserRole.USER)
        demoted_target.id = target.id
        mock_role_service.demote_to_user = AsyncMock(return_value=demoted_target)

        mock_audit_service = AsyncMock(spec=AuditService)
        mock_audit_service.log_action = AsyncMock(return_value=_make_audit_log())

        async def _override_role_service():
            return mock_role_service

        async def _override_audit_service():
            return mock_audit_service

        app.dependency_overrides[get_role_service] = _override_role_service
        app.dependency_overrides[get_audit_service] = _override_audit_service

        client = TestClient(app)
        response = client.patch(
            f"/api/admin/users/{target.id}/role",
            json={"role": "user"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "user"
        mock_role_service.demote_to_user.assert_called_once()

    def test_returns_404_when_user_not_found(self) -> None:
        admin = _make_user(email="admin@example.com", role=UserRole.ADMIN)
        app = _create_test_app(admin)

        mock_role_service = AsyncMock(spec=RoleService)
        mock_role_service.promote_to_admin = AsyncMock(side_effect=UserNotFoundError())

        mock_audit_service = AsyncMock(spec=AuditService)

        async def _override_role_service():
            return mock_role_service

        async def _override_audit_service():
            return mock_audit_service

        app.dependency_overrides[get_role_service] = _override_role_service
        app.dependency_overrides[get_audit_service] = _override_audit_service

        client = TestClient(app)
        response = client.patch(
            f"/api/admin/users/{uuid4()}/role",
            json={"role": "admin"},
        )

        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "USER_NOT_FOUND"

    def test_returns_400_when_last_admin(self) -> None:
        admin = _make_user(email="admin@example.com", role=UserRole.ADMIN)
        app = _create_test_app(admin)

        mock_role_service = AsyncMock(spec=RoleService)
        mock_role_service.demote_to_user = AsyncMock(side_effect=LastAdminError())

        mock_audit_service = AsyncMock(spec=AuditService)

        async def _override_role_service():
            return mock_role_service

        async def _override_audit_service():
            return mock_audit_service

        app.dependency_overrides[get_role_service] = _override_role_service
        app.dependency_overrides[get_audit_service] = _override_audit_service

        client = TestClient(app)
        response = client.patch(
            f"/api/admin/users/{uuid4()}/role",
            json={"role": "user"},
        )

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "ADMIN_LAST_ADMIN"

    def test_returns_400_when_super_admin_protected(self) -> None:
        admin = _make_user(email="admin@example.com", role=UserRole.ADMIN)
        app = _create_test_app(admin)

        mock_role_service = AsyncMock(spec=RoleService)
        mock_role_service.demote_to_user = AsyncMock(side_effect=SuperAdminProtectedError())

        mock_audit_service = AsyncMock(spec=AuditService)

        async def _override_role_service():
            return mock_role_service

        async def _override_audit_service():
            return mock_audit_service

        app.dependency_overrides[get_role_service] = _override_role_service
        app.dependency_overrides[get_audit_service] = _override_audit_service

        client = TestClient(app)
        response = client.patch(
            f"/api/admin/users/{uuid4()}/role",
            json={"role": "user"},
        )

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "ADMIN_SUPER_ADMIN_PROTECTED"

    def test_rejects_invalid_role_value(self) -> None:
        admin = _make_user(email="admin@example.com", role=UserRole.ADMIN)
        app = _create_test_app(admin)

        mock_role_service = AsyncMock(spec=RoleService)
        mock_audit_service = AsyncMock(spec=AuditService)

        async def _override_role_service():
            return mock_role_service

        async def _override_audit_service():
            return mock_audit_service

        app.dependency_overrides[get_role_service] = _override_role_service
        app.dependency_overrides[get_audit_service] = _override_audit_service

        client = TestClient(app)
        response = client.patch(
            f"/api/admin/users/{uuid4()}/role",
            json={"role": "superadmin"},
        )

        assert response.status_code == 422

    def test_audit_log_records_role_change_details(self) -> None:
        admin = _make_user(email="admin@example.com", role=UserRole.ADMIN)
        target = _make_user(email="target@example.com", role=UserRole.USER)

        app = _create_test_app(admin)

        mock_role_service = AsyncMock(spec=RoleService)
        promoted_target = _make_user(email="target@example.com", role=UserRole.ADMIN)
        promoted_target.id = target.id
        mock_role_service.promote_to_admin = AsyncMock(return_value=promoted_target)

        mock_audit_service = AsyncMock(spec=AuditService)
        mock_audit_service.log_action = AsyncMock(return_value=_make_audit_log())

        async def _override_role_service():
            return mock_role_service

        async def _override_audit_service():
            return mock_audit_service

        app.dependency_overrides[get_role_service] = _override_role_service
        app.dependency_overrides[get_audit_service] = _override_audit_service

        client = TestClient(app)
        client.patch(
            f"/api/admin/users/{target.id}/role",
            json={"role": "admin"},
        )

        # Verify audit log was called with correct details
        call_args = mock_audit_service.log_action.call_args
        assert call_args.kwargs["action_type"] == AuditActionType.ROLE_CHANGE
        details = call_args.kwargs["details"]
        assert details["target_user_email"] == "target@example.com"
        assert details["old_role"] == "user"
        assert details["new_role"] == "admin"


class TestGetAuditLogs:
    """Tests for GET /api/admin/audit-logs."""

    def test_returns_paginated_audit_logs(self) -> None:
        admin = _make_user(email="admin@example.com", role=UserRole.ADMIN)
        app = _create_test_app(admin)

        log1 = _make_audit_log(action_type=AuditActionType.ROLE_CHANGE)
        log2 = _make_audit_log(action_type=AuditActionType.WHITELIST_ADD)

        mock_audit_service = AsyncMock(spec=AuditService)
        mock_audit_service.get_logs = AsyncMock(
            return_value=PaginatedAuditLogs(
                items=[log1, log2],
                total=2,
                page=1,
                page_size=20,
            )
        )

        async def _override_audit_service():
            return mock_audit_service

        app.dependency_overrides[get_audit_service] = _override_audit_service

        client = TestClient(app)
        response = client.get("/api/admin/audit-logs")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert len(data["items"]) == 2
        assert data["items"][0]["action_type"] == "role_change"
        assert data["items"][1]["action_type"] == "whitelist_add"

    def test_passes_filter_params_to_service(self) -> None:
        admin = _make_user(email="admin@example.com", role=UserRole.ADMIN)
        app = _create_test_app(admin)

        mock_audit_service = AsyncMock(spec=AuditService)
        mock_audit_service.get_logs = AsyncMock(
            return_value=PaginatedAuditLogs(
                items=[],
                total=0,
                page=2,
                page_size=10,
            )
        )

        async def _override_audit_service():
            return mock_audit_service

        app.dependency_overrides[get_audit_service] = _override_audit_service

        client = TestClient(app)
        response = client.get(
            "/api/admin/audit-logs",
            params={
                "page": 2,
                "page_size": 10,
                "action_type": "role_change",
            },
        )

        assert response.status_code == 200
        call_args = mock_audit_service.get_logs.call_args
        assert call_args.kwargs["page"] == 2
        assert call_args.kwargs["page_size"] == 10
        assert call_args.kwargs["action_type"] == "role_change"

    def test_returns_empty_when_no_logs(self) -> None:
        admin = _make_user(email="admin@example.com", role=UserRole.ADMIN)
        app = _create_test_app(admin)

        mock_audit_service = AsyncMock(spec=AuditService)
        mock_audit_service.get_logs = AsyncMock(
            return_value=PaginatedAuditLogs(
                items=[],
                total=0,
                page=1,
                page_size=20,
            )
        )

        async def _override_audit_service():
            return mock_audit_service

        app.dependency_overrides[get_audit_service] = _override_audit_service

        client = TestClient(app)
        response = client.get("/api/admin/audit-logs")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_validates_page_size_bounds(self) -> None:
        admin = _make_user(email="admin@example.com", role=UserRole.ADMIN)
        app = _create_test_app(admin)

        mock_audit_service = AsyncMock(spec=AuditService)

        async def _override_audit_service():
            return mock_audit_service

        app.dependency_overrides[get_audit_service] = _override_audit_service

        client = TestClient(app)

        # page_size > 100 should be rejected
        response = client.get("/api/admin/audit-logs", params={"page_size": 101})
        assert response.status_code == 422

        # page < 1 should be rejected
        response = client.get("/api/admin/audit-logs", params={"page": 0})
        assert response.status_code == 422
