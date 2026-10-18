"""llm generations, exercise i18n, and workout session state

Revision ID: a4b9d8e1c2f3
Revises: 7c29a7d4e371
Create Date: 2026-09-16 13:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a4b9d8e1c2f3"
down_revision: str | Sequence[str] | None = "7c29a7d4e371"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _rebuild_duration_constraints() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        with op.batch_alter_table("users") as batch:
            batch.drop_constraint("ck_user_duration", type_="check")
            batch.create_check_constraint(
                "ck_user_duration", "training_duration_minutes IN (30,45,60,90)"
            )
        with op.batch_alter_table("workout_plans") as batch:
            batch.drop_constraint("ck_plan_duration", type_="check")
            batch.create_check_constraint(
                "ck_plan_duration", "training_duration_minutes IN (30,45,60,90)"
            )
        return

    op.drop_constraint("ck_user_duration", "users", type_="check")
    op.create_check_constraint(
        "ck_user_duration", "users", "training_duration_minutes IN (30,45,60,90)"
    )
    op.drop_constraint("ck_plan_duration", "workout_plans", type_="check")
    op.create_check_constraint(
        "ck_plan_duration", "workout_plans", "training_duration_minutes IN (30,45,60,90)"
    )


def _rebuild_session_constraints() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        with op.batch_alter_table("workout_sessions") as batch:
            batch.add_column(sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
            batch.drop_constraint("ck_session_status", type_="check")
            batch.create_check_constraint(
                "ck_session_status",
                "status IN ('in_progress','completed','abandoned','cancelled')",
            )
            batch.create_check_constraint(
                "ck_session_complete_after_start",
                "completed_at IS NULL OR completed_at >= started_at",
            )
        return

    op.add_column(
        "workout_sessions", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.drop_constraint("ck_session_status", "workout_sessions", type_="check")
    op.create_check_constraint(
        "ck_session_status",
        "workout_sessions",
        "status IN ('in_progress','completed','abandoned','cancelled')",
    )
    op.create_check_constraint(
        "ck_session_complete_after_start",
        "workout_sessions",
        "completed_at IS NULL OR completed_at >= started_at",
    )


def upgrade() -> None:
    _rebuild_duration_constraints()
    _rebuild_session_constraints()

    op.add_column("exercises", sa.Column("exercise_name_en", sa.String(length=120), nullable=True))
    op.add_column("exercises", sa.Column("exercise_name_zh", sa.String(length=120), nullable=True))
    op.add_column("exercises", sa.Column("description_en", sa.Text(), nullable=True))
    op.add_column("exercises", sa.Column("description_zh", sa.Text(), nullable=True))
    op.add_column(
        "exercises",
        sa.Column("instructions_en", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
    )
    op.add_column(
        "exercises",
        sa.Column("instructions_zh", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
    )
    op.add_column("exercises", sa.Column("coaching_notes_en", sa.Text(), nullable=True))
    op.add_column("exercises", sa.Column("coaching_notes_zh", sa.Text(), nullable=True))

    op.execute(
        "UPDATE exercises SET exercise_name_en = exercise_name WHERE exercise_name_en IS NULL"
    )
    op.execute(
        "UPDATE exercises SET exercise_name_zh = exercise_name WHERE exercise_name_zh IS NULL"
    )
    op.execute("UPDATE exercises SET description_zh = description WHERE description_zh IS NULL")

    op.create_table(
        "llm_generations",
        sa.Column(
            "llm_generation_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("used_fallback", sa.Boolean(), server_default=sa.text("(false)"), nullable=False),
        sa.Column("prompt_summary", sa.Text(), nullable=True),
        sa.Column("response_summary", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('success','failed','fallback')", name="ck_llm_generation_status"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("llm_generation_id"),
    )
    op.create_index(
        "ix_llm_generations_user_created",
        "llm_generations",
        ["user_id", sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index("ix_llm_generations_status", "llm_generations", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_llm_generations_status", table_name="llm_generations")
    op.drop_index("ix_llm_generations_user_created", table_name="llm_generations")
    op.drop_table("llm_generations")

    op.drop_column("exercises", "coaching_notes_zh")
    op.drop_column("exercises", "coaching_notes_en")
    op.drop_column("exercises", "instructions_zh")
    op.drop_column("exercises", "instructions_en")
    op.drop_column("exercises", "description_zh")
    op.drop_column("exercises", "description_en")
    op.drop_column("exercises", "exercise_name_zh")
    op.drop_column("exercises", "exercise_name_en")

    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        with op.batch_alter_table("workout_sessions") as batch:
            batch.drop_constraint("ck_session_complete_after_start", type_="check")
            batch.drop_constraint("ck_session_status", type_="check")
            batch.create_check_constraint(
                "ck_session_status", "status IN ('in_progress','completed','cancelled')"
            )
            batch.drop_column("completed_at")
        with op.batch_alter_table("workout_plans") as batch:
            batch.drop_constraint("ck_plan_duration", type_="check")
            batch.create_check_constraint(
                "ck_plan_duration", "training_duration_minutes IN (30,60,90)"
            )
        with op.batch_alter_table("users") as batch:
            batch.drop_constraint("ck_user_duration", type_="check")
            batch.create_check_constraint(
                "ck_user_duration", "training_duration_minutes IN (30,60,90)"
            )
        return

    op.drop_constraint("ck_session_complete_after_start", "workout_sessions", type_="check")
    op.drop_constraint("ck_session_status", "workout_sessions", type_="check")
    op.create_check_constraint(
        "ck_session_status",
        "workout_sessions",
        "status IN ('in_progress','completed','cancelled')",
    )
    op.drop_column("workout_sessions", "completed_at")
    op.drop_constraint("ck_plan_duration", "workout_plans", type_="check")
    op.create_check_constraint(
        "ck_plan_duration", "workout_plans", "training_duration_minutes IN (30,60,90)"
    )
    op.drop_constraint("ck_user_duration", "users", type_="check")
    op.create_check_constraint(
        "ck_user_duration", "users", "training_duration_minutes IN (30,60,90)"
    )
