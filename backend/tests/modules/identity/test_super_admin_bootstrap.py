"""Unit tests for super admin bootstrap logic.

Tests the startup bootstrap behavior including:
- Calling ensure_super_admin when AUTH_SUPER_ADMIN_EMAIL is set
- Logging a warning when no super admin is configured and no admin exists
- Assigning admin role during user auto-provisioning when email matches super admin
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.modules.identity.domain.entities import User, UserRole
from src.modules.identity.infrastructure.user_repository import UserRepository


class TestUserRepositoryUpsertWithRole:
    """Tests for UserRepository.upsert with role parameter."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def google_user_info(self):
        """Create a mock GoogleUserInfo."""
        info = MagicMock()
        info.email = "admin@example.com"
        info.name = "Admin User"
        info.picture = "https://example.com/avatar.jpg"
        info.sub = "google-sub-admin"
        return info

    async def test_new_user_gets_default_user_role(self, mock_session, google_user_info):
        """New user without explicit role should get UserRole.USER."""
        # Simulate no existing user found
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = UserRepository(mock_session)
        user = await repo.upsert(google_user_info)

        assert user.role == UserRole.USER

    async def test_new_user_gets_admin_role_when_specified(self, mock_session, google_user_info):
        """New user with role=ADMIN should get UserRole.ADMIN."""
        # Simulate no existing user found
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = UserRepository(mock_session)
        user = await repo.upsert(google_user_info, role=UserRole.ADMIN)

        assert user.role == UserRole.ADMIN

    async def test_existing_user_role_not_changed_by_upsert(self, mock_session, google_user_info):
        """Existing user's role should not be changed by upsert even if role is passed."""
        existing_user = MagicMock(spec=User)
        existing_user.role = UserRole.USER
        existing_user.email = "admin@example.com"

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = existing_user
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = UserRepository(mock_session)
        user = await repo.upsert(google_user_info, role=UserRole.ADMIN)

        # Existing user is returned unchanged (role param only applies to new users)
        assert user == existing_user


