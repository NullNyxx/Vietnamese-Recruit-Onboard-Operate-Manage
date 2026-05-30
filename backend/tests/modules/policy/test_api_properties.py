# Feature: company-policy-engine, Property 35: Admin Role Authorization
"""Property-based tests for admin role authorization.

Property 35: For any user without the "admin" role for a given tenant,
all policy management endpoints (CRUD, publish, version history) SHALL
reject the request with an authorization error without revealing whether
the requested resource exists.

**Validates: Requirements 11.7**
"""

import string
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from hypothesis import given, settings
from hypothesis import strategies as st

from src.modules.identity.domain.entities import User, UserRole
from src.modules.policy.container import require_policy_admin

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Generate non-admin roles (only UserRole.USER in this system)
_non_admin_roles = st.sampled_from([UserRole.USER])

# Generate user names
_user_name_strategy = st.text(
    alphabet=string.ascii_letters + " ",
    min_size=1,
    max_size=64,
)

# Generate email addresses
_email_strategy = st.text(
    alphabet=string.ascii_lowercase + string.digits,
    min_size=3,
    max_size=20,
).map(lambda s: f"{s}@example.com")


@st.composite
def non_admin_user(draw: st.DrawFn) -> User:
    """Generate a User entity with a non-admin role."""
    role = draw(_non_admin_roles)
    name = draw(_user_name_strategy)
    email = draw(_email_strategy)

    user = User(
        id=uuid4(),
        email=email,
        name=name,
        avatar_url=None,
        google_sub=f"google-{uuid4().hex[:16]}",
        is_active=True,
        role=role,
    )
    return user


@st.composite
def admin_user(draw: st.DrawFn) -> User:
    """Generate a User entity with the admin role."""
    name = draw(_user_name_strategy)
    email = draw(_email_strategy)

    user = User(
        id=uuid4(),
        email=email,
        name=name,
        avatar_url=None,
        google_sub=f"google-{uuid4().hex[:16]}",
        is_active=True,
        role=UserRole.ADMIN,
    )
    return user


# ---------------------------------------------------------------------------
# Property 35: Admin Role Authorization
# ---------------------------------------------------------------------------


class TestProperty35AdminRoleAuthorization:
    """Property 35: Admin Role Authorization.

    For any user without the "admin" role for a given tenant, all policy
    management endpoints (CRUD, publish, version history) SHALL reject
    the request with an authorization error without revealing whether
    the requested resource exists.

    **Validates: Requirements 11.7**
    """

    @settings(max_examples=100)
    @given(user=non_admin_user())
    @pytest.mark.asyncio
    async def test_non_admin_user_rejected_with_403(
        self,
        user: User,
    ) -> None:
        """Any user without the admin role SHALL be rejected with 403.

        The error response SHALL NOT reveal whether the resource exists,
        returning a generic "Access denied" message.

        **Validates: Requirements 11.7**
        """
        with pytest.raises(HTTPException) as exc_info:
            await require_policy_admin(current_user=user)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["code"] == "INSUFFICIENT_ROLE"
        assert exc_info.value.detail["message"] == "Access denied"
        # Ensure no resource existence information is leaked
        assert "not found" not in str(exc_info.value.detail).lower()
        assert "does not exist" not in str(exc_info.value.detail).lower()

    @settings(max_examples=100)
    @given(user=admin_user())
    @pytest.mark.asyncio
    async def test_admin_user_allowed(
        self,
        user: User,
    ) -> None:
        """Any user with the admin role SHALL be allowed through.

        The dependency returns the authenticated user entity when
        the role check passes.

        **Validates: Requirements 11.7**
        """
        result = await require_policy_admin(current_user=user)
        assert result == user
        assert result.role == UserRole.ADMIN

    @settings(max_examples=100)
    @given(user=non_admin_user())
    @pytest.mark.asyncio
    async def test_error_does_not_reveal_resource_existence(
        self,
        user: User,
    ) -> None:
        """The authorization error SHALL NOT reveal whether the
        requested resource exists.

        The error response must be identical regardless of whether
        the target policy rule, version, or endpoint exists.

        **Validates: Requirements 11.7**
        """
        with pytest.raises(HTTPException) as exc_info:
            await require_policy_admin(current_user=user)

        # The error detail should be a fixed structure with no
        # resource-specific information
        detail = exc_info.value.detail
        assert detail == {
            "code": "INSUFFICIENT_ROLE",
            "message": "Access denied",
            "fields": [],
        }
