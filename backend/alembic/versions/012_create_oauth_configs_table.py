"""Create oauth_configs table.

Revision ID: 012
Revises: 011
Create Date: 2024-01-01 00:00:11.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the oauth_configs table with unique constraint."""
    op.create_table(
        "oauth_configs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "provider",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'google'"),
        ),
        sa.Column("client_id", sa.String(length=255), nullable=False),
        sa.Column("client_secret_enc", sa.Text(), nullable=False),
        sa.Column("redirect_uri", sa.String(length=500), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"]),
        sa.UniqueConstraint("provider", "is_active", name="uq_oauth_config_provider_active"),
    )


def downgrade() -> None:
    """Drop the oauth_configs table."""
    op.drop_table("oauth_configs")
