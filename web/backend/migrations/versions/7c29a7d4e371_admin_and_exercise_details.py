"""admin auth and exercise details

Revision ID: 7c29a7d4e371
Revises: 5f6d6d2d9b7c
Create Date: 2026-09-16 12:55:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7c29a7d4e371"
down_revision: str | Sequence[str] | None = "5f6d6d2d9b7c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "admins",
        sa.Column(
            "admin_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("(true)"), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint("length(username) >= 3", name="ck_admin_username_length"),
        sa.PrimaryKeyConstraint("admin_id"),
    )
    op.create_index("ix_admins_username", "admins", ["username"], unique=True)

    op.add_column(
        "exercises",
        sa.Column("external_exercise_id", sa.String(length=80), nullable=True),
    )
    op.add_column("exercises", sa.Column("gif_url", sa.String(length=500), nullable=True))
    op.add_column(
        "exercises",
        sa.Column("target_muscles", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
    )
    op.add_column(
        "exercises",
        sa.Column("secondary_muscles", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
    )
    op.add_column(
        "exercises",
        sa.Column("instructions", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
    )
    op.create_index("ix_exercises_external_id", "exercises", ["external_exercise_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_exercises_external_id", table_name="exercises")
    op.drop_column("exercises", "instructions")
    op.drop_column("exercises", "secondary_muscles")
    op.drop_column("exercises", "target_muscles")
    op.drop_column("exercises", "gif_url")
    op.drop_column("exercises", "external_exercise_id")
    op.drop_index("ix_admins_username", table_name="admins")
    op.drop_table("admins")
