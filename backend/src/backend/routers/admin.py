import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import String, cast, desc, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from backend.database import get_db
from backend.dependencies import get_current_admin
from backend.models import (
    Admin,
    BodyPart,
    BodyRecord,
    Exercise,
    PlanDay,
    PlanExercise,
    TrainingGoal,
    User,
    UserBodyPart,
    WorkoutPlan,
    WorkoutSession,
    WorkoutSet,
)
from backend.schemas import (
    AdminDashboardRead,
    AdminLoginRequest,
    AdminLoginResponse,
    AdminPlanSummaryRead,
    AdminRead,
    AdminRecentUserRead,
    AdminStatisticsRead,
    AdminUserDetailRead,
    AdminUserListItemRead,
    AdminWorkoutSessionSummaryRead,
    BodyRecordRead,
    ExerciseRead,
    MetricPoint,
    PaginatedAdminUsersRead,
    UserProfileRead,
)
from backend.security import create_admin_token, verify_password

router = APIRouter(prefix="/admin", tags=["admin"])
SessionDep = Annotated[Session, Depends(get_db)]
CurrentAdminDep = Annotated[Admin, Depends(get_current_admin)]


def _goal_name(row: User) -> str:
    return row.training_goal.goal_name if row.training_goal else "—"


def _latest_weight(db: Session, user_id: uuid.UUID) -> Decimal | None:
    return db.scalar(
        select(BodyRecord.weight_kg)
        .where(BodyRecord.user_id == user_id)
        .order_by(BodyRecord.recorded_on.desc())
        .limit(1)
    )


def _preferred_names(user: User) -> list[str]:
    return [
        f"{item.body_part.name_en} {item.body_part.name_zh}"
        for item in user.preferred_body_parts
    ]


def _user_loader():
    return (
        joinedload(User.training_goal),
        selectinload(User.preferred_body_parts).joinedload(UserBodyPart.body_part),
    )


def _plan_loader():
    return (
        joinedload(WorkoutPlan.training_goal),
        selectinload(WorkoutPlan.days)
        .selectinload(PlanDay.exercises)
        .joinedload(PlanExercise.exercise)
        .joinedload(Exercise.body_part),
    )


@router.post("/login", response_model=AdminLoginResponse)
def admin_login(payload: AdminLoginRequest, db: SessionDep) -> AdminLoginResponse:
    admin = db.scalar(select(Admin).where(Admin.username == payload.username.strip()))
    invalid_credentials = (
        admin is None
        or not admin.is_active
        or not verify_password(payload.password, admin.password_hash)
    )
    if invalid_credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin username or password",
        )
    admin.last_login_at = datetime.now(UTC)
    db.commit()
    db.refresh(admin)
    return AdminLoginResponse(
        access_token=create_admin_token(admin.admin_id, admin.username),
        admin=admin,
    )


@router.get("/me", response_model=AdminRead)
def admin_me(current_admin: CurrentAdminDep) -> Admin:
    return current_admin


@router.get("/dashboard", response_model=AdminDashboardRead)
def admin_dashboard(db: SessionDep, _admin: CurrentAdminDep) -> AdminDashboardRead:
    today = date.today()
    total_users = db.scalar(select(func.count()).select_from(User)) or 0
    new_users_today = (
        db.scalar(select(func.count()).select_from(User).where(func.date(User.created_at) == today))
        or 0
    )
    total_workouts = db.scalar(select(func.count()).select_from(WorkoutSession)) or 0
    total_workout_plans = db.scalar(select(func.count()).select_from(WorkoutPlan)) or 0
    average_age = db.scalar(select(func.avg(User.age)))
    average_training_days = db.scalar(select(func.avg(User.training_days_per_week)))
    total_volume = db.scalar(
        select(func.coalesce(func.sum(WorkoutSet.weight_kg * WorkoutSet.reps), 0))
        .join(WorkoutSession, WorkoutSession.session_id == WorkoutSet.session_id)
        .where(WorkoutSession.status == "completed", WorkoutSet.is_warmup.is_(False))
    )
    recent_users = db.scalars(
        select(User)
        .options(joinedload(User.training_goal))
        .order_by(User.created_at.desc())
        .limit(8)
    ).all()
    return AdminDashboardRead(
        total_users=total_users,
        new_users_today=new_users_today,
        total_workouts=total_workouts,
        total_workout_plans=total_workout_plans,
        average_age=round(float(average_age), 2) if average_age is not None else None,
        average_training_days=(
            round(float(average_training_days), 2) if average_training_days is not None else None
        ),
        total_training_volume=float(total_volume or 0),
        recent_users=[
            AdminRecentUserRead(
                user_id=user.user_id,
                name=user.name,
                age=user.age,
                goal=_goal_name(user),
                experience=user.training_experience,
                joined=user.created_at,
            )
            for user in recent_users
        ],
    )