class TestAuthServiceSuperAdminProvisioning:
    """Tests for AuthService assigning admin role to super admin on first login."""

    async def test_super_admin_email_gets_admin_role_on_upsert(self):
        """When email matches super admin, upsert should be called with ADMIN role."""
        from src.modules.identity.application.auth_service import AuthService

        mock_settings = MagicMock()
        mock_settings.super_admin_email = "superadmin@example.com"
        mock_settings.google_client_id = "test-client-id"
        mock_settings.google_redirect_uri = "http://localhost:8000/api/auth/callback"
        mock_settings.refresh_token_expire_days = 7

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "superadmin@example.com"

        mock_user_repo = MagicMock()
        mock_user_repo.upsert = AsyncMock(return_value=mock_user)

        mock_jwt_utils = MagicMock()
        mock_jwt_utils.verify_state_token.return_value = {"nonce": "test"}

        mock_crypto = MagicMock()
        mock_crypto.encrypt.side_effect = lambda x: f"enc:{x}"

        mock_whitelist = MagicMock()
        mock_whitelist.is_allowed.return_value = True

        mock_oauth_service = MagicMock()
        mock_oauth_service.exchange_code = AsyncMock(return_value=MagicMock(
            access_token="at",
            refresh_token="rt",
            id_token="eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiIxMjMiLCJlbWFpbCI6InN1cGVyYWRtaW5AZXhhbXBsZS5jb20iLCJuYW1lIjoiU3VwZXIgQWRtaW4ifQ.sig",
            expires_in=3600,
            scope="openid email profile",
        ))
        mock_oauth_service.determine_grant_status.return_value = MagicMock(
            gmail_grant_valid=True, calendar_grant_valid=True
        )

        mock_token_service = MagicMock()
        mock_token_service.create_access_token.return_value = "access-token"
        mock_token_service.create_refresh_token.return_value = ("refresh", "hash")
        mock_token_service.revoke_user_tokens = AsyncMock()

        mock_oauth_grant_repo = MagicMock()
        mock_oauth_grant_repo.upsert = AsyncMock()

        mock_refresh_repo = MagicMock()
        mock_refresh_repo.store = AsyncMock()

        service = AuthService(
            settings=mock_settings,
            jwt_utils=mock_jwt_utils,
            crypto=mock_crypto,
            whitelist_service=mock_whitelist,
            oauth_service=mock_oauth_service,
            token_service=mock_token_service,
            user_repository=mock_user_repo,
            oauth_grant_repository=mock_oauth_grant_repo,
            refresh_token_repository=mock_refresh_repo,
        )

        with patch("src.modules.identity.application.auth_service.jose_jwt") as mock_jose:
            mock_jose.get_unverified_claims.return_value = {
                "sub": "google-sub-123",
                "email": "superadmin@example.com",
                "name": "Super Admin",
            }

            await service.handle_callback("code", "state", "verifier")

        # Verify upsert was called with role=ADMIN
        mock_user_repo.upsert.assert_called_once()
        call_kwargs = mock_user_repo.upsert.call_args[1]
        assert call_kwargs["role"] == UserRole.ADMIN

    async def test_non_super_admin_email_gets_no_role_override(self):
        """When email does not match super admin, upsert should be called with role=None."""
        from src.modules.identity.application.auth_service import AuthService

        mock_settings = MagicMock()
        mock_settings.super_admin_email = "superadmin@example.com"
        mock_settings.google_client_id = "test-client-id"
        mock_settings.google_redirect_uri = "http://localhost:8000/api/auth/callback"
        mock_settings.refresh_token_expire_days = 7

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "regular@example.com"

        mock_user_repo = MagicMock()
        mock_user_repo.upsert = AsyncMock(return_value=mock_user)

        mock_jwt_utils = MagicMock()
        mock_jwt_utils.verify_state_token.return_value = {"nonce": "test"}

        mock_crypto = MagicMock()
        mock_crypto.encrypt.side_effect = lambda x: f"enc:{x}"

        mock_whitelist = MagicMock()
        mock_whitelist.is_allowed.return_value = True

        mock_oauth_service = MagicMock()
        mock_oauth_service.exchange_code = AsyncMock(return_value=MagicMock(
            access_token="at",
            refresh_token="rt",
            id_token="eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiIxMjMiLCJlbWFpbCI6InJlZ3VsYXJAZXhhbXBsZS5jb20iLCJuYW1lIjoiUmVndWxhciBVc2VyIn0.sig",
            expires_in=3600,
            scope="openid email profile",
        ))
        mock_oauth_service.determine_grant_status.return_value = MagicMock(
            gmail_grant_valid=True, calendar_grant_valid=True
        )

        mock_token_service = MagicMock()
        mock_token_service.create_access_token.return_value = "access-token"
        mock_token_service.create_refresh_token.return_value = ("refresh", "hash")
        mock_token_service.revoke_user_tokens = AsyncMock()

        mock_oauth_grant_repo = MagicMock()
        mock_oauth_grant_repo.upsert = AsyncMock()

        mock_refresh_repo = MagicMock()
        mock_refresh_repo.store = AsyncMock()

        service = AuthService(
            settings=mock_settings,
            jwt_utils=mock_jwt_utils,
            crypto=mock_crypto,
            whitelist_service=mock_whitelist,
            oauth_service=mock_oauth_service,
            token_service=mock_token_service,
            user_repository=mock_user_repo,
            oauth_grant_repository=mock_oauth_grant_repo,
            refresh_token_repository=mock_refresh_repo,
        )

        with patch("src.modules.identity.application.auth_service.jose_jwt") as mock_jose:
            mock_jose.get_unverified_claims.return_value = {
                "sub": "google-sub-456",
                "email": "regular@example.com",
                "name": "Regular User",
            }

            await service.handle_callback("code", "state", "verifier")

        # Verify upsert was called with role=None (default user)
        mock_user_repo.upsert.assert_called_once()
        call_kwargs = mock_user_repo.upsert.call_args[1]
        assert call_kwargs["role"] is None

    async def test_no_super_admin_configured_passes_none_role(self):
        """When no super admin email is configured, role should be None."""
        from src.modules.identity.application.auth_service import AuthService

        mock_settings = MagicMock()
        mock_settings.super_admin_email = None
        mock_settings.google_client_id = "test-client-id"
        mock_settings.google_redirect_uri = "http://localhost:8000/api/auth/callback"
        mock_settings.refresh_token_expire_days = 7

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "anyone@example.com"

        mock_user_repo = MagicMock()
        mock_user_repo.upsert = AsyncMock(return_value=mock_user)

        mock_jwt_utils = MagicMock()
        mock_jwt_utils.verify_state_token.return_value = {"nonce": "test"}

        mock_crypto = MagicMock()
        mock_crypto.encrypt.side_effect = lambda x: f"enc:{x}"

        mock_whitelist = MagicMock()
        mock_whitelist.is_allowed.return_value = True

        mock_oauth_service = MagicMock()
        mock_oauth_service.exchange_code = AsyncMock(return_value=MagicMock(
            access_token="at",
            refresh_token="rt",
            id_token="eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiIxMjMiLCJlbWFpbCI6ImFueW9uZUBleGFtcGxlLmNvbSIsIm5hbWUiOiJBbnlvbmUifQ.sig",
            expires_in=3600,
            scope="openid email profile",
        ))
        mock_oauth_service.determine_grant_status.return_value = MagicMock(
            gmail_grant_valid=True, calendar_grant_valid=True
        )

        mock_token_service = MagicMock()
        mock_token_service.create_access_token.return_value = "access-token"
        mock_token_service.create_refresh_token.return_value = ("refresh", "hash")
        mock_token_service.revoke_user_tokens = AsyncMock()

        mock_oauth_grant_repo = MagicMock()
        mock_oauth_grant_repo.upsert = AsyncMock()

        mock_refresh_repo = MagicMock()
        mock_refresh_repo.store = AsyncMock()

        service = AuthService(
            settings=mock_settings,
            jwt_utils=mock_jwt_utils,
            crypto=mock_crypto,
            whitelist_service=mock_whitelist,
            oauth_service=mock_oauth_service,
            token_service=mock_token_service,
            user_repository=mock_user_repo,
            oauth_grant_repository=mock_oauth_grant_repo,
            refresh_token_repository=mock_refresh_repo,
        )

        with patch("src.modules.identity.application.auth_service.jose_jwt") as mock_jose:
            mock_jose.get_unverified_claims.return_value = {
                "sub": "google-sub-789",
                "email": "anyone@example.com",
                "name": "Anyone",
            }

            await service.handle_callback("code", "state", "verifier")

        # Verify upsert was called with role=None
        mock_user_repo.upsert.assert_called_once()
        call_kwargs = mock_user_repo.upsert.call_args[1]
        assert call_kwargs["role"] is None


