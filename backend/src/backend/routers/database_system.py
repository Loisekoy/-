import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, distinct, func, select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import (
    Base,
    BodyPart,
    Exercise,
    WorkoutSession,
    WorkoutSet,
)
from backend.schemas import (
    DatabaseColumnRead,
    DatabaseOverviewRead,
    DatabaseQueryExampleRead,
    DatabaseRelationshipRead,
    DatabaseTableRead,
)

router = APIRouter(prefix="/database", tags=["database"])
SessionDep = Annotated[Session, Depends(get_db)]

TABLE_ORDER = [
    "admins",
    "users",
    "training_goals",
    "body_parts",
    "user_body_parts",
    "exercises",
    "workout_plans",
    "plan_days",
    "plan_exercises",
    "workout_sessions",
    "session_plan_days",
    "workout_sets",
    "body_records",
]

RELATIONSHIP_LABELS = {
    ("user_body_parts", "user_id"): (
        "User 1:N User_Body_Parts; junction table for User M:N Body_Part"
    ),
    (
        "user_body_parts",
        "body_part_id",
    ): "Body_Part 1:N User_Body_Parts; junction table for User M:N Body_Part",
    ("exercises", "body_part_id"): "Body_Part 1:N Exercise",
    ("users", "training_goal_id"): "Training_Goal 1:N User",
    ("workout_plans", "user_id"): "User 1:N Workout_Plan",
    ("workout_plans", "training_goal_id"): "Training_Goal 1:N Workout_Plan",
    ("plan_days", "plan_id"): "Workout_Plan 1:N Plan_Day",
    ("plan_exercises", "plan_day_id"): "Plan_Day 1:N Plan_Exercise",
    ("plan_exercises", "exercise_id"): "Exercise 1:N Plan_Exercise",
    ("workout_sessions", "user_id"): "User 1:N Workout_Session",
    ("session_plan_days", "session_id"): "Workout_Session 1:1 Session_Plan_Day",
    ("session_plan_days", "plan_day_id"): "Plan_Day 1:N Session_Plan_Day",
    ("workout_sets", "session_id"): "Workout_Session 1:N Workout_Set",
    ("workout_sets", "exercise_id"): "Exercise 1:N Workout_Set",
    ("body_records", "user_id"): "User 1:N Body_Record",
}

NORMALIZATION_NOTES = [
    (
        "1NF：所有欄位皆為 atomic values；使用 user_body_parts junction table，"
        "沒有把多個部位塞進同一個 VARCHAR。"
    ),
    (
        "2NF：複合主鍵資料表 user_body_parts 的非鍵屬性 selected_at "
        "依賴完整主鍵 user_id + body_part_id。"
    ),
    (
        "3NF：Training Goal、Body Part、Exercise 等參考資料獨立成表；"
        "User 不重複儲存 goal/body-part 名稱。"
    ),
    (
        "Referential Integrity：所有交易資料透過 Foreign Key 連回主資料表，"
        "並使用 CASCADE / RESTRICT 保護資料一致性。"
    ),
]


def _serialize(value: object) -> str | int | float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (int, float, str)):
        return value
    return str(value)


def _table_count(db: Session, table_name: str) -> int:
    table = Base.metadata.tables[table_name]
    return int(db.scalar(select(func.count()).select_from(table)) or 0)


def _tables(db: Session) -> list[DatabaseTableRead]:
    dialect = db.bind.dialect if db.bind is not None else None
    result: list[DatabaseTableRead] = []
    for table_name in TABLE_ORDER:
        table = Base.metadata.tables[table_name]
        primary_keys = {column.name for column in table.primary_key.columns}
        columns: list[DatabaseColumnRead] = []
        for column in table.columns:
            foreign_key = next(iter(column.foreign_keys), None)
            data_type = (
                column.type.compile(dialect=dialect) if dialect is not None else str(column.type)
            )
            columns.append(
                DatabaseColumnRead(
                    column_name=column.name,
                    data_type=data_type,
                    is_primary_key=column.name in primary_keys,
                    is_nullable=column.nullable,
                    foreign_key=(
                        f"{foreign_key.column.table.name}.{foreign_key.column.name}"
                        if foreign_key is not None
                        else None
                    ),
                )
            )
        result.append(
            DatabaseTableRead(
                table_name=table_name,
                row_count=_table_count(db, table_name),
                columns=columns,
            )
        )
    return result