@router.get("/users", response_model=PaginatedAdminUsersRead)
def admin_list_users(
    db: SessionDep,
    _admin: CurrentAdminDep,
    search: Annotated[str | None, Query(max_length=100)] = None,
    training_goal_id: int | None = None,
    experience: str | None = None,
    sort: str = "created_desc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=5, le=100)] = 10,
) -> PaginatedAdminUsersRead:
    statement = select(User).options(*_user_loader())
    count_statement = select(func.count()).select_from(User)
    filters = []
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(or_(User.name.ilike(pattern), cast(User.user_id, String).ilike(pattern)))
    if training_goal_id is not None:
        filters.append(User.training_goal_id == training_goal_id)
    if experience:
        filters.append(User.training_experience == experience)
    if filters:
        statement = statement.where(*filters)
        count_statement = count_statement.where(*filters)
    sort_map = {
        "created_desc": User.created_at.desc(),
        "created_asc": User.created_at.asc(),
        "name_asc": User.name.asc(),
        "age_desc": User.age.desc(),
        "age_asc": User.age.asc(),
    }
    statement = statement.order_by(sort_map.get(sort, User.created_at.desc()))
    total = db.scalar(count_statement) or 0
    users = db.scalars(statement.offset((page - 1) * page_size).limit(page_size)).unique().all()
    return PaginatedAdminUsersRead(
        items=[
            AdminUserListItemRead(
                user_id=user.user_id,
                name=user.name,
                gender=user.gender,
                age=user.age,
                height_cm=user.height_cm,
                latest_weight_kg=_latest_weight(db, user.user_id),
                training_goal=_goal_name(user),
                training_experience=user.training_experience,
                training_days_per_week=user.training_days_per_week,
                training_duration_minutes=user.training_duration_minutes,
                preferred_body_parts=_preferred_names(user),
                created_at=user.created_at,
            )
            for user in users
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/users/{user_id}", response_model=AdminUserDetailRead)
def admin_user_detail(
    user_id: uuid.UUID,
    db: SessionDep,
    _admin: CurrentAdminDep,
) -> AdminUserDetailRead:
    user = db.scalar(select(User).options(*_user_loader()).where(User.user_id == user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    latest_weight = _latest_weight(db, user.user_id)
    if latest_weight is None:
        raise HTTPException(status_code=409, detail="User has no weight record")
    plans = db.scalars(
        select(WorkoutPlan)
        .options(*_plan_loader())
        .where(WorkoutPlan.user_id == user_id)
        .order_by(WorkoutPlan.generated_at.desc())
    ).unique().all()
    history_rows = db.execute(
        select(
            WorkoutSession.session_id,
            WorkoutSession.session_name,
            WorkoutSession.status,
            WorkoutSession.started_at,
            WorkoutSession.ended_at,
            func.count(WorkoutSet.workout_set_id).label("set_count"),
            func.coalesce(func.sum(WorkoutSet.weight_kg * WorkoutSet.reps), 0).label("volume"),
        )
        .outerjoin(WorkoutSet, WorkoutSet.session_id == WorkoutSession.session_id)
        .where(WorkoutSession.user_id == user_id)
        .group_by(
            WorkoutSession.session_id,
            WorkoutSession.session_name,
            WorkoutSession.status,
            WorkoutSession.started_at,
            WorkoutSession.ended_at,
        )
        .order_by(WorkoutSession.started_at.desc())
        .limit(20)
    ).all()
    body_records = db.scalars(
        select(BodyRecord).where(BodyRecord.user_id == user_id).order_by(BodyRecord.recorded_on)
    ).all()
    return AdminUserDetailRead(
        profile=UserProfileRead(
            user_id=user.user_id,
            name=user.name,
            gender=user.gender,
            age=user.age,
            height_cm=user.height_cm,
            training_experience=user.training_experience,
            training_goal=user.training_goal,
            training_days_per_week=user.training_days_per_week,
            training_duration_minutes=user.training_duration_minutes,
            preferred_body_parts=[item.body_part for item in user.preferred_body_parts],
            latest_weight_kg=latest_weight,
            created_at=user.created_at,
            updated_at=user.updated_at,
        ),
        workout_plans=[
            AdminPlanSummaryRead(
                plan_id=plan.plan_id,
                plan_name=plan.plan_name,
                status=plan.status,
                generated_at=plan.generated_at,
                days=plan.days,
            )
            for plan in plans
        ],
        workout_history=[
            AdminWorkoutSessionSummaryRead(
                session_id=row.session_id,
                session_name=row.session_name,
                status=row.status,
                started_at=row.started_at,
                ended_at=row.ended_at,
                set_count=row.set_count,
                volume_kg=float(row.volume),
            )
            for row in history_rows
        ],
        weight_history=[BodyRecordRead.model_validate(record) for record in body_records],
    )


@router.get("/statistics", response_model=AdminStatisticsRead)
def admin_statistics(db: SessionDep, _admin: CurrentAdminDep) -> AdminStatisticsRead:
    total_users = db.scalar(select(func.count()).select_from(User)) or 0
    users_by_goal = db.execute(
        select(TrainingGoal.goal_name, func.count(User.user_id))
        .outerjoin(User, User.training_goal_id == TrainingGoal.training_goal_id)
        .group_by(TrainingGoal.training_goal_id, TrainingGoal.goal_name)
        .order_by(TrainingGoal.training_goal_id)
    ).all()
    users_by_experience = db.execute(
        select(User.training_experience, func.count(User.user_id))
        .group_by(User.training_experience)
        .order_by(User.training_experience)
    ).all()
    selected_parts = db.execute(
        select(BodyPart.name_en, func.count(UserBodyPart.user_id))
        .join(UserBodyPart, UserBodyPart.body_part_id == BodyPart.body_part_id)
        .group_by(BodyPart.body_part_id, BodyPart.name_en, BodyPart.display_order)
        .order_by(desc(func.count(UserBodyPart.user_id)), BodyPart.display_order)
        .limit(8)
    ).all()
    popular_exercises = db.execute(
        select(Exercise.exercise_name, func.count(WorkoutSet.workout_set_id))
        .join(WorkoutSet, WorkoutSet.exercise_id == Exercise.exercise_id)
        .join(WorkoutSession, WorkoutSession.session_id == WorkoutSet.session_id)
        .where(WorkoutSession.status == "completed", WorkoutSet.is_warmup.is_(False))
        .group_by(Exercise.exercise_id, Exercise.exercise_name)
        .order_by(desc(func.count(WorkoutSet.workout_set_id)), Exercise.exercise_name)
        .limit(8)
    ).all()
    avg_training_days = db.scalar(select(func.avg(User.training_days_per_week)))
    total_sessions = db.scalar(select(func.count()).select_from(WorkoutSession)) or 0
    total_volume = db.scalar(
        select(func.coalesce(func.sum(WorkoutSet.weight_kg * WorkoutSet.reps), 0))
        .join(WorkoutSession, WorkoutSession.session_id == WorkoutSet.session_id)
        .where(WorkoutSession.status == "completed", WorkoutSet.is_warmup.is_(False))
    )
    return AdminStatisticsRead(
        total_users=total_users,
        users_by_training_goal=[
            MetricPoint(label=row[0], value=float(row[1])) for row in users_by_goal
        ],
        users_by_experience_level=[
            MetricPoint(label=row[0] or "unknown", value=float(row[1]))
            for row in users_by_experience
        ],
        most_selected_body_parts=[
            MetricPoint(label=row[0], value=float(row[1])) for row in selected_parts
        ],
        most_popular_exercises=[
            MetricPoint(label=row[0], value=float(row[1])) for row in popular_exercises
        ],
        average_training_days_per_week=(
            round(float(avg_training_days), 2) if avg_training_days is not None else None
        ),
        total_workout_sessions=total_sessions,
        total_training_volume=float(total_volume or 0),
    )


@router.get("/exercises", response_model=list[ExerciseRead])
def admin_exercises(
    db: SessionDep,
    _admin: CurrentAdminDep,
    search: Annotated[str | None, Query(max_length=120)] = None,
    body_part_id: int | None = None,
    equipment: str | None = None,
) -> list[Exercise]:
    statement = select(Exercise).options(joinedload(Exercise.body_part))
    if search:
        pattern = f"%{search.strip()}%"
        statement = statement.where(
            or_(Exercise.exercise_name.ilike(pattern), Exercise.description.ilike(pattern))
        )
    if body_part_id is not None:
        statement = statement.where(Exercise.body_part_id == body_part_id)
    if equipment:
        statement = statement.where(Exercise.equipment.ilike(f"%{equipment.strip()}%"))
    return list(db.scalars(statement.order_by(Exercise.exercise_name)).all())
