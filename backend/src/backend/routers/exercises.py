from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from backend.database import get_db
from backend.models import BodyPart, Exercise, PlanExercise, WorkoutSet
from backend.schemas import ExerciseCreate, ExerciseRead, ExerciseUpdate

router = APIRouter(prefix="/exercises", tags=["exercises"])
SessionDep = Annotated[Session, Depends(get_db)]


def _get_exercise(db: Session, exercise_id: int) -> Exercise:
    exercise = db.scalar(
        select(Exercise)
        .options(joinedload(Exercise.body_part))
        .where(Exercise.exercise_id == exercise_id)
    )
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return exercise


@router.post("", response_model=ExerciseRead, status_code=status.HTTP_201_CREATED)
def create_exercise(payload: ExerciseCreate, db: SessionDep) -> Exercise:
    if db.get(BodyPart, payload.body_part_id) is None:
        raise HTTPException(status_code=422, detail="Invalid body part")
    exercise = Exercise(**payload.model_dump())
    exercise.exercise_name = exercise.exercise_name.strip()
    db.add(exercise)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Exercise name already exists") from exc
    return _get_exercise(db, exercise.exercise_id)


@router.patch("/{exercise_id}", response_model=ExerciseRead)
def update_exercise(exercise_id: int, payload: ExerciseUpdate, db: SessionDep) -> Exercise:
    exercise = _get_exercise(db, exercise_id)
    changes = payload.model_dump(exclude_unset=True)
    if "body_part_id" in changes and db.get(BodyPart, changes["body_part_id"]) is None:
        raise HTTPException(status_code=422, detail="Invalid body part")
    for key, value in changes.items():
        if key in {"exercise_name", "image_url"} and isinstance(value, str):
            value = value.strip()
        setattr(exercise, key, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Exercise name already exists") from exc
    return _get_exercise(db, exercise_id)


@router.delete("/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exercise(exercise_id: int, db: SessionDep) -> Response:
    exercise = _get_exercise(db, exercise_id)
    plan_refs = db.scalar(
        select(func.count())
        .select_from(PlanExercise)
        .where(PlanExercise.exercise_id == exercise_id)
    )
    set_refs = db.scalar(
        select(func.count()).select_from(WorkoutSet).where(WorkoutSet.exercise_id == exercise_id)
    )
    if (plan_refs or 0) + (set_refs or 0) > 0:
        exercise.is_active = False
    else:
        db.delete(exercise)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
