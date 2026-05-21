"""Attendance & Leave Management module."""

# Import Employee model so SQLAlchemy metadata knows about the 'employees' table
# (needed for FK resolution during flush/commit)
import src.modules.employee.domain.entities  # noqa: F401
import src.modules.identity.domain.entities  # noqa: F401
