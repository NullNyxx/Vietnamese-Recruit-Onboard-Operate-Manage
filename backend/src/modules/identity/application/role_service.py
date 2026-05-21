"""RoleService for managing user role assignments.

Provides methods to promote users to admin, demote admins to regular users,
and bootstrap the super admin at application startup. Includes protection
against demoting the last admin or the super admin.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.modules.identity.domain.entities import User, UserRole
from src.modules.identity.domain.exceptions import AuthError

logger = logging.getLogger(__name__)


class LastAdminError(AuthError):
    """Cannot demote the last remaining administrator.

    Raised when an attempt is made to remove admin role from the only
    user with admin privileges, which would leave the system without
    any administrator.
    """

    status_code = 400
    error_code = "ADMIN_LAST_ADMIN"
    message = "Cannot remove the last administrator"


class SuperAdminProtectedError(AuthError):
    """Super admin role cannot be changed.

    Raised when an attempt is made to demote the super admin user
    whose email is configured via AUTH_SUPER_ADMIN_EMAIL.
    """

    status_code = 400
    error_code = "ADMIN_SUPER_ADMIN_PROTECTED"
    message = "Super admin role cannot be changed"


class UserNotFoundError(AuthError):
    """Target user does not exist.

    Raised when a role change is attempted on a user ID that does
    not correspond to any user in the database.
    """

    status_code = 404
    error_code = "USER_NOT_FOUND"
    message = "User not found"


class RoleService:
    """Manages user role assignments with safety protections.

    Coordinates role changes (promote/demote) while enforcing invariants:
    - The super admin cannot be demoted.
    - The last remaining admin cannot be demoted.

    Args:
        session: Async database session for user queries and updates.
        super_admin_email: The configured super admin email address, or None
            if not configured.
    """

    def __init__(self, session: AsyncSession, super_admin_email: str | None = None) -> None:
        """Initialize RoleService with database session and super admin config.

        Args:
            session: An SQLAlchemy AsyncSession for database operations.
            super_admin_email: The email of the super admin (from AUTH_SUPER_ADMIN_EMAIL
                env var), or None if not configured.
        """
        self._session = session
        self._super_admin_email = super_admin_email.lower() if super_admin_email else None

    async def promote_to_admin(self, target_user_id: UUID, admin_user: User) -> User:
        """Promote a user to the admin role.

        Changes the target user's role from USER to ADMIN. If the user
        is already an admin, this is a no-op that returns the user unchanged.

        Args:
            target_user_id: The UUID of the user to promote.
            admin_user: The admin user performing the promotion (for audit context).

        Returns:
            The updated User entity with admin role.

        Raises:
            UserNotFoundError: If no user exists with the given ID.
        """
        user = await self._get_user_by_id(target_user_id)
        if user is None:
            raise UserNotFoundError()

        if user.role == UserRole.ADMIN:
            return user

        user.role = UserRole.ADMIN
        self._session.add(user)
        await self._session.flush()

        logger.info(
            "User %s promoted to admin by %s",
            user.email,
            admin_user.email,
        )
        return user

    async def demote_to_user(self, target_user_id: UUID, admin_user: User) -> User:
        """Demote an admin to regular user role.

        Changes the target user's role from ADMIN to USER. Enforces
        protection against demoting the super admin or the last remaining
        admin in the system.

        Args:
            target_user_id: The UUID of the user to demote.
            admin_user: The admin user performing the demotion (for audit context).

        Returns:
            The updated User entity with user role.

        Raises:
            UserNotFoundError: If no user exists with the given ID.
            SuperAdminProtectedError: If the target user is the super admin.
            LastAdminError: If the target is the last remaining admin.
        """
        user = await self._get_user_by_id(target_user_id)
        if user is None:
            raise UserNotFoundError()

        if user.role == UserRole.USER:
            return user

        # Protect the super admin from demotion.
        if self._super_admin_email and user.email.lower() == self._super_admin_email:
            raise SuperAdminProtectedError()

        # Protect the last admin from demotion.
        admin_count = await self._count_admins()
        if admin_count <= 1:
            raise LastAdminError()

        user.role = UserRole.USER
        self._session.add(user)
        await self._session.flush()

        logger.info(
            "User %s demoted to user by %s",
            user.email,
            admin_user.email,
        )
        return user

    async def ensure_super_admin(self, email: str) -> None:
        """Ensure the super admin email has the admin role.

        Called at application startup to bootstrap the first administrator.
        If the user exists, their role is set to ADMIN. If the user does
        not exist yet (hasn't logged in), a log message is emitted and
        the role will be assigned on first login.

        Args:
            email: The super admin email address from AUTH_SUPER_ADMIN_EMAIL.
        """
        statement = select(User).where(func.lower(User.email) == email.lower())
        result = await self._session.execute(statement)
        user = result.scalars().first()

        if user is None:
            logger.info(
                "Super admin user '%s' not found in database. "
                "Admin role will be assigned on first login.",
                email,
            )
            return

        if user.role != UserRole.ADMIN:
            user.role = UserRole.ADMIN
            self._session.add(user)
            await self._session.flush()
            logger.info("Super admin role assigned to existing user '%s'.", email)
        else:
            logger.debug("Super admin '%s' already has admin role.", email)

    async def _get_user_by_id(self, user_id: UUID) -> User | None:
        """Retrieve a user by their unique identifier.

        Args:
            user_id: The UUID primary key of the user.

        Returns:
            The User entity if found, None otherwise.
        """
        statement = select(User).where(User.id == user_id)
        result = await self._session.execute(statement)
        return result.scalars().first()

    async def _count_admins(self) -> int:
        """Count the number of users with the admin role.

        Returns:
            The total number of admin users in the database.
        """
        statement = select(func.count()).select_from(User).where(User.role == UserRole.ADMIN)
        result = await self._session.execute(statement)
        return result.scalar_one()
