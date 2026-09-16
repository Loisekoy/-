import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


BIGINT_PK = BigInteger().with_variant(Integer, "sqlite")


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Admin(Base, TimestampMixin):
    __tablename__ = "admins"
    __table_args__ = (
        CheckConstraint("length(username) >= 3", name="ck_admin_username_length"),
        Index("ix_admins_username", "username", unique=True),
    )

    admin_id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(80), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class TrainingGoal(Base):
    __tablename__ = "training_goals"
    __table_args__ = (
        CheckConstraint("default_sets BETWEEN 1 AND 6", name="ck_goal_default_sets"),
        CheckConstraint("default_reps BETWEEN 1 AND 30", name="ck_goal_default_reps"),
        CheckConstraint("default_rest_seconds BETWEEN 15 AND 300", name="ck_goal_default_rest"),
    )

    training_goal_id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    goal_code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    goal_name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    default_sets: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    default_reps: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    default_rest_seconds: Mapped[int] = mapped_column(Integer, nullable=False)


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("age BETWEEN 13 AND 100", name="ck_user_age"),
        CheckConstraint("height_cm BETWEEN 50 AND 300", name="ck_user_height"),
        CheckConstraint(
            "gender IS NULL OR gender IN ('male','female','non_binary','prefer_not_to_say')",
            name="ck_user_gender",
        ),
        CheckConstraint(
            "training_experience IN ('beginner','intermediate','advanced')",
            name="ck_user_experience",
        ),
        CheckConstraint("training_days_per_week IN (2,3,4,5,6)", name="ck_user_days"),
        CheckConstraint("training_duration_minutes IN (30,60,90)", name="ck_user_duration"),
        Index("ix_users_training_goal_id", "training_goal_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    gender: Mapped[str | None] = mapped_column(String(20))
    age: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    height_cm: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    training_experience: Mapped[str] = mapped_column(String(20), nullable=False)
    training_goal_id: Mapped[int] = mapped_column(
        ForeignKey("training_goals.training_goal_id", ondelete="RESTRICT"), nullable=False
    )
    training_days_per_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    training_duration_minutes: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    training_goal: Mapped[TrainingGoal] = relationship()
    preferred_body_parts: Mapped[list[UserBodyPart]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    body_records: Mapped[list[BodyRecord]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


class BodyPart(Base):
    __tablename__ = "body_parts"
    __table_args__ = (CheckConstraint("display_order > 0", name="ck_body_part_order"),)

    body_part_id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    body_part_code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name_zh: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    display_order: Mapped[int] = mapped_column(SmallInteger, unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))


class UserBodyPart(Base):
    __tablename__ = "user_body_parts"
    __table_args__ = (Index("ix_user_body_parts_reverse", "body_part_id", "user_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True
    )
    body_part_id: Mapped[int] = mapped_column(
        ForeignKey("body_parts.body_part_id", ondelete="RESTRICT"), primary_key=True
    )
    selected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="preferred_body_parts")
    body_part: Mapped[BodyPart] = relationship()


class Exercise(Base, TimestampMixin):
    __tablename__ = "exercises"
    __table_args__ = (
        CheckConstraint(
            "difficulty_level IN ('beginner','intermediate','advanced')",
            name="ck_exercise_difficulty",
        ),
        CheckConstraint(
            "movement_type IN ('compound','isolation')", name="ck_exercise_movement_type"
        ),
        Index("uq_exercises_name_ci", func.lower(text("exercise_name")), unique=True),
        Index("ix_exercises_recommendation", "body_part_id", "difficulty_level", "is_active"),
        Index("ix_exercises_equipment", "equipment", "is_active"),
    )

    exercise_id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    exercise_name: Mapped[str] = mapped_column(String(120), nullable=False)
    body_part_id: Mapped[int] = mapped_column(
        ForeignKey("body_parts.body_part_id", ondelete="RESTRICT"), nullable=False
    )
    difficulty_level: Mapped[str] = mapped_column(String(20), nullable=False)
    equipment: Mapped[str] = mapped_column(String(80), nullable=False)
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(255))
    external_exercise_id: Mapped[str | None] = mapped_column(String(80), unique=True)
    gif_url: Mapped[str | None] = mapped_column(String(500))
    target_muscles: Mapped[list[str]] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    secondary_muscles: Mapped[list[str]] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    instructions: Mapped[list[str]] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    body_part: Mapped[BodyPart] = relationship()


class WorkoutPlan(Base):
    __tablename__ = "workout_plans"
    __table_args__ = (
        CheckConstraint("training_days_per_week IN (2,3,4,5,6)", name="ck_plan_days"),
        CheckConstraint("training_duration_minutes IN (30,60,90)", name="ck_plan_duration"),
        CheckConstraint("status IN ('generated','active','archived')", name="ck_plan_status"),
        Index("ix_workout_plans_user_generated", "user_id", text("generated_at DESC")),
        Index(
            "uq_workout_plans_one_active",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )

    plan_id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    training_goal_id: Mapped[int] = mapped_column(
        ForeignKey("training_goals.training_goal_id", ondelete="RESTRICT"), nullable=False
    )
    plan_name: Mapped[str] = mapped_column(String(120), nullable=False)
    training_days_per_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    training_duration_minutes: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship()
    training_goal: Mapped[TrainingGoal] = relationship()
    days: Mapped[list[PlanDay]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="PlanDay.day_number",
    )


class PlanDay(Base):
    __tablename__ = "plan_days"
    __table_args__ = (
        CheckConstraint("day_number BETWEEN 1 AND 6", name="ck_plan_day_number"),
        UniqueConstraint("plan_id", "day_number", name="uq_plan_day_number"),
    )

    plan_day_id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("workout_plans.plan_id", ondelete="CASCADE"), nullable=False
    )
    day_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    day_name: Mapped[str] = mapped_column(String(100), nullable=False)
    focus_summary: Mapped[str] = mapped_column(String(150), nullable=False)

    plan: Mapped[WorkoutPlan] = relationship(back_populates="days")
    exercises: Mapped[list[PlanExercise]] = relationship(
        back_populates="plan_day",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="PlanExercise.exercise_order",
    )


class PlanExercise(Base):
    __tablename__ = "plan_exercises"
    __table_args__ = (
        CheckConstraint("exercise_order > 0", name="ck_plan_exercise_order"),
        CheckConstraint("target_sets BETWEEN 1 AND 6", name="ck_plan_exercise_sets"),
        CheckConstraint("target_reps BETWEEN 1 AND 30", name="ck_plan_exercise_reps"),
        CheckConstraint("rest_seconds BETWEEN 15 AND 300", name="ck_plan_exercise_rest"),
        UniqueConstraint("plan_day_id", "exercise_order", name="uq_plan_exercise_order"),
        UniqueConstraint("plan_day_id", "exercise_id", name="uq_plan_day_exercise"),
        Index("ix_plan_exercises_exercise_id", "exercise_id"),
    )

    plan_exercise_id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    plan_day_id: Mapped[int] = mapped_column(
        ForeignKey("plan_days.plan_day_id", ondelete="CASCADE"), nullable=False
    )
    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.exercise_id", ondelete="RESTRICT"), nullable=False
    )
    exercise_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    target_sets: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    target_reps: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    rest_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    plan_day: Mapped[PlanDay] = relationship(back_populates="exercises")
    exercise: Mapped[Exercise] = relationship()


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('in_progress','completed','cancelled')", name="ck_session_status"
        ),
        CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at", name="ck_session_end_after_start"
        ),
        CheckConstraint(
            "status <> 'completed' OR ended_at IS NOT NULL", name="ck_completed_session_end"
        ),
        Index("ix_sessions_user_started", "user_id", text("started_at DESC")),
        Index("ix_sessions_user_status", "user_id", "status"),
    )

    session_id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    session_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)

    source: Mapped[SessionPlanDay | None] = relationship(
        back_populates="session", cascade="all, delete-orphan", uselist=False
    )
    sets: Mapped[list[WorkoutSet]] = relationship(
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )


