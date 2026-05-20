"""Create recruitment pipeline tables.

Revision ID: 009
Revises: 008
Create Date: 2024-01-01 00:00:08.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create recruitment tables: candidates, cv_documents, recruitment_audit_logs."""

    # --- candidates ---
    op.create_table(
        "candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("skills", JSONB(), nullable=False, server_default="[]"),
        sa.Column("experience", JSONB(), nullable=False, server_default="[]"),
        sa.Column("education", JSONB(), nullable=False, server_default="[]"),
        sa.Column("summary", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("parsed_cv_json", JSONB(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="new"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("source_email_message_id", sa.Uuid(), nullable=True),
        sa.Column("rejection_reason", sa.String(length=1000), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["source_email_message_id"], ["email_messages.id"]
        ),
    )

    op.create_index("ix_candidates_email", "candidates", ["email"])
    op.create_index("ix_candidates_status", "candidates", ["status"])

    # --- cv_documents ---
    op.create_table(
        "cv_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=True),
        sa.Column("gmail_message_id", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("ocr_output", sa.Text(), nullable=True),
        sa.Column("parsed_cv_data", JSONB(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column(
            "processing_status",
            sa.String(length=30),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("processing_error", sa.String(length=500), nullable=True),
        sa.Column("validation_errors", JSONB(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
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
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"]),
    )

    op.create_index("ix_cv_documents_processing_status", "cv_documents", ["processing_status"])
    op.create_index("ix_cv_documents_gmail_message_id", "cv_documents", ["gmail_message_id"])
    op.create_index("ix_cv_documents_candidate_id", "cv_documents", ["candidate_id"])

    # --- recruitment_audit_logs ---
    op.create_table(
        "recruitment_audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("operation_type", sa.String(length=50), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("previous_value", JSONB(), nullable=True),
        sa.Column("new_value", JSONB(), nullable=True),
        sa.Column("change_summary", sa.String(length=500), nullable=True),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("token_usage", JSONB(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )

    op.create_index("ix_recruitment_audit_logs_entity_id", "recruitment_audit_logs", ["entity_id"])
    op.create_index(
        "ix_recruitment_audit_logs_operation_type", "recruitment_audit_logs", ["operation_type"]
    )
    op.create_index("ix_recruitment_audit_logs_user_id", "recruitment_audit_logs", ["user_id"])
    op.create_index(
        "ix_recruitment_audit_logs_created_at", "recruitment_audit_logs", ["created_at"]
    )


def downgrade() -> None:
    """Drop all recruitment tables in reverse order."""
    op.drop_index("ix_recruitment_audit_logs_created_at", table_name="recruitment_audit_logs")
    op.drop_index("ix_recruitment_audit_logs_user_id", table_name="recruitment_audit_logs")
    op.drop_index("ix_recruitment_audit_logs_operation_type", table_name="recruitment_audit_logs")
    op.drop_index("ix_recruitment_audit_logs_entity_id", table_name="recruitment_audit_logs")
    op.drop_table("recruitment_audit_logs")

    op.drop_index("ix_cv_documents_candidate_id", table_name="cv_documents")
    op.drop_index("ix_cv_documents_gmail_message_id", table_name="cv_documents")
    op.drop_index("ix_cv_documents_processing_status", table_name="cv_documents")
    op.drop_table("cv_documents")

    op.drop_index("ix_candidates_status", table_name="candidates")
    op.drop_index("ix_candidates_email", table_name="candidates")
    op.drop_table("candidates")
