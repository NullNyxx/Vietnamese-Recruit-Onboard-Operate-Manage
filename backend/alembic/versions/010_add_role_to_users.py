"""Add role column to users table.

Revision ID: 010
Revises: 009
Create Date: 2024-01-01 00:00:09.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add role column to users table with index."""
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.String(length=10),
            nullable=False,
            server_default=sa.text("'user'"),
        ),
    )
    op.create_index("ix_users_role", "users", ["role"])


def downgrade() -> None:
    """Remove role column from users table."""
    op.drop_index("ix_users_role", table_name="users")
    op.drop_column("users", "role")
