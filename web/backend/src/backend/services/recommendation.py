import json
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session, joinedload

from backend.config import get_settings
from backend.models import (
    BodyPart,
    Exercise,
    LLMGeneration,
    PlanDay,
    PlanExercise,
    TrainingGoal,
    User,
    UserBodyPart,
    WorkoutPlan,
)

RULE_ALGORITHM_VERSION = "rules-v1"
FALLBACK_ALGORITHM_VERSION = "rules-v1-fallback"

BASE_SPLITS: dict[int, list[list[str]]] = {
    2: [
        ["chest", "back", "legs", "core"],
        ["shoulders", "glutes", "biceps", "triceps"],
    ],
    3: [
        ["chest", "shoulders", "triceps", "core"],
        ["back", "biceps", "core"],
        ["legs", "glutes", "core"],
    ],
    4: [
        ["chest", "shoulders", "triceps"],
        ["back", "biceps"],
        ["legs", "glutes", "core"],
        ["chest", "back", "shoulders", "core"],
    ],
    5: [
        ["chest", "shoulders", "triceps"],
        ["back", "biceps"],
        ["legs", "glutes", "core"],
        ["chest", "back", "shoulders", "biceps", "triceps"],
        ["legs", "glutes", "core"],
    ],
    6: [
        ["chest", "shoulders", "triceps"],
        ["back", "biceps", "core"],
        ["legs", "glutes", "core"],
        ["chest", "shoulders", "triceps"],
        ["back", "biceps", "core"],
        ["legs", "glutes", "core"],
    ],
}

DURATION_CAPACITY = {30: 4, 45: 5, 60: 6, 90: 8}
ACCESSORY_CODES = {"biceps", "triceps"}
EXPERIENCE_RANK = {"beginner": 0, "intermediate": 1, "advanced": 2}


class RecommendationError(ValueError):
    pass


class LLMRecommendationError(RecommendationError):
    pass


@dataclass(frozen=True)
class ExerciseCandidate:
    exercise_id: int
    body_part_code: str
    difficulty_level: str
    movement_type: str


@dataclass(frozen=True)
class PlannedExercise:
    exercise_id: int
    exercise_order: int
    target_sets: int
    target_reps: int
    rest_seconds: int
    notes: str | None = None


@dataclass(frozen=True)
class PlannedDay:
    day_number: int
    day_name: str
    focus_summary: str
    exercises: list[PlannedExercise]


@dataclass(frozen=True)
class PlannedWorkout:
    plan_name: str
    days: list[PlannedDay]


@dataclass(frozen=True)
class RecommendationContext:
    user: User
    goal: TrainingGoal
    preferred_parts: list[BodyPart]
    exercises: list[Exercise]


def build_focus_schedule(
    days_per_week: int, duration_minutes: int, preferred_codes: list[str]
) -> list[list[str]]:
    """Return deterministic body-part slots for each Plan Day."""
    if days_per_week not in BASE_SPLITS:
        raise RecommendationError("Training days must be between 2 and 6")
    if duration_minutes not in DURATION_CAPACITY:
        raise RecommendationError("Training duration must be 30, 45, 60, or 90 minutes")
    if not preferred_codes:
        raise RecommendationError("At least one preferred body part is required")

    capacity = DURATION_CAPACITY[duration_minutes]
    schedule = [focus.copy() for focus in BASE_SPLITS[days_per_week]]

    # Give every preferred part exposure on at least two different days when possible.
    for preferred in preferred_codes:
        present_days = [index for index, focus in enumerate(schedule) if preferred in focus]
        if len(present_days) >= min(2, days_per_week):
            continue
        target_candidates = [
            index
            for index, focus in enumerate(schedule)
            if preferred not in focus and index not in present_days
        ]
        if not target_candidates:
            continue
        target = min(target_candidates, key=lambda index: (len(schedule[index]), index))
        if len(schedule[target]) < capacity:
            schedule[target].append(preferred)
            continue

        replacement = next(
            (
                index
                for index in range(len(schedule[target]) - 1, -1, -1)
                if schedule[target][index] in ACCESSORY_CODES
                and schedule[target][index] not in preferred_codes
            ),
            len(schedule[target]) - 1,
        )
        schedule[target][replacement] = preferred

    # Fill the remaining time with preferred work, then the day's original focus.
    for day_index, focus in enumerate(schedule):
        fill_order = list(dict.fromkeys(preferred_codes + BASE_SPLITS[days_per_week][day_index]))
        fill_index = 0
        while len(focus) < capacity:
            focus.append(fill_order[fill_index % len(fill_order)])
            fill_index += 1
        del focus[capacity:]

    return schedule