def _relationships() -> list[DatabaseRelationshipRead]:
    relationships: list[DatabaseRelationshipRead] = []
    for table_name in TABLE_ORDER:
        table = Base.metadata.tables[table_name]
        for column in table.columns:
            for foreign_key in column.foreign_keys:
                relationships.append(
                    DatabaseRelationshipRead(
                        from_table=table_name,
                        from_column=column.name,
                        to_table=foreign_key.column.table.name,
                        to_column=foreign_key.column.name,
                        relationship_type=RELATIONSHIP_LABELS.get(
                            (table_name, column.name), "N:1"
                        ),
                        on_delete=foreign_key.ondelete,
                    )
                )
    return relationships


def _result_rows(rows: object) -> list[dict[str, str | int | float | None]]:
    return [
        {key: _serialize(value) for key, value in row._mapping.items()}  # noqa: SLF001
        for row in rows
    ]


@router.get("/overview", response_model=DatabaseOverviewRead)
def database_overview(
    db: SessionDep,
    user_id: Annotated[uuid.UUID | None, Query()] = None,
) -> DatabaseOverviewRead:
    exercise_join_rows = db.execute(
        select(
            Exercise.exercise_name.label("exercise"),
            BodyPart.name_en.label("body_part"),
            Exercise.difficulty_level.label("difficulty"),
            Exercise.equipment,
            Exercise.image_url,
            Exercise.gif_url,
        )
        .join(BodyPart, BodyPart.body_part_id == Exercise.body_part_id)
        .where(Exercise.is_active.is_(True))
        .order_by(BodyPart.display_order, Exercise.exercise_name)
        .limit(8)
    ).all()

    group_by_body_part_rows = db.execute(
        select(
            BodyPart.name_en.label("body_part"),
            func.count(Exercise.exercise_id).label("exercise_count"),
            func.sum(case((Exercise.is_active.is_(True), 1), else_=0)).label(
                "active_exercise_count"
            ),
        )
        .join(Exercise, Exercise.body_part_id == BodyPart.body_part_id)
        .group_by(BodyPart.body_part_id, BodyPart.name_en, BodyPart.display_order)
        .order_by(BodyPart.display_order)
    ).all()

    volume_statement = (
        select(
            BodyPart.name_en.label("body_part"),
            func.count(distinct(WorkoutSession.session_id)).label("completed_workouts"),
            func.count(WorkoutSet.workout_set_id).label("working_sets"),
            func.coalesce(func.sum(WorkoutSet.weight_kg * WorkoutSet.reps), 0).label(
                "training_volume_kg"
            ),
        )
        .join(Exercise, Exercise.body_part_id == BodyPart.body_part_id)
        .join(WorkoutSet, WorkoutSet.exercise_id == Exercise.exercise_id)
        .join(WorkoutSession, WorkoutSession.session_id == WorkoutSet.session_id)
        .where(WorkoutSession.status == "completed", WorkoutSet.is_warmup.is_(False))
        .group_by(BodyPart.body_part_id, BodyPart.name_en)
        .order_by(func.coalesce(func.sum(WorkoutSet.weight_kg * WorkoutSet.reps), 0).desc())
        .limit(8)
    )
    if user_id is not None:
        volume_statement = volume_statement.where(WorkoutSession.user_id == user_id)
    volume_by_body_part_rows = db.execute(volume_statement).all()

    popular_exercise_statement = (
        select(
            Exercise.exercise_name.label("exercise"),
            BodyPart.name_en.label("body_part"),
            func.count(WorkoutSet.workout_set_id).label("sets"),
            func.coalesce(func.sum(WorkoutSet.weight_kg * WorkoutSet.reps), 0).label(
                "volume_kg"
            ),
        )
        .join(WorkoutSet, WorkoutSet.exercise_id == Exercise.exercise_id)
        .join(WorkoutSession, WorkoutSession.session_id == WorkoutSet.session_id)
        .join(BodyPart, BodyPart.body_part_id == Exercise.body_part_id)
        .where(WorkoutSession.status == "completed", WorkoutSet.is_warmup.is_(False))
        .group_by(Exercise.exercise_id, Exercise.exercise_name, BodyPart.name_en)
        .order_by(func.count(WorkoutSet.workout_set_id).desc(), Exercise.exercise_name)
        .limit(8)
    )
    if user_id is not None:
        popular_exercise_statement = popular_exercise_statement.where(
            WorkoutSession.user_id == user_id
        )
    popular_exercise_rows = db.execute(popular_exercise_statement).all()

    return DatabaseOverviewRead(
        tables=_tables(db),
        relationships=_relationships(),
        query_examples=[
            DatabaseQueryExampleRead(
                title="JOIN：Exercise 與 Body Part",
                sql=(
                    "SELECT e.exercise_name, bp.name_en AS body_part, "
                    "e.difficulty_level, e.equipment, e.image_url, e.gif_url "
                    "FROM exercises e JOIN body_parts bp ON e.body_part_id = bp.body_part_id "
                    "WHERE e.is_active = TRUE ORDER BY bp.display_order, e.exercise_name LIMIT 8;"
                ),
                rows=_result_rows(exercise_join_rows),
            ),
            DatabaseQueryExampleRead(
                title="GROUP BY：各 Body Part 的 Exercise 數量",
                sql=(
                    "SELECT bp.name_en AS body_part, COUNT(e.exercise_id) AS exercise_count, "
                    "SUM(CASE WHEN e.is_active THEN 1 ELSE 0 END) AS active_exercise_count "
                    "FROM body_parts bp JOIN exercises e ON e.body_part_id = bp.body_part_id "
                    "GROUP BY bp.body_part_id, bp.name_en, bp.display_order "
                    "ORDER BY bp.display_order;"
                ),
                rows=_result_rows(group_by_body_part_rows),
            ),
            DatabaseQueryExampleRead(
                title="Aggregate：Training Volume by Body Part",
                sql=(
                    "SELECT bp.name_en AS body_part, "
                    "COUNT(DISTINCT ws.session_id) AS completed_workouts, "
                    "COUNT(wset.workout_set_id) AS working_sets, "
                    "SUM(wset.weight_kg * wset.reps) AS training_volume_kg "
                    "FROM body_parts bp JOIN exercises e ON e.body_part_id = bp.body_part_id "
                    "JOIN workout_sets wset ON wset.exercise_id = e.exercise_id "
                    "JOIN workout_sessions ws ON ws.session_id = wset.session_id "
                    "WHERE ws.status = 'completed' GROUP BY bp.body_part_id, bp.name_en "
                    "ORDER BY training_volume_kg DESC;"
                ),
                rows=_result_rows(volume_by_body_part_rows),
            ),
            DatabaseQueryExampleRead(
                title="Aggregate：Most Used Exercises",
                sql=(
                    "SELECT e.exercise_name, bp.name_en AS body_part, "
                    "COUNT(wset.workout_set_id) AS sets, "
                    "SUM(wset.weight_kg * wset.reps) AS volume_kg "
                    "FROM exercises e JOIN workout_sets wset ON wset.exercise_id = e.exercise_id "
                    "JOIN workout_sessions ws ON ws.session_id = wset.session_id "
                    "JOIN body_parts bp ON bp.body_part_id = e.body_part_id "
                    "WHERE ws.status = 'completed' "
                    "GROUP BY e.exercise_id, e.exercise_name, bp.name_en "
                    "ORDER BY sets DESC, e.exercise_name LIMIT 8;"
                ),
                rows=_result_rows(popular_exercise_rows),
            ),
        ],
        normalization_notes=NORMALIZATION_NOTES,
    )
