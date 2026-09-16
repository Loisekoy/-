from collections import Counter
from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.orm import Session, joinedload

from backend.models import (
    BodyPart,
    Exercise,
    PlanDay,
    PlanExercise,
    TrainingGoal,
    User,
    UserBodyPart,
    WorkoutPlan,
)

ALGORITHM_VERSION = "rules-v1"

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

DURATION_CAPACITY = {30: 4, 60: 6, 90: 8}
ACCESSORY_CODES = {"biceps", "triceps"}
EXPERIENCE_RANK = {"beginner": 0, "intermediate": 1, "advanced": 2}


class RecommendationError(ValueError):
    pass


@dataclass(frozen=True)
class ExerciseCandidate:
    exercise_id: int
    body_part_code: str
    difficulty_level: str
    movement_type: str


def build_focus_schedule(
    days_per_week: int, duration_minutes: int, preferred_codes: list[str]
) -> list[list[str]]:
    """Return deterministic body-part slots for each Plan Day."""
    if days_per_week not in BASE_SPLITS:
        raise RecommendationError("Training days must be between 2 and 6")
    if duration_minutes not in DURATION_CAPACITY:
        raise RecommendationError("Training duration must be 30, 60, or 90 minutes")
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


def generate_plan(db: Session, user_id: object) -> WorkoutPlan:
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
    preferred_codes = [part.body_part_code for part in preferred_parts]
    if not preferred_codes:
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

    schedule = build_focus_schedule(
        user.training_days_per_week,
        user.training_duration_minutes,
        preferred_codes,
    )

    db.execute(
        update(WorkoutPlan)
        .where(WorkoutPlan.user_id == user.user_id, WorkoutPlan.status == "active")
        .values(status="archived")
    )

    plan = WorkoutPlan(
        user_id=user.user_id,
        training_goal_id=user.training_goal_id,
        plan_name=f"{user.training_days_per_week} 天{goal.goal_name}訓練計畫",
        training_days_per_week=user.training_days_per_week,
        training_duration_minutes=user.training_duration_minutes,
        algorithm_version=ALGORITHM_VERSION,
        status="generated",
    )
    db.add(plan)
    db.flush()

    body_part_names = {
        part.body_part_code: part.name_zh
        for part in db.scalars(select(BodyPart).where(BodyPart.is_active.is_(True))).all()
    }
    preferred_set = set(preferred_codes)
    weekly_usage: Counter[int] = Counter()
    previous_day_ids: set[int] = set()

    for day_number, body_part_slots in enumerate(schedule, start=1):
        unique_focus = list(dict.fromkeys(body_part_slots))
        focus_summary = "＋".join(body_part_names.get(code, code.title()) for code in unique_focus)
        plan_day = PlanDay(
            plan=plan,
            day_number=day_number,
            day_name=f"Day {day_number} - {focus_summary}",
            focus_summary=focus_summary,
        )
        db.add(plan_day)
        db.flush()

        selected_ids: set[int] = set()
        current_day_ids: set[int] = set()
        for order, code in enumerate(body_part_slots, start=1):
            ranked = _rank_exercises(
                exercises,
                body_part_code=code,
                experience=user.training_experience,
                preferred_codes=preferred_set,
                early_slot=order <= 2,
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
            db.add(
                PlanExercise(
                    plan_day=plan_day,
                    exercise_id=exercise.exercise_id,
                    exercise_order=len(selected_ids) + 1,
                    target_sets=sets,
                    target_reps=reps,
                    rest_seconds=rest,
                )
            )
            selected_ids.add(exercise.exercise_id)
            current_day_ids.add(exercise.exercise_id)
            weekly_usage[exercise.exercise_id] += 1

        if not selected_ids:
            raise RecommendationError(f"No eligible exercises for Day {day_number}")
        previous_day_ids = current_day_ids

    plan.status = "active"
    db.flush()
    return plan
