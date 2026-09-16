import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Gender = Literal["male", "female", "non_binary", "prefer_not_to_say"]
Experience = Literal["beginner", "intermediate", "advanced"]
Difficulty = Literal["beginner", "intermediate", "advanced"]
MovementType = Literal["compound", "isolation"]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TrainingGoalRead(ORMModel):
    training_goal_id: int
    goal_code: str
    goal_name: str
    description: str | None
    default_sets: int
    default_reps: int
    default_rest_seconds: int


class BodyPartRead(ORMModel):
    body_part_id: int
    body_part_code: str
    name_en: str
    name_zh: str
    display_order: int


class OnboardingCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    gender: Gender | None = None
    age: int = Field(ge=13, le=100)
    height_cm: Decimal = Field(ge=50, le=300, decimal_places=2)
    weight_kg: Decimal = Field(ge=20, le=500, decimal_places=2)
    training_experience: Experience
    training_goal_id: int
    training_days_per_week: Literal[2, 3, 4, 5, 6]
    training_duration_minutes: Literal[30, 45, 60, 90]
    preferred_body_part_ids: list[int] = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be blank")
        return value

    @field_validator("preferred_body_part_ids")
    @classmethod
    def unique_body_parts(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("Preferred body parts cannot contain duplicates")
        return value


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    gender: Gender | None = None
    age: int | None = Field(default=None, ge=13, le=100)
    height_cm: Decimal | None = Field(default=None, ge=50, le=300, decimal_places=2)
    training_experience: Experience | None = None
    training_goal_id: int | None = None
    training_days_per_week: Literal[2, 3, 4, 5, 6] | None = None
    training_duration_minutes: Literal[30, 45, 60, 90] | None = None
    preferred_body_part_ids: list[int] | None = Field(default=None, min_length=1)


class UserProfileRead(ORMModel):
    user_id: uuid.UUID
    name: str
    gender: str | None
    age: int
    height_cm: Decimal
    training_experience: str
    training_goal: TrainingGoalRead
    training_days_per_week: int
    training_duration_minutes: int
    preferred_body_parts: list[BodyPartRead]
    latest_weight_kg: Decimal
    created_at: datetime
    updated_at: datetime


class ExerciseBase(BaseModel):
    exercise_name: str = Field(min_length=1, max_length=120)
    exercise_name_en: str | None = Field(default=None, max_length=120)
    exercise_name_zh: str | None = Field(default=None, max_length=120)
    body_part_id: int
    difficulty_level: Difficulty
    equipment: str = Field(min_length=1, max_length=80)
    movement_type: MovementType
    description: str = Field(min_length=1)
    description_en: str | None = None
    description_zh: str | None = None
    image_url: str | None = Field(default=None, max_length=255)
    external_exercise_id: str | None = Field(default=None, max_length=80)
    gif_url: str | None = Field(default=None, max_length=500)
    target_muscles: list[str] = Field(default_factory=list)
    secondary_muscles: list[str] = Field(default_factory=list)
    instructions: list[str] = Field(default_factory=list)
    instructions_en: list[str] = Field(default_factory=list)
    instructions_zh: list[str] = Field(default_factory=list)
    coaching_notes_en: str | None = None
    coaching_notes_zh: str | None = None


class ExerciseCreate(ExerciseBase):
    pass


class ExerciseUpdate(BaseModel):
    exercise_name: str | None = Field(default=None, min_length=1, max_length=120)
    exercise_name_en: str | None = Field(default=None, max_length=120)
    exercise_name_zh: str | None = Field(default=None, max_length=120)
    body_part_id: int | None = None
    difficulty_level: Difficulty | None = None
    equipment: str | None = Field(default=None, min_length=1, max_length=80)
    movement_type: MovementType | None = None
    description: str | None = Field(default=None, min_length=1)
    description_en: str | None = None
    description_zh: str | None = None
    image_url: str | None = Field(default=None, max_length=255)
    external_exercise_id: str | None = Field(default=None, max_length=80)
    gif_url: str | None = Field(default=None, max_length=500)
    target_muscles: list[str] | None = None
    secondary_muscles: list[str] | None = None
    instructions: list[str] | None = None
    instructions_en: list[str] | None = None
    instructions_zh: list[str] | None = None
    coaching_notes_en: str | None = None
    coaching_notes_zh: str | None = None
    is_active: bool | None = None


class ExerciseRead(ORMModel):
    exercise_id: int
    exercise_name: str
    exercise_name_en: str | None
    exercise_name_zh: str | None
    body_part: BodyPartRead
    difficulty_level: str
    equipment: str
    movement_type: str
    description: str
    description_en: str | None
    description_zh: str | None
    image_url: str | None
    external_exercise_id: str | None
    gif_url: str | None
    target_muscles: list[str]
    secondary_muscles: list[str]
    instructions: list[str]
    instructions_en: list[str]
    instructions_zh: list[str]
    coaching_notes_en: str | None
    coaching_notes_zh: str | None
    is_active: bool


class PlanExerciseRead(ORMModel):
    plan_exercise_id: int
    exercise_order: int
    target_sets: int
    target_reps: int
    rest_seconds: int
    notes: str | None
    exercise: ExerciseRead


class PlanDayRead(ORMModel):
    plan_day_id: int
    day_number: int
    day_name: str
    focus_summary: str
    exercises: list[PlanExerciseRead]


class WorkoutPlanRead(ORMModel):
    plan_id: int
    plan_name: str
    training_goal: TrainingGoalRead
    training_days_per_week: int
    training_duration_minutes: int
    algorithm_version: str
    status: str
    generated_at: datetime
    days: list[PlanDayRead]


class PlanExerciseUpdate(BaseModel):
    target_sets: int | None = Field(default=None, ge=1, le=6)
    target_reps: int | None = Field(default=None, ge=1, le=30)
    rest_seconds: int | None = Field(default=None, ge=15, le=300)
    notes: str | None = None


class WorkoutSessionCreate(BaseModel):
    plan_day_id: int


class WorkoutSetCreate(BaseModel):
    exercise_id: int
    set_number: int = Field(ge=1)
    weight_kg: Decimal = Field(ge=0, decimal_places=2)
    reps: int = Field(ge=1, le=100)
    is_warmup: bool = False
    notes: str | None = None


class WorkoutSetUpdate(BaseModel):
    weight_kg: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    reps: int | None = Field(default=None, ge=1, le=100)
    is_warmup: bool | None = None
    notes: str | None = None


class WorkoutSetRead(ORMModel):
    workout_set_id: int
    set_order: int
    set_number: int
    weight_kg: Decimal
    reps: int
    is_warmup: bool
    notes: str | None
    logged_at: datetime
    exercise: ExerciseRead


class WorkoutSessionRead(ORMModel):
    session_id: int
    plan_day_id: int | None
    session_name: str
    status: str
    started_at: datetime
    ended_at: datetime | None
    completed_at: datetime | None
    notes: str | None
    sets: list[WorkoutSetRead]


class LLMGenerationRead(ORMModel):
    llm_generation_id: int
    user_id: uuid.UUID
    provider: str
    model: str
    status: str
    used_fallback: bool
    prompt_summary: str | None
    response_summary: str | None
    error_message: str | None
    created_at: datetime


class BodyRecordCreate(BaseModel):
    recorded_on: date
    weight_kg: Decimal = Field(ge=20, le=500, decimal_places=2)
    notes: str | None = None


class BodyRecordUpdate(BaseModel):
    recorded_on: date | None = None
    weight_kg: Decimal | None = Field(default=None, ge=20, le=500, decimal_places=2)
    notes: str | None = None


class BodyRecordRead(ORMModel):
    body_record_id: int
    recorded_on: date
    weight_kg: Decimal
    notes: str | None
    created_at: datetime


class MetricPoint(BaseModel):
    label: str
    value: float


class RecentWorkout(BaseModel):
    session_id: int
    session_name: str
    started_at: datetime
    set_count: int
    volume_kg: float


class DashboardRead(BaseModel):
    this_week_workouts: int
    total_completed_workouts: int
    total_training_volume_kg: float
    completed_workouts: int
    working_sets: int
    training_volume_kg: float
    latest_weight_kg: float | None
    weight_change_kg: float | None
    most_trained_body_part: str | None
    most_used_exercise: str | None
    weekly_volume: list[MetricPoint]
    weight_history: list[MetricPoint]
    recent_workouts: list[RecentWorkout]


class DatabaseColumnRead(BaseModel):
    column_name: str
    data_type: str
    is_primary_key: bool
    is_nullable: bool
    foreign_key: str | None


class DatabaseTableRead(BaseModel):
    table_name: str
    row_count: int
    columns: list[DatabaseColumnRead]


class DatabaseRelationshipRead(BaseModel):
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    relationship_type: str
    on_delete: str | None


class DatabaseQueryExampleRead(BaseModel):
    title: str
    sql: str
    rows: list[dict[str, str | int | float | None]]


class DatabaseOverviewRead(BaseModel):
    tables: list[DatabaseTableRead]
    relationships: list[DatabaseRelationshipRead]
    query_examples: list[DatabaseQueryExampleRead]
    normalization_notes: list[str]


class AdminLoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=200)