def difficulty_is_eligible(user_experience: str, exercise_difficulty: str) -> bool:
    if user_experience == "beginner":
        return exercise_difficulty in {"beginner", "intermediate"}
    if user_experience == "intermediate":
        return exercise_difficulty in {"beginner", "intermediate"}
    return exercise_difficulty in EXPERIENCE_RANK


def score_exercise(
    candidate: ExerciseCandidate,
    *,
    experience: str,
    preferred_codes: set[str],
    early_slot: bool,
    previous_day_exercise_ids: set[int],
    weekly_usage: int,
) -> int:
    score = 0
    if candidate.body_part_code in preferred_codes:
        score += 30
    if candidate.difficulty_level == experience:
        score += 20
    if early_slot and candidate.movement_type == "compound":
        score += 10
    if candidate.exercise_id in previous_day_exercise_ids:
        score -= 25
    score -= weekly_usage * 10
    return score


def prescription_for(
    goal: TrainingGoal, *, experience: str, movement_type: str
) -> tuple[int, int, int]:
    sets = goal.default_sets
    reps = goal.default_reps
    rest = goal.default_rest_seconds

    if goal.goal_code == "strength" and movement_type == "isolation":
        sets, reps, rest = 3, 8, 75
    if experience == "beginner":
        sets = min(sets, 3)
    return sets, reps, rest


def _rank_exercises(
    exercises: list[Exercise],
    *,
    body_part_code: str,
    experience: str,
    preferred_codes: set[str],
    early_slot: bool,
    previous_day_ids: set[int],
    weekly_usage: Counter[int],
    excluded_ids: set[int],
) -> list[Exercise]:
    matching = [
        exercise
        for exercise in exercises
        if exercise.body_part.body_part_code == body_part_code
        and exercise.exercise_id not in excluded_ids
        and difficulty_is_eligible(experience, exercise.difficulty_level)
    ]
    if not matching:
        matching = [
            exercise
            for exercise in exercises
            if exercise.body_part.body_part_code == body_part_code
            and exercise.exercise_id not in excluded_ids
        ]

    def sort_key(exercise: Exercise) -> tuple[int, int]:
        candidate = ExerciseCandidate(
            exercise_id=exercise.exercise_id,
            body_part_code=exercise.body_part.body_part_code,
            difficulty_level=exercise.difficulty_level,
            movement_type=exercise.movement_type,
        )
        score = score_exercise(
            candidate,
            experience=experience,
            preferred_codes=preferred_codes,
            early_slot=early_slot,
            previous_day_exercise_ids=previous_day_ids,
            weekly_usage=weekly_usage[exercise.exercise_id],
        )
        return (-score, exercise.exercise_id)

    return sorted(matching, key=sort_key)


def _load_context(db: Session, user_id: object) -> RecommendationContext:
    user = db.get(User, user_id)
    if user is None:
        raise RecommendationError("User not found")

    goal = db.get(TrainingGoal, user.training_goal_id)
    if goal is None:
        raise RecommendationError("Training goal not found")

    preferred_parts = db.scalars(
        select(BodyPart)
        .join(UserBodyPart, UserBodyPart.body_part_id == BodyPart.body_part_id)
        .where(UserBodyPart.user_id == user.user_id, BodyPart.is_active.is_(True))
        .order_by(BodyPart.display_order)
    ).all()
    if not preferred_parts:
        raise RecommendationError("At least one preferred body part is required")

    exercises = list(
        db.scalars(
            select(Exercise)
            .options(joinedload(Exercise.body_part))
            .where(Exercise.is_active.is_(True))
            .order_by(Exercise.exercise_id)
        ).all()
    )
    if not exercises:
        raise RecommendationError("Exercise catalogue is empty")

    return RecommendationContext(
        user=user,
        goal=goal,
        preferred_parts=list(preferred_parts),
        exercises=exercises,
    )


def _body_part_names(db: Session) -> dict[str, str]:
    return {
        part.body_part_code: part.name_zh
        for part in db.scalars(select(BodyPart).where(BodyPart.is_active.is_(True))).all()
    }


