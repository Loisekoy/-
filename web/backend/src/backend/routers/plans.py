import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from backend.database import get_db
from backend.models import Exercise, PlanDay, PlanExercise, WorkoutPlan
from backend.schemas import PlanExerciseUpdate, WorkoutPlanRead
from backend.services.recommendation import RecommendationError, generate_plan

router = APIRouter(prefix="/users/{user_id}/plans", tags=["plans"])
SessionDep = Annotated[Session, Depends(get_db)]


def _plan_loader():
    return (
        selectinload(WorkoutPlan.days)
        .selectinload(PlanDay.exercises)
        .joinedload(PlanExercise.exercise)
        .joinedload(Exercise.body_part)
    )


def _get_plan(db: Session, user_id: uuid.UUID, plan_id: int) -> WorkoutPlan:
    plan = db.scalar(
        select(WorkoutPlan)
        .options(joinedload(WorkoutPlan.training_goal), _plan_loader())
        .where(WorkoutPlan.plan_id == plan_id, WorkoutPlan.user_id == user_id)
    )
    if plan is None:
        raise HTTPException(status_code=404, detail="Workout plan not found")
    return plan


@router.post("/generate", response_model=WorkoutPlanRead, status_code=status.HTTP_201_CREATED)
def create_generated_plan(user_id: uuid.UUID, db: SessionDep) -> WorkoutPlan:
    try:
        plan = generate_plan(db, user_id)
        plan_id = plan.plan_id
        db.commit()
    except RecommendationError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise
    return _get_plan(db, user_id, plan_id)


@router.get("/active", response_model=WorkoutPlanRead)
def get_active_plan(user_id: uuid.UUID, db: SessionDep) -> WorkoutPlan:
    plan_id = db.scalar(
        select(WorkoutPlan.plan_id).where(
            WorkoutPlan.user_id == user_id, WorkoutPlan.status == "active"
        )
    )
    if plan_id is None:
        raise HTTPException(status_code=404, detail="Active workout plan not found")
    return _get_plan(db, user_id, plan_id)


@router.get("", response_model=list[WorkoutPlanRead])
def list_plans(user_id: uuid.UUID, db: SessionDep) -> list[WorkoutPlan]:
    return list(
        db.scalars(
            select(WorkoutPlan)
            .options(joinedload(WorkoutPlan.training_goal), _plan_loader())
            .where(WorkoutPlan.user_id == user_id)
            .order_by(WorkoutPlan.generated_at.desc())
        ).all()
    )


@router.get("/{plan_id}", response_model=WorkoutPlanRead)
def get_plan(user_id: uuid.UUID, plan_id: int, db: SessionDep) -> WorkoutPlan:
    return _get_plan(db, user_id, plan_id)


@router.patch("/{plan_id}/exercises/{plan_exercise_id}", response_model=WorkoutPlanRead)
def update_plan_exercise(
    user_id: uuid.UUID,
    plan_id: int,
    plan_exercise_id: int,
    payload: PlanExerciseUpdate,
    db: SessionDep,
) -> WorkoutPlan:
    _get_plan(db, user_id, plan_id)
    plan_exercise = db.scalar(
        select(PlanExercise)
        .join(PlanDay)
        .where(
            PlanExercise.plan_exercise_id == plan_exercise_id,
            PlanDay.plan_id == plan_id,
        )
    )
    if plan_exercise is None:
        raise HTTPException(status_code=404, detail="Plan exercise not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(plan_exercise, key, value)
    db.commit()
    return _get_plan(db, user_id, plan_id)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan(user_id: uuid.UUID, plan_id: int, db: SessionDep) -> Response:
    plan = _get_plan(db, user_id, plan_id)
    db.delete(plan)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
