from datetime import date
from types import SimpleNamespace

from app.services.analytics import (
    calculate_goal_progress,
    calculate_strength_progress,
    DEADLINE_PACE_BUFFER,
)


def _goal(**kwargs):
    defaults = {
        "goal_type": SimpleNamespace(value="reduce_body_fat"),
        "target_body_fat": 12.0,
        "current_body_fat": 20.0,
        "target_weight": None,
        "current_weight": None,
        "target_exercise": None,
        "target_weight_lifted": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _metric(**kwargs):
    return SimpleNamespace(
        weight_kg=kwargs.get("weight_kg"),
        body_fat_percent=kwargs.get("body_fat_percent"),
    )


def _workout(exercises):
    return SimpleNamespace(exercises=exercises)


def _exercise(name, sets):
    return SimpleNamespace(
        exercise_name=name,
        sets=[SimpleNamespace(weight_kg=s[0], reps=s[1]) for s in sets],
    )


def test_body_fat_progress_at_start():
    goal = _goal()
    assert calculate_goal_progress(goal, _metric(body_fat_percent=20.0)) == 0.0


def test_body_fat_progress_halfway():
    goal = _goal()
    assert calculate_goal_progress(goal, _metric(body_fat_percent=16.0)) == 50.0


def test_body_fat_progress_at_target():
    goal = _goal()
    assert calculate_goal_progress(goal, _metric(body_fat_percent=12.0)) == 100.0


def test_weight_progress():
    goal = _goal(
        goal_type=SimpleNamespace(value="lose_fat_gain_muscle"),
        target_body_fat=None,
        current_body_fat=None,
        target_weight=65.0,
        current_weight=75.0,
    )
    assert calculate_goal_progress(goal, _metric(weight_kg=70.0)) == 50.0


def test_strength_progress_no_workouts():
    goal = _goal(
        goal_type=SimpleNamespace(value="increase_strength"),
        target_exercise="Bench Press",
        target_weight_lifted=100.0,
    )
    assert calculate_strength_progress(goal, []) == 0.0


def test_strength_progress_with_lift():
    goal = _goal(
        goal_type=SimpleNamespace(value="increase_strength"),
        target_exercise="Bench Press",
        target_weight_lifted=100.0,
    )
    workouts = [_workout([_exercise("Bench Press", [(85, 5)])])]
    # start assumed 70kg (70% of 100), current 85 -> (85-70)/(100-70) = 50%
    assert calculate_strength_progress(goal, workouts) == 50.0


def test_deadline_pace_buffer_is_reasonable():
    assert DEADLINE_PACE_BUFFER == 5
