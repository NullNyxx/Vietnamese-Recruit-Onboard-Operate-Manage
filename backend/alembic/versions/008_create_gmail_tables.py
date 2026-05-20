"""Create Gmail integration tables.

Revision ID: 008
Revises: 007
Create Date: 2024-01-01 00:00:07.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Gmail integration tables: email_messages, sync_cursors, gmail_label_mappings, email_attachments, gmail_audit_logs."""

    # --- email_messages ---
    op.create_table(
        "email_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("gmail_message_id", sa.String(length=255), nullable=False),
        sa.Column("gmail_thread_id", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=998), nullable=False, server_default=""),
        sa.Column("sender_email", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("sender_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("recipient_emails", JSONB(), nullable=False),
        sa.Column("cc_emails", JSONB(), nullable=False, server_default="[]"),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snippet", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("label_ids", JSONB(), nullable=False, server_default="[]"),
        sa.Column("has_attachments", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("raw_payload_enc", sa.Text(), nullable=True),
        sa.Column("processing_status", sa.String(length=20), nullable=False, server_default="unprocessed"),
        sa.Column("category", sa.String(length=20), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_permanently_failed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
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
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("gmail_message_id"),
    )

    op.create_index("ix_email_messages_user_id", "email_messages", ["user_id"])
    op.create_index("ix_email_messages_gmail_message_id", "email_messages", ["gmail_message_id"])
    op.create_index("ix_email_messages_gmail_thread_id", "email_messages", ["gmail_thread_id"])

    # --- sync_cursors ---
    op.create_table(
        "sync_cursors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("history_id", sa.String(length=50), nullable=False),
        sa.Column("last_poll_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("user_id"),
    )

    # --- gmail_label_mappings ---
    op.create_table(
        "gmail_label_mappings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("label_name", sa.String(length=100), nullable=False),
        sa.Column("gmail_label_id", sa.String(length=255), nullable=False),
        sa.Column("is_initialized", sa.Boolean(), nullable=False, server_default=sa.text("false")),
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
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("user_id", "label_name", name="uq_gmail_label_mappings_user_id_label_name"),
    )

    op.create_index("ix_gmail_label_mappings_user_id", "gmail_label_mappings", ["user_id"])

    # --- email_attachments ---
    op.create_table(
        "email_attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email_message_id", sa.Uuid(), nullable=False),
        sa.Column("gmail_attachment_id", sa.String(length=255), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["email_message_id"], ["email_messages.id"]),
    )

    op.create_index("ix_email_attachments_email_message_id", "email_attachments", ["email_message_id"])

    # --- gmail_audit_logs ---
    op.create_table(
        "gmail_audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("operation_type", sa.String(length=50), nullable=False),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("metadata", JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )

    op.create_index("ix_gmail_audit_logs_user_id", "gmail_audit_logs", ["user_id"])
    op.create_index("ix_gmail_audit_logs_created_at", "gmail_audit_logs", ["created_at"])


def downgrade() -> None:
    """Drop all Gmail integration tables in reverse order."""
    op.drop_index("ix_gmail_audit_logs_created_at", table_name="gmail_audit_logs")
    op.drop_index("ix_gmail_audit_logs_user_id", table_name="gmail_audit_logs")
    op.drop_table("gmail_audit_logs")

    op.drop_index("ix_email_attachments_email_message_id", table_name="email_attachments")
    op.drop_table("email_attachments")

    op.drop_index("ix_gmail_label_mappings_user_id", table_name="gmail_label_mappings")
    op.drop_table("gmail_label_mappings")

    op.drop_table("sync_cursors")

    op.drop_index("ix_email_messages_gmail_thread_id", table_name="email_messages")
    op.drop_index("ix_email_messages_gmail_message_id", table_name="email_messages")
    op.drop_index("ix_email_messages_user_id", table_name="email_messages")
    op.drop_table("email_messages")
