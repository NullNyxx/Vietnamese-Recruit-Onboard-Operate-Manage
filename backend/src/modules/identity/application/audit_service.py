"""Audit service for recording and querying admin actions.

Provides methods to log admin actions with secret-value stripping
and to retrieve paginated, filterable audit log entries.
"""

from datetime import datetime

from src.modules.identity.domain.entities import (
    AuditActionType,
    AuditLog,
    User,
)
from src.modules.identity.infrastructure.audit_log_repository import (
    AuditLogRepository,
)

# Keys whose values must never be stored in audit details
_SENSITIVE_KEYS = frozenset(
    {
        "client_secret",
        "client_secret_enc",
        "secret",
        "password",
        "token",
        "access_token",
        "refresh_token",
        "access_token_enc",
        "refresh_token_enc",
    }
)

_MASK = "****"


class PaginatedAuditLogs:
    """Paginated audit log response container.

    Attributes:
        items: The list of audit log entries for the current page.
        total: The total number of entries matching the query filters.
        page: The current page number (1-indexed).
        page_size: The number of entries per page.
    """

    def __init__(
        self,
        items: list[AuditLog],
        total: int,
        page: int,
        page_size: int,
    ) -> None:
        self.items = items
        self.total = total
        self.page = page
        self.page_size = page_size


class AuditService:
    """Records admin actions and provides paginated audit log queries.

    Ensures that secret values (e.g. client_secret, tokens) are never
    persisted in audit log details by stripping or masking them before
    storage.

    Args:
        repository: The AuditLogRepository instance for persistence.
    """

    def __init__(self, repository: AuditLogRepository) -> None:
        self._repository = repository

    async def log_action(
        self,
        admin: User,
        action_type: AuditActionType,
        details: dict,
    ) -> AuditLog:
        """Create an audit log entry for an admin action.

        Strips sensitive keys from the details dict before persisting
        to ensure secret values are never stored in the audit trail.

        Args:
            admin: The admin User performing the action.
            action_type: The type of admin action being logged.
            details: A dictionary of action-specific details. Sensitive
                keys will be masked automatically.

        Returns:
            The persisted AuditLog entity.
        """
        sanitized_details = self._sanitize_details(details)

        log_entry = AuditLog(
            admin_user_id=admin.id,
            admin_email=admin.email,
            action_type=action_type,
            details=sanitized_details,
        )

        return await self._repository.create(log_entry)

    async def get_logs(
        self,
        page: int = 1,
        page_size: int = 20,
        action_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> PaginatedAuditLogs:
        """Retrieve paginated audit log entries with optional filtering.

        Args:
            page: The page number to retrieve (1-indexed, default 1).
            page_size: The number of entries per page (default 20).
            action_type: Optional filter by action type string value.
            start_date: Optional filter for entries on or after this date.
            end_date: Optional filter for entries on or before this date.

        Returns:
            A PaginatedAuditLogs instance containing the matching entries
            and pagination metadata.
        """
        offset = (page - 1) * page_size

        filters: dict = {}
        if action_type is not None:
            filters["action_type"] = action_type
        if start_date is not None:
            filters["start_date"] = start_date
        if end_date is not None:
            filters["end_date"] = end_date

        items, total = await self._repository.get_paginated(
            offset=offset,
            limit=page_size,
            filters=filters,
        )

        return PaginatedAuditLogs(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    @staticmethod
    def _sanitize_details(details: dict) -> dict:
        """Remove or mask sensitive values from the details dictionary.

        Recursively processes nested dictionaries. Keys matching known
        sensitive patterns are replaced with a mask value.

        Args:
            details: The raw details dictionary to sanitize.

        Returns:
            A new dictionary with sensitive values masked.
        """
        sanitized: dict = {}
        for key, value in details.items():
            if key.lower() in _SENSITIVE_KEYS:
                sanitized[key] = _MASK
            elif isinstance(value, dict):
                sanitized[key] = AuditService._sanitize_details(value)
            else:
                sanitized[key] = value
        return sanitized
