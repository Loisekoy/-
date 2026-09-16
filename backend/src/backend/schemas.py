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
    training_duration_minutes: Literal[30, 60, 90]
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
    training_duration_minutes: Literal[30, 60, 90] | None = None
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
    body_part_id: int
    difficulty_level: Difficulty
    equipment: str = Field(min_length=1, max_length=80)
    movement_type: MovementType
    description: str = Field(min_length=1)


class ExerciseCreate(ExerciseBase):
    pass


class ExerciseUpdate(BaseModel):
    exercise_name: str | None = Field(default=None, min_length=1, max_length=120)
    body_part_id: int | None = None
    difficulty_level: Difficulty | None = None
    equipment: str | None = Field(default=None, min_length=1, max_length=80)
    movement_type: MovementType | None = None
    description: str | None = Field(default=None, min_length=1)
    is_active: bool | None = None


class ExerciseRead(ORMModel):
    exercise_id: int
    exercise_name: str
    body_part: BodyPartRead
    difficulty_level: str
    equipment: str
    movement_type: str
    description: str
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
    session_name: str
    status: str
    started_at: datetime
    ended_at: datetime | None
    notes: str | None
    sets: list[WorkoutSetRead]


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