def _build_rule_spec(db: Session, context: RecommendationContext) -> PlannedWorkout:
    user = context.user
    goal = context.goal
    preferred_codes = [part.body_part_code for part in context.preferred_parts]
    schedule = build_focus_schedule(
        user.training_days_per_week,
        user.training_duration_minutes,
        preferred_codes,
    )
    body_part_names = _body_part_names(db)
    preferred_set = set(preferred_codes)
    weekly_usage: Counter[int] = Counter()
    previous_day_ids: set[int] = set()
    planned_days: list[PlannedDay] = []

    for day_number, body_part_slots in enumerate(schedule, start=1):
        unique_focus = list(dict.fromkeys(body_part_slots))
        focus_summary = "＋".join(body_part_names.get(code, code.title()) for code in unique_focus)
        selected_ids: set[int] = set()
        current_day_ids: set[int] = set()
        planned_exercises: list[PlannedExercise] = []

        for slot_number, code in enumerate(body_part_slots, start=1):
            ranked = _rank_exercises(
                context.exercises,
                body_part_code=code,
                experience=user.training_experience,
                preferred_codes=preferred_set,
                early_slot=slot_number <= 2,
                previous_day_ids=previous_day_ids,
                weekly_usage=weekly_usage,
                excluded_ids=selected_ids,
            )
            if not ranked:
                continue
            exercise = ranked[0]
            sets, reps, rest = prescription_for(
                goal,
                experience=user.training_experience,
                movement_type=exercise.movement_type,
            )
            planned_exercises.append(
                PlannedExercise(
                    exercise_id=exercise.exercise_id,
                    exercise_order=len(planned_exercises) + 1,
                    target_sets=sets,
                    target_reps=reps,
                    rest_seconds=rest,
                    notes="Rule-based fallback recommendation.",
                )
            )
            selected_ids.add(exercise.exercise_id)
            current_day_ids.add(exercise.exercise_id)
            weekly_usage[exercise.exercise_id] += 1

        if not planned_exercises:
            raise RecommendationError(f"No eligible exercises for Day {day_number}")
        previous_day_ids = current_day_ids
        planned_days.append(
            PlannedDay(
                day_number=day_number,
                day_name=f"Day {day_number} - {focus_summary}",
                focus_summary=focus_summary,
                exercises=planned_exercises,
            )
        )

    return PlannedWorkout(
        plan_name=f"{user.training_days_per_week} 天{goal.goal_name}訓練計畫",
        days=planned_days,
    )


def _candidate_payload(context: RecommendationContext) -> list[dict[str, Any]]:
    user = context.user
    return [
        {
            "exercise_id": exercise.exercise_id,
            "exercise_name_en": exercise.exercise_name_en or exercise.exercise_name,
            "exercise_name_zh": exercise.exercise_name_zh or exercise.exercise_name,
            "body_part_code": exercise.body_part.body_part_code,
            "body_part_zh": exercise.body_part.name_zh,
            "difficulty_level": exercise.difficulty_level,
            "equipment": exercise.equipment,
            "movement_type": exercise.movement_type,
            "target_muscles": exercise.target_muscles,
        }
        for exercise in context.exercises
        if difficulty_is_eligible(user.training_experience, exercise.difficulty_level)
    ]


def _json_schema() -> dict[str, Any]:
    exercise_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "exercise_id": {"type": "integer"},
            "target_sets": {"type": "integer", "minimum": 1, "maximum": 6},
            "target_reps": {"type": "integer", "minimum": 1, "maximum": 30},
            "rest_seconds": {"type": "integer", "minimum": 15, "maximum": 300},
            "notes": {"type": "string"},
        },
        "required": [
            "exercise_id",
            "target_sets",
            "target_reps",
            "rest_seconds",
            "notes",
        ],
    }
    day_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "day_number": {"type": "integer", "minimum": 1, "maximum": 6},
            "day_name": {"type": "string"},
            "focus_summary": {"type": "string"},
            "exercises": {"type": "array", "items": exercise_schema, "minItems": 1, "maxItems": 8},
        },
        "required": ["day_number", "day_name", "focus_summary", "exercises"],
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "plan_name": {"type": "string"},
            "days": {"type": "array", "items": day_schema, "minItems": 2, "maxItems": 6},
        },
        "required": ["plan_name", "days"],
    }


