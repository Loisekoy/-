from types import SimpleNamespace

import pytest

from backend.services.recommendation import (
    ExerciseCandidate,
    RecommendationError,
    build_focus_schedule,
    prescription_for,
    score_exercise,
)


def test_focus_schedule_covers_major_regions_and_repeats_preferences() -> None:
    schedule = build_focus_schedule(4, 60, ["chest", "back"])

    assert len(schedule) == 4
    assert all(len(day) == 6 for day in schedule)
    flattened = {body_part for day in schedule for body_part in day}
    assert {"chest", "back", "shoulders", "legs", "glutes", "core"} <= flattened
    assert sum("chest" in day for day in schedule) >= 2
    assert sum("back" in day for day in schedule) >= 2


def test_focus_schedule_validates_inputs() -> None:
    with pytest.raises(RecommendationError):
        build_focus_schedule(1, 60, ["chest"])
    assert all(len(day) == 5 for day in build_focus_schedule(4, 45, ["chest"]))
    with pytest.raises(RecommendationError):
        build_focus_schedule(4, 60, [])


def test_exercise_score_rewards_preference_and_exact_difficulty() -> None:
    candidate = ExerciseCandidate(1, "chest", "beginner", "compound")
    score = score_exercise(
        candidate,
        experience="beginner",
        preferred_codes={"chest"},
        early_slot=True,
        previous_day_exercise_ids=set(),
        weekly_usage=0,
    )
    assert score == 60


def test_strength_isolation_and_beginner_cap() -> None:
    goal = SimpleNamespace(
        goal_code="strength", default_sets=5, default_reps=5, default_rest_seconds=150
    )
    assert prescription_for(goal, experience="advanced", movement_type="isolation") == (
        3,
        8,
        75,
    )
    assert prescription_for(goal, experience="beginner", movement_type="compound") == (
        3,
        5,
        150,
    )