class SessionPlanDay(Base):
    __tablename__ = "session_plan_days"
    __table_args__ = (Index("ix_session_plan_days_plan_day", "plan_day_id"),)

    session_id: Mapped[int] = mapped_column(
        ForeignKey("workout_sessions.session_id", ondelete="CASCADE"), primary_key=True
    )
    plan_day_id: Mapped[int] = mapped_column(
        ForeignKey("plan_days.plan_day_id", ondelete="CASCADE"), nullable=False
    )

    session: Mapped[WorkoutSession] = relationship(back_populates="source")
    plan_day: Mapped[PlanDay] = relationship()


class WorkoutSet(Base):
    __tablename__ = "workout_sets"
    __table_args__ = (
        CheckConstraint("set_order > 0", name="ck_workout_set_order"),
        CheckConstraint("set_number > 0", name="ck_workout_set_number"),
        CheckConstraint("weight_kg >= 0", name="ck_workout_set_weight"),
        CheckConstraint("reps BETWEEN 1 AND 100", name="ck_workout_set_reps"),
        UniqueConstraint("session_id", "set_order", name="uq_workout_set_order"),
        UniqueConstraint("session_id", "exercise_id", "set_number", name="uq_session_exercise_set"),
        Index("ix_workout_sets_exercise_logged", "exercise_id", "logged_at"),
    )

    workout_set_id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("workout_sessions.session_id", ondelete="CASCADE"), nullable=False
    )
    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.exercise_id", ondelete="RESTRICT"), nullable=False
    )
    set_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    set_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    reps: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_warmup: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    notes: Mapped[str | None] = mapped_column(Text)
    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session: Mapped[WorkoutSession] = relationship(back_populates="sets")
    exercise: Mapped[Exercise] = relationship()


class BodyRecord(Base, TimestampMixin):
    __tablename__ = "body_records"
    __table_args__ = (
        CheckConstraint("weight_kg BETWEEN 20 AND 500", name="ck_body_record_weight"),
        UniqueConstraint("user_id", "recorded_on", name="uq_body_record_day"),
    )

    body_record_id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    recorded_on: Mapped[date] = mapped_column(Date, nullable=False)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="body_records")