def _request_openai_plan(context: RecommendationContext) -> dict[str, Any]:
    settings = get_settings()
    if settings.llm_force_failure:
        raise LLMRecommendationError("LLM_FORCE_FAILURE is enabled")
    if not settings.openai_api_key:
        raise LLMRecommendationError("OPENAI_API_KEY is not configured")

    user = context.user
    candidates = _candidate_payload(context)
    if not candidates:
        raise LLMRecommendationError("No eligible exercise candidates for LLM planning")

    request_payload = {
        "profile": {
            "age": user.age,
            "gender": user.gender,
            "height_cm": float(user.height_cm),
            "training_experience": user.training_experience,
            "training_goal": context.goal.goal_code,
            "training_goal_name": context.goal.goal_name,
            "training_days_per_week": user.training_days_per_week,
            "training_duration_minutes": user.training_duration_minutes,
            "preferred_body_parts": [
                {"code": part.body_part_code, "name_zh": part.name_zh, "name_en": part.name_en}
                for part in context.preferred_parts
            ],
        },
        "exercise_candidates": candidates,
        "rules": [
            "Use only exercise_id values from exercise_candidates.",
            "Preferred body parts should appear more often, but include other major regions.",
            (
                "Each day should fit the duration capacity and avoid duplicated exercises "
                "within the same day."
            ),
            "Return Traditional Chinese day names and concise notes.",
        ],
    }
    body = {
        "model": settings.openai_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a safe fitness plan generator. Return only a validated JSON "
                    "workout plan. Never invent exercise IDs."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(request_payload, ensure_ascii=False),
            },
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "fitness_workout_plan",
                "strict": True,
                "schema": _json_schema(),
            },
        },
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "fitness-tracking-management-system/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.llm_timeout_seconds) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise LLMRecommendationError(f"OpenAI request failed: {exc}") from exc

    try:
        content = response_payload["choices"][0]["message"]["content"]
        parsed = json.loads(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise LLMRecommendationError("OpenAI response did not contain valid JSON content") from exc
    if not isinstance(parsed, dict):
        raise LLMRecommendationError("OpenAI response root must be an object")
    return parsed


def _validate_llm_payload(
    payload: dict[str, Any],
    context: RecommendationContext,
) -> PlannedWorkout:
    plan_name = payload.get("plan_name")
    days = payload.get("days")
    if not isinstance(plan_name, str) or not plan_name.strip():
        raise LLMRecommendationError("LLM plan is missing plan_name")
    if not isinstance(days, list) or len(days) != context.user.training_days_per_week:
        raise LLMRecommendationError("LLM plan day count does not match user schedule")

    exercise_map = {exercise.exercise_id: exercise for exercise in context.exercises}
    max_exercises_per_day = DURATION_CAPACITY[context.user.training_duration_minutes]
    planned_days: list[PlannedDay] = []
    seen_day_numbers: set[int] = set()

    for day in sorted(days, key=lambda item: item.get("day_number", 0)):
        if not isinstance(day, dict):
            raise LLMRecommendationError("LLM day item must be an object")
        day_number = day.get("day_number")
        day_name = day.get("day_name")
        focus_summary = day.get("focus_summary")
        exercise_items = day.get("exercises")
        if not isinstance(day_number, int) or day_number < 1 or day_number > 6:
            raise LLMRecommendationError("LLM day_number is invalid")
        if day_number in seen_day_numbers:
            raise LLMRecommendationError("LLM returned duplicate day_number")
        seen_day_numbers.add(day_number)
        if not isinstance(day_name, str) or not day_name.strip():
            day_name = f"Day {day_number}"
        if not isinstance(focus_summary, str) or not focus_summary.strip():
            focus_summary = "綜合訓練"
        if (
            not isinstance(exercise_items, list)
            or not exercise_items
            or len(exercise_items) > max_exercises_per_day
        ):
            raise LLMRecommendationError("LLM exercise count does not fit duration")

        seen_exercise_ids: set[int] = set()
        planned_exercises: list[PlannedExercise] = []
        for order, item in enumerate(exercise_items, start=1):
            if not isinstance(item, dict):
                raise LLMRecommendationError("LLM exercise item must be an object")
            exercise_id = item.get("exercise_id")
            if not isinstance(exercise_id, int) or exercise_id not in exercise_map:
                raise LLMRecommendationError("LLM used an exercise_id that is not in database")
            if exercise_id in seen_exercise_ids:
                raise LLMRecommendationError("LLM duplicated an exercise within one day")
            seen_exercise_ids.add(exercise_id)
            target_sets = item.get("target_sets")
            target_reps = item.get("target_reps")
            rest_seconds = item.get("rest_seconds")
            if not isinstance(target_sets, int) or not 1 <= target_sets <= 6:
                raise LLMRecommendationError("LLM target_sets is out of range")
            if not isinstance(target_reps, int) or not 1 <= target_reps <= 30:
                raise LLMRecommendationError("LLM target_reps is out of range")
            if not isinstance(rest_seconds, int) or not 15 <= rest_seconds <= 300:
                raise LLMRecommendationError("LLM rest_seconds is out of range")
            notes = item.get("notes")
            planned_exercises.append(
                PlannedExercise(
                    exercise_id=exercise_id,
                    exercise_order=order,
                    target_sets=target_sets,
                    target_reps=target_reps,
                    rest_seconds=rest_seconds,
                    notes=notes if isinstance(notes, str) and notes.strip() else None,
                )
            )
        planned_days.append(
            PlannedDay(
                day_number=day_number,
                day_name=day_name.strip(),
                focus_summary=focus_summary.strip(),
                exercises=planned_exercises,
            )
        )

    expected_days = set(range(1, context.user.training_days_per_week + 1))
    if seen_day_numbers != expected_days:
        raise LLMRecommendationError("LLM day numbers must be sequential from 1")
    return PlannedWorkout(plan_name=plan_name.strip(), days=planned_days)


def _record_generation(
    db: Session,
    context: RecommendationContext,
    *,
    status: str,
    provider: str,
    model: str,
    used_fallback: bool,
    error_message: str | None = None,
    response_summary: str | None = None,
) -> None:
    db.add(
        LLMGeneration(
            user_id=context.user.user_id,
            provider=provider,
            model=model,
            status=status,
            used_fallback=used_fallback,
            prompt_summary=(
                f"{context.user.training_experience}; {context.goal.goal_code}; "
                f"{context.user.training_days_per_week}d/"
                f"{context.user.training_duration_minutes}m; "
                f"preferred={','.join(part.body_part_code for part in context.preferred_parts)}"
            ),
            response_summary=response_summary,
            error_message=error_message,
        )
    )


def _insert_plan(
    db: Session,
    context: RecommendationContext,
    spec: PlannedWorkout,
    *,
    algorithm_version: str,
) -> WorkoutPlan:
    user = context.user
    db.execute(
        update(WorkoutPlan)
        .where(WorkoutPlan.user_id == user.user_id, WorkoutPlan.status == "active")
        .values(status="archived")
    )

    plan = WorkoutPlan(
        user_id=user.user_id,
        training_goal_id=user.training_goal_id,
        plan_name=spec.plan_name,
        training_days_per_week=user.training_days_per_week,
        training_duration_minutes=user.training_duration_minutes,
        algorithm_version=algorithm_version,
        status="generated",
    )
    db.add(plan)
    db.flush()

    for day in spec.days:
        plan_day = PlanDay(
            plan=plan,
            day_number=day.day_number,
            day_name=day.day_name,
            focus_summary=day.focus_summary,
        )
        db.add(plan_day)
        db.flush()

        for exercise in day.exercises:
            db.add(
                PlanExercise(
                    plan_day=plan_day,
                    exercise_id=exercise.exercise_id,
                    exercise_order=exercise.exercise_order,
                    target_sets=exercise.target_sets,
                    target_reps=exercise.target_reps,
                    rest_seconds=exercise.rest_seconds,
                    notes=exercise.notes,
                )
            )

    plan.status = "active"
    db.flush()
    return plan


def generate_plan(db: Session, user_id: object) -> WorkoutPlan:
    context = _load_context(db, user_id)
    settings = get_settings()

    try:
        llm_payload = _request_openai_plan(context)
        llm_spec = _validate_llm_payload(llm_payload, context)
    except LLMRecommendationError as exc:
        _record_generation(
            db,
            context,
            status="fallback" if "OPENAI_API_KEY" in str(exc) else "failed",
            provider="openai",
            model=settings.openai_model,
            used_fallback=True,
            error_message=str(exc),
        )
        fallback_spec = _build_rule_spec(db, context)
        return _insert_plan(
            db,
            context,
            fallback_spec,
            algorithm_version=FALLBACK_ALGORITHM_VERSION,
        )

    _record_generation(
        db,
        context,
        status="success",
        provider="openai",
        model=settings.openai_model,
        used_fallback=False,
        response_summary=f"{len(llm_spec.days)} days generated and validated",
    )
    return _insert_plan(
        db,
        context,
        llm_spec,
        algorithm_version=f"llm-openai:{settings.openai_model}",
    )
