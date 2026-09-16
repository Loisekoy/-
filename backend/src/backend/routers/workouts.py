import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from backend.database import get_db
from backend.models import (
    Exercise,
    PlanDay,
    PlanExercise,
    SessionPlanDay,
    WorkoutPlan,
    WorkoutSession,
    WorkoutSet,
)
from backend.schemas import (
    WorkoutSessionCreate,
    WorkoutSessionRead,
    WorkoutSetCreate,
    WorkoutSetRead,
    WorkoutSetUpdate,
)

router = APIRouter(prefix="/users/{user_id}/workouts", tags=["workouts"])
SessionDep = Annotated[Session, Depends(get_db)]


def _session_loader():
    return (
        selectinload(WorkoutSession.source),
        selectinload(WorkoutSession.sets)
        .joinedload(WorkoutSet.exercise)
        .joinedload(Exercise.body_part),
    )


def _get_session(db: Session, user_id: uuid.UUID, session_id: int) -> WorkoutSession:
    workout = db.scalar(
        select(WorkoutSession)
        .options(*_session_loader())
        .where(
            WorkoutSession.session_id == session_id,
            WorkoutSession.user_id == user_id,
        )
    )
    if workout is None:
        raise HTTPException(status_code=404, detail="Workout session not found")
    return workout


@router.post("/sessions", response_model=WorkoutSessionRead, status_code=status.HTTP_201_CREATED)
def start_session(
    user_id: uuid.UUID, payload: WorkoutSessionCreate, db: SessionDep
) -> WorkoutSession:
    plan_day = db.scalar(
        select(PlanDay)
        .join(WorkoutPlan)
        .options(
            selectinload(PlanDay.exercises)
            .joinedload(PlanExercise.exercise)
            .joinedload(Exercise.body_part)
        )
        .where(PlanDay.plan_day_id == payload.plan_day_id, WorkoutPlan.user_id == user_id)
    )
    if plan_day is None:
        raise HTTPException(status_code=404, detail="Plan day not found for this user")
    workout = WorkoutSession(
        user_id=user_id,
        session_name=plan_day.day_name,
        status="in_progress",
    )
    db.add(workout)
    db.flush()
    db.add(SessionPlanDay(session_id=workout.session_id, plan_day_id=plan_day.plan_day_id))
    db.commit()
    return _get_session(db, user_id, workout.session_id)


@router.get("/sessions", response_model=list[WorkoutSessionRead])
def list_sessions(
    user_id: uuid.UUID,
    db: SessionDep,
    status_filter: str | None = None,
) -> list[WorkoutSession]:
    statement = (
        select(WorkoutSession)
        .options(*_session_loader())
        .where(WorkoutSession.user_id == user_id)
        .order_by(WorkoutSession.started_at.desc())
    )
    if status_filter:
        statement = statement.where(WorkoutSession.status == status_filter)
    return list(db.scalars(statement).all())


@router.get("/sessions/{session_id}", response_model=WorkoutSessionRead)
def get_session(user_id: uuid.UUID, session_id: int, db: SessionDep) -> WorkoutSession:
    return _get_session(db, user_id, session_id)