class AdminRead(ORMModel):
    admin_id: int
    username: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin: AdminRead


class AdminMetricRead(BaseModel):
    label: str
    value: int | float


class AdminRecentUserRead(BaseModel):
    user_id: uuid.UUID
    name: str
    age: int
    goal: str
    experience: str
    joined: datetime


class AdminDashboardRead(BaseModel):
    total_users: int
    new_users_today: int
    total_workouts: int
    total_workout_plans: int
    completed_workouts_today: int
    total_exercises: int
    average_age: float | None
    average_training_days: float | None
    total_training_volume: float
    recent_users: list[AdminRecentUserRead]


class AdminUserListItemRead(BaseModel):
    user_id: uuid.UUID
    name: str
    gender: str | None
    age: int
    height_cm: Decimal
    latest_weight_kg: Decimal | None
    training_goal: str
    training_experience: str
    training_days_per_week: int
    training_duration_minutes: int
    preferred_body_parts: list[str]
    created_at: datetime


class PaginatedAdminUsersRead(BaseModel):
    items: list[AdminUserListItemRead]
    total: int
    page: int
    page_size: int


class AdminPlanSummaryRead(BaseModel):
    plan_id: int
    plan_name: str
    status: str
    generated_at: datetime
    days: list[PlanDayRead]


class AdminWorkoutSessionSummaryRead(BaseModel):
    session_id: int
    session_name: str
    status: str
    started_at: datetime
    ended_at: datetime | None
    completed_at: datetime | None
    set_count: int
    volume_kg: float


class AdminUserDetailRead(BaseModel):
    profile: UserProfileRead
    workout_plans: list[AdminPlanSummaryRead]
    workout_history: list[AdminWorkoutSessionSummaryRead]
    workout_sets: list[WorkoutSetRead]
    weight_history: list[BodyRecordRead]
    llm_generations: list[LLMGenerationRead]


class AdminStatisticsRead(BaseModel):
    total_users: int
    users_by_training_goal: list[MetricPoint]
    users_by_experience_level: list[MetricPoint]
    most_selected_body_parts: list[MetricPoint]
    most_popular_exercises: list[MetricPoint]
    average_training_days_per_week: float | None
    total_workout_sessions: int
    total_training_volume: float
