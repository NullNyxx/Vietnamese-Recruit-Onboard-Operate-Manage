"""Create whitelist_entries table.

Revision ID: 011
Revises: 010
Create Date: 2024-01-01 00:00:10.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the whitelist_entries table with indexes."""
    op.create_table(
        "whitelist_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.Column("entry_type", sa.String(length=20), nullable=False),
        sa.Column("added_by_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["added_by_user_id"], ["users.id"]),
        sa.UniqueConstraint("value", name="uq_whitelist_value"),
    )

    # Indexes for query performance
    op.create_index("ix_whitelist_entries_value", "whitelist_entries", ["value"])
    op.create_index("ix_whitelist_entries_type", "whitelist_entries", ["entry_type"])


def downgrade() -> None:
    """Drop the whitelist_entries table."""
    op.drop_index("ix_whitelist_entries_type", table_name="whitelist_entries")
    op.drop_index("ix_whitelist_entries_value", table_name="whitelist_entries")
    op.drop_table("whitelist_entries")