@router.post(
    "/sessions/{session_id}/sets",
    response_model=WorkoutSetRead,
    status_code=status.HTTP_201_CREATED,
)
def create_set(
    user_id: uuid.UUID,
    session_id: int,
    payload: WorkoutSetCreate,
    db: SessionDep,
) -> WorkoutSet:
    workout = _get_session(db, user_id, session_id)
    if workout.status != "in_progress":
        raise HTTPException(status_code=409, detail="Only an in-progress workout can be edited")
    if workout.source is not None:
        allowed_exercise_id = db.scalar(
            select(PlanExercise.exercise_id).where(
                PlanExercise.plan_day_id == workout.source.plan_day_id,
                PlanExercise.exercise_id == payload.exercise_id,
            )
        )
        if allowed_exercise_id is None:
            raise HTTPException(
                status_code=422,
                detail="Exercise is not part of this workout session plan day",
            )
    exercise = db.scalar(
        select(Exercise)
        .options(joinedload(Exercise.body_part))
        .where(Exercise.exercise_id == payload.exercise_id, Exercise.is_active.is_(True))
    )
    if exercise is None:
        raise HTTPException(status_code=422, detail="Invalid exercise")
    next_order = (
        db.scalar(
            select(func.coalesce(func.max(WorkoutSet.set_order), 0)).where(
                WorkoutSet.session_id == session_id
            )
        )
        or 0
    ) + 1
    workout_set = WorkoutSet(
        session_id=session_id,
        set_order=next_order,
        **payload.model_dump(),
    )
    db.add(workout_set)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="This set number already exists for the exercise"
        ) from exc
    return db.scalar(
        select(WorkoutSet)
        .options(joinedload(WorkoutSet.exercise).joinedload(Exercise.body_part))
        .where(WorkoutSet.workout_set_id == workout_set.workout_set_id)
    )


@router.patch("/sessions/{session_id}/sets/{set_id}", response_model=WorkoutSetRead)
def update_set(
    user_id: uuid.UUID,
    session_id: int,
    set_id: int,
    payload: WorkoutSetUpdate,
    db: SessionDep,
) -> WorkoutSet:
    workout = _get_session(db, user_id, session_id)
    if workout.status != "in_progress":
        raise HTTPException(status_code=409, detail="Only an in-progress workout can be edited")
    workout_set = db.scalar(
        select(WorkoutSet)
        .options(joinedload(WorkoutSet.exercise).joinedload(Exercise.body_part))
        .where(WorkoutSet.workout_set_id == set_id, WorkoutSet.session_id == session_id)
    )
    if workout_set is None:
        raise HTTPException(status_code=404, detail="Workout set not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(workout_set, key, value)
    db.commit()
    db.refresh(workout_set)
    return workout_set


@router.delete("/sessions/{session_id}/sets/{set_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_set(user_id: uuid.UUID, session_id: int, set_id: int, db: SessionDep) -> Response:
    workout = _get_session(db, user_id, session_id)
    if workout.status != "in_progress":
        raise HTTPException(status_code=409, detail="Only an in-progress workout can be edited")
    workout_set = db.scalar(
        select(WorkoutSet).where(
            WorkoutSet.workout_set_id == set_id, WorkoutSet.session_id == session_id
        )
    )
    if workout_set is None:
        raise HTTPException(status_code=404, detail="Workout set not found")
    db.delete(workout_set)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/sessions/{session_id}/complete", response_model=WorkoutSessionRead)
def complete_session(user_id: uuid.UUID, session_id: int, db: SessionDep) -> WorkoutSession:
    workout = _get_session(db, user_id, session_id)
    if workout.status != "in_progress":
        raise HTTPException(status_code=409, detail="Workout is not in progress")
    if not workout.sets:
        raise HTTPException(status_code=409, detail="Record at least one set before completion")
    workout.status = "completed"
    workout.ended_at = datetime.now(UTC)
    workout.completed_at = workout.ended_at
    db.commit()
    return _get_session(db, user_id, session_id)


@router.post("/sessions/{session_id}/abandon", response_model=WorkoutSessionRead)
def abandon_session(user_id: uuid.UUID, session_id: int, db: SessionDep) -> WorkoutSession:
    workout = _get_session(db, user_id, session_id)
    if workout.status != "in_progress":
        raise HTTPException(status_code=409, detail="Workout is not in progress")
    workout.status = "abandoned"
    workout.ended_at = datetime.now(UTC)
    db.commit()
    return _get_session(db, user_id, session_id)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(user_id: uuid.UUID, session_id: int, db: SessionDep) -> Response:
    workout = _get_session(db, user_id, session_id)
    db.delete(workout)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
