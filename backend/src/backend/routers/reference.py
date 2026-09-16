from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from backend.database import get_db
from backend.models import BodyPart, Exercise, TrainingGoal
from backend.schemas import BodyPartRead, ExerciseRead, TrainingGoalRead

router = APIRouter(prefix="/reference", tags=["reference"])
SessionDep = Annotated[Session, Depends(get_db)]


@router.get("/training-goals", response_model=list[TrainingGoalRead])
def list_training_goals(db: SessionDep) -> list[TrainingGoal]:
    return list(db.scalars(select(TrainingGoal).order_by(TrainingGoal.training_goal_id)).all())


@router.get("/body-parts", response_model=list[BodyPartRead])
def list_body_parts(db: SessionDep) -> list[BodyPart]:
    return list(
        db.scalars(
            select(BodyPart).where(BodyPart.is_active.is_(True)).order_by(BodyPart.display_order)
        ).all()
    )


@router.get("/exercises", response_model=list[ExerciseRead])
def list_exercises(
    db: SessionDep,
    search: Annotated[str | None, Query(max_length=120)] = None,
    body_part_id: int | None = None,
    difficulty_level: str | None = None,
    equipment: str | None = None,
    include_inactive: bool = False,
) -> list[Exercise]:
    statement = select(Exercise).options(joinedload(Exercise.body_part))
    if not include_inactive:
        statement = statement.where(Exercise.is_active.is_(True))
    if search:
        pattern = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                Exercise.exercise_name.ilike(pattern),
                Exercise.exercise_name_en.ilike(pattern),
                Exercise.exercise_name_zh.ilike(pattern),
                Exercise.description.ilike(pattern),
                Exercise.description_en.ilike(pattern),
                Exercise.description_zh.ilike(pattern),
            )
        )
    if body_part_id is not None:
        statement = statement.where(Exercise.body_part_id == body_part_id)
    if difficulty_level:
        statement = statement.where(Exercise.difficulty_level == difficulty_level)
    if equipment:
        statement = statement.where(Exercise.equipment.ilike(f"%{equipment.strip()}%"))
    return list(db.scalars(statement.order_by(Exercise.exercise_name)).all())