class TestBootstrapSuperAdminFunction:
    """Tests for the _bootstrap_super_admin startup function."""

    async def test_calls_ensure_super_admin_when_email_configured(self):
        """When AUTH_SUPER_ADMIN_EMAIL is set, ensure_super_admin should be called."""
        from src.main import _bootstrap_super_admin

        mock_settings = MagicMock()
        mock_settings.super_admin_email = "admin@company.com"

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("src.modules.identity.container.get_settings", return_value=mock_settings), \
             patch("src.modules.identity.container._get_async_session_maker", return_value=mock_session_maker), \
             patch("src.modules.identity.application.role_service.RoleService") as MockRoleService:
            mock_role_service = AsyncMock()
            MockRoleService.return_value = mock_role_service

            await _bootstrap_super_admin()

            MockRoleService.assert_called_once_with(
                session=mock_session, super_admin_email="admin@company.com"
            )
            mock_role_service.ensure_super_admin.assert_called_once_with("admin@company.com")
            mock_session.commit.assert_called_once()

    async def test_logs_warning_when_no_admin_configured_and_none_exists(self):
        """When no super admin email and no admin in DB, should log warning."""
        from src.main import _bootstrap_super_admin

        mock_settings = MagicMock()
        mock_settings.super_admin_email = None

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 0  # No admins exist

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("src.modules.identity.container.get_settings", return_value=mock_settings), \
             patch("src.modules.identity.container._get_async_session_maker", return_value=mock_session_maker), \
             patch("src.main.logger") as mock_logger:

            await _bootstrap_super_admin()

            mock_logger.warning.assert_called_once()
            warning_msg = mock_logger.warning.call_args[0][0]
            assert "AUTH_SUPER_ADMIN_EMAIL" in warning_msg

    async def test_no_warning_when_admin_exists_without_super_admin_config(self):
        """When no super admin email but admins exist, should not log warning."""
        from src.main import _bootstrap_super_admin

        mock_settings = MagicMock()
        mock_settings.super_admin_email = None

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 2  # Admins exist

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("src.modules.identity.container.get_settings", return_value=mock_settings), \
             patch("src.modules.identity.container._get_async_session_maker", return_value=mock_session_maker), \
             patch("src.main.logger") as mock_logger:

            await _bootstrap_super_admin()

            mock_logger.warning.assert_not_called()


class TestConfigSuperAdminEmail:
    """Tests for the super_admin_email config setting."""

    def test_super_admin_email_defaults_to_none(self):
        """super_admin_email should default to None when not set."""
        from src.modules.identity.infrastructure.config import AuthSettings

        with patch.dict("os.environ", {
            "AUTH_GOOGLE_CLIENT_ID": "test",
            "AUTH_GOOGLE_CLIENT_SECRET": "test",
            "AUTH_JWT_SECRET_KEY": "test",
            "AUTH_OAUTH_TOKEN_ENCRYPTION_KEY": "dGVzdGtleXRlc3RrZXl0ZXN0a2V5dGVzdGtleXM=",
        }, clear=False):
            settings = AuthSettings()  # type: ignore[call-arg]
            assert settings.super_admin_email is None

    def test_super_admin_email_reads_from_env(self):
        """super_admin_email should read from AUTH_SUPER_ADMIN_EMAIL env var."""
        import os
        from src.modules.identity.infrastructure.config import AuthSettings

        with patch.dict("os.environ", {
            "AUTH_GOOGLE_CLIENT_ID": "test",
            "AUTH_GOOGLE_CLIENT_SECRET": "test",
            "AUTH_JWT_SECRET_KEY": "test",
            "AUTH_OAUTH_TOKEN_ENCRYPTION_KEY": "dGVzdGtleXRlc3RrZXl0ZXN0a2V5dGVzdGtleXM=",
            "AUTH_SUPER_ADMIN_EMAIL": "admin@company.com",
        }, clear=False):
            settings = AuthSettings()  # type: ignore[call-arg]
            assert settings.super_admin_email == "admin@company.com"
