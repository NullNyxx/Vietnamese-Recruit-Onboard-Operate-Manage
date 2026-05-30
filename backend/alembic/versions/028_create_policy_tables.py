"""Create policy engine tables.

Creates policy_templates, policy_rules, policy_versions, and
policy_audit_logs tables for the Company Policy Engine module.

Revision ID: 028
Revises: 027
Create Date: 2026-06-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql  # noqa: I001

from alembic import op

revision: str = "028"
down_revision: str | None = "027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create policy engine tables."""
    # --- policy_templates ---
    op.create_table(
        "policy_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("domain", sa.String(20), nullable=False),
        sa.Column("rule_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.String(512), nullable=False),
        sa.Column("rule_condition", postgresql.JSONB(), nullable=False),
        sa.Column("rule_action", postgresql.JSONB(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("legal_constraints", postgresql.JSONB(), nullable=True),
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
        sa.UniqueConstraint("rule_id", name="uq_policy_templates_rule_id"),
    )

    op.create_index("ix_policy_templates_domain", "policy_templates", ["domain"])
    op.create_index("ix_policy_templates_rule_id", "policy_templates", ["rule_id"])

    # --- policy_rules ---
    op.create_table(
        "policy_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("domain", sa.String(20), nullable=False),
        sa.Column("rule_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.String(512), nullable=False),
        sa.Column("rule_condition", postgresql.JSONB(), nullable=False),
        sa.Column("rule_action", postgresql.JSONB(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("template_rule_id", sa.Uuid(), nullable=True),
        sa.Column("is_custom", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
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
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["template_rule_id"],
            ["policy_templates.id"],
            name="fk_policy_rules_template_rule_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_policy_rules_created_by",
        ),
        sa.UniqueConstraint("tenant_id", "rule_id", name="uq_policy_rules_tenant_rule"),
    )

    op.create_index("ix_policy_rules_tenant_id", "policy_rules", ["tenant_id"])
    op.create_index("ix_policy_rules_domain", "policy_rules", ["domain"])

    # --- policy_versions ---
    op.create_table(
        "policy_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("change_summary", sa.String(512), nullable=False),
        sa.Column("rules_added", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rules_removed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rules_modified", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("published_by", sa.Uuid(), nullable=False),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["published_by"],
            ["users.id"],
            name="fk_policy_versions_published_by",
        ),
        sa.UniqueConstraint(
            "tenant_id", "version_number", name="uq_policy_versions_tenant_version"
        ),
    )

    op.create_index("ix_policy_versions_tenant_id", "policy_versions", ["tenant_id"])

    # --- policy_audit_logs ---
    op.create_table(
        "policy_audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_policy_audit_logs_user_id",
        ),
    )

    op.create_index("ix_policy_audit_logs_tenant_id", "policy_audit_logs", ["tenant_id"])


def downgrade() -> None:
    """Drop policy engine tables."""
    op.drop_index("ix_policy_audit_logs_tenant_id", table_name="policy_audit_logs")
    op.drop_table("policy_audit_logs")

    op.drop_index("ix_policy_versions_tenant_id", table_name="policy_versions")
    op.drop_table("policy_versions")

    op.drop_index("ix_policy_rules_domain", table_name="policy_rules")
    op.drop_index("ix_policy_rules_tenant_id", table_name="policy_rules")
    op.drop_table("policy_rules")

    op.drop_index("ix_policy_templates_rule_id", table_name="policy_templates")
    op.drop_index("ix_policy_templates_domain", table_name="policy_templates")
    op.drop_table("policy_templates")
