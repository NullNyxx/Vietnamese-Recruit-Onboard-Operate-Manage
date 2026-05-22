"""Create holidays table with Vietnamese public holidays.

Revision ID: 020
Revises: 019
Create Date: 2026-05-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create holidays table and seed Vietnamese public holidays."""
    op.create_table(
        "holidays",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("holiday_date", sa.Date(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("is_recurring", sa.Boolean(), server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Seed Vietnamese public holidays for 2026
    op.execute("""
        INSERT INTO holidays (id, holiday_date, name, is_recurring) VALUES
        (gen_random_uuid(), '2026-01-01', 'Tết Dương lịch', true),
        (gen_random_uuid(), '2026-01-26', 'Tết Nguyên Đán (29 Tết)', false),
        (gen_random_uuid(), '2026-01-27', 'Tết Nguyên Đán (30 Tết)', false),
        (gen_random_uuid(), '2026-01-28', 'Tết Nguyên Đán (Mùng 1)', false),
        (gen_random_uuid(), '2026-01-29', 'Tết Nguyên Đán (Mùng 2)', false),
        (gen_random_uuid(), '2026-01-30', 'Tết Nguyên Đán (Mùng 3)', false),
        (gen_random_uuid(), '2026-04-30', 'Ngày Giải phóng miền Nam', true),
        (gen_random_uuid(), '2026-05-01', 'Ngày Quốc tế Lao động', true),
        (gen_random_uuid(), '2026-09-02', 'Ngày Quốc khánh', true),
        (gen_random_uuid(), '2026-04-06', 'Giỗ Tổ Hùng Vương (10/3 ÂL)', false)
    """)


def downgrade() -> None:
    """Drop holidays table."""
    op.drop_table("holidays")
