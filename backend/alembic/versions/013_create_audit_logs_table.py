"""Create audit_logs table.

Revision ID: 013
Revises: 011, 012
Create Date: 2024-01-01 00:00:12.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "013"
down_revision: Union[str, Sequence[str], None] = ("011", "012")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the audit_logs table with indexes."""
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("admin_user_id", sa.Uuid(), nullable=False),
        sa.Column("admin_email", sa.String(length=255), nullable=False),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("details", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["admin_user_id"], ["users.id"]),
    )

    # Indexes for query performance
    op.create_index("ix_audit_logs_action_type", "audit_logs", ["action_type"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_admin_user_id", "audit_logs", ["admin_user_id"])


def downgrade() -> None:
    """Drop the audit_logs table."""
    op.drop_index("ix_audit_logs_admin_user_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action_type", table_name="audit_logs")
    op.drop_table("audit_logs")
