import uuid
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import BodyPart, BodyRecord, Exercise, WorkoutSession, WorkoutSet
from backend.schemas import DashboardRead, MetricPoint, RecentWorkout

router = APIRouter(prefix="/users/{user_id}/dashboard", tags=["dashboard"])
SessionDep = Annotated[Session, Depends(get_db)]


@router.get("", response_model=DashboardRead)
def get_dashboard(
    user_id: uuid.UUID,
    db: SessionDep,
    days: Annotated[int, Query(ge=7, le=365)] = 28,
) -> DashboardRead:
    start_date = date.today() - timedelta(days=days - 1)
    week_start = date.today() - timedelta(days=date.today().weekday())
    all_time_filters = (
        WorkoutSession.user_id == user_id,
        WorkoutSession.status == "completed",
    )
    base_filters = (
        WorkoutSession.user_id == user_id,
        WorkoutSession.status == "completed",
        func.date(WorkoutSession.started_at) >= start_date,
    )

    completed_workouts = (
        db.scalar(select(func.count(WorkoutSession.session_id)).where(*base_filters)) or 0
    )
    total_completed_workouts = (
        db.scalar(select(func.count(WorkoutSession.session_id)).where(*all_time_filters)) or 0
    )
    this_week_workouts = (
        db.scalar(
            select(func.count(WorkoutSession.session_id)).where(
                *all_time_filters,
                func.date(WorkoutSession.started_at) >= week_start,
            )
        )
        or 0
    )
    working_sets, training_volume = db.execute(
        select(
            func.count(WorkoutSet.workout_set_id),
            func.coalesce(func.sum(WorkoutSet.weight_kg * WorkoutSet.reps), 0),
        )
        .join(WorkoutSession, WorkoutSession.session_id == WorkoutSet.session_id)
        .where(*base_filters, WorkoutSet.is_warmup.is_(False))
    ).one()
    total_training_volume = db.scalar(
        select(func.coalesce(func.sum(WorkoutSet.weight_kg * WorkoutSet.reps), 0))
        .join(WorkoutSession, WorkoutSession.session_id == WorkoutSet.session_id)
        .where(*all_time_filters, WorkoutSet.is_warmup.is_(False))
    )

    weights = db.execute(
        select(BodyRecord.recorded_on, BodyRecord.weight_kg)
        .where(BodyRecord.user_id == user_id)
        .order_by(BodyRecord.recorded_on)
    ).all()
    latest_weight = float(weights[-1].weight_kg) if weights else None
    weight_change = (
        round(float(weights[-1].weight_kg - weights[-2].weight_kg), 2)
        if len(weights) >= 2
        else None
    )

    most_body_part = db.execute(
        select(BodyPart.name_en, func.count(WorkoutSet.workout_set_id).label("set_count"))
        .join(Exercise, Exercise.body_part_id == BodyPart.body_part_id)
        .join(WorkoutSet, WorkoutSet.exercise_id == Exercise.exercise_id)
        .join(WorkoutSession, WorkoutSession.session_id == WorkoutSet.session_id)
        .where(*base_filters, WorkoutSet.is_warmup.is_(False))
        .group_by(BodyPart.body_part_id, BodyPart.name_en)
        .order_by(desc("set_count"), BodyPart.name_en)
        .limit(1)
    ).first()
    most_exercise = db.execute(
        select(Exercise.exercise_name, func.count(WorkoutSet.workout_set_id).label("set_count"))
        .join(WorkoutSet, WorkoutSet.exercise_id == Exercise.exercise_id)
        .join(WorkoutSession, WorkoutSession.session_id == WorkoutSet.session_id)
        .where(*base_filters, WorkoutSet.is_warmup.is_(False))
        .group_by(Exercise.exercise_id, Exercise.exercise_name)
        .order_by(desc("set_count"), Exercise.exercise_name)
        .limit(1)
    ).first()

    dialect = db.bind.dialect.name if db.bind is not None else "postgresql"
    week_expr = (
        func.strftime("%Y-%W", WorkoutSession.started_at)
        if dialect == "sqlite"
        else func.to_char(func.date_trunc("week", WorkoutSession.started_at), "YYYY-MM-DD")
    )
    weekly_rows = db.execute(
        select(
            week_expr.label("week"),
            func.coalesce(func.sum(WorkoutSet.weight_kg * WorkoutSet.reps), 0).label("volume"),
        )
        .join(WorkoutSet, WorkoutSet.session_id == WorkoutSession.session_id)
        .where(*base_filters, WorkoutSet.is_warmup.is_(False))
        .group_by(week_expr)
        .order_by(week_expr)
    ).all()

    recent_rows = db.execute(
        select(
            WorkoutSession.session_id,
            WorkoutSession.session_name,
            WorkoutSession.started_at,
            func.count(WorkoutSet.workout_set_id).label("set_count"),
            func.coalesce(func.sum(WorkoutSet.weight_kg * WorkoutSet.reps), 0).label("volume"),
        )
        .outerjoin(WorkoutSet, WorkoutSet.session_id == WorkoutSession.session_id)
        .where(*base_filters)
        .group_by(
            WorkoutSession.session_id,
            WorkoutSession.session_name,
            WorkoutSession.started_at,
        )
        .order_by(WorkoutSession.started_at.desc())
        .limit(6)
    ).all()

    return DashboardRead(
        this_week_workouts=this_week_workouts,
        total_completed_workouts=total_completed_workouts,
        total_training_volume_kg=float(total_training_volume or 0),
        completed_workouts=completed_workouts,
        working_sets=working_sets or 0,
        training_volume_kg=float(training_volume or 0),
        latest_weight_kg=latest_weight,
        weight_change_kg=weight_change,
        most_trained_body_part=most_body_part.name_en if most_body_part else None,
        most_used_exercise=most_exercise.exercise_name if most_exercise else None,
        weekly_volume=[
            MetricPoint(label=str(row.week), value=float(row.volume)) for row in weekly_rows
        ],
        weight_history=[
            MetricPoint(label=row.recorded_on.isoformat(), value=float(row.weight_kg))
            for row in weights
        ],
        recent_workouts=[
            RecentWorkout(
                session_id=row.session_id,
                session_name=row.session_name,
                started_at=row.started_at,
                set_count=row.set_count,
                volume_kg=float(row.volume),
            )
            for row in recent_rows
        ],
    )
