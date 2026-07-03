from datetime import date
from types import SimpleNamespace

import pytest

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


def test_exclude_today_before_7pm():
    from datetime import datetime, timezone, timedelta

    from app.services.analytics import resolve_analysis_dates, ANALYSIS_CUTOFF_HOUR

    ist = timezone(timedelta(hours=5, minutes=30))
    requested = date(2026, 3, 3)
    morning = datetime(2026, 3, 3, 10, 0, tzinfo=ist)
    ctx = resolve_analysis_dates(requested, morning)
    assert ctx["exclude_requested_day"] is True
    assert ctx["stats_through_date"] == "2026-03-02"
    assert "2026-03-02" in ctx["stats_basis_note"]
    assert str(ANALYSIS_CUTOFF_HOUR) in ctx["stats_basis_note"]


def test_include_today_after_7pm():
    from datetime import datetime, timezone, timedelta

    from app.services.analytics import resolve_analysis_dates

    ist = timezone(timedelta(hours=5, minutes=30))
    requested = date(2026, 3, 3)
    evening = datetime(2026, 3, 3, 20, 0, tzinfo=ist)
    ctx = resolve_analysis_dates(requested, evening)
    assert ctx["exclude_requested_day"] is False
    assert ctx["stats_through_date"] == "2026-03-03"


def test_past_date_always_included():
    from datetime import datetime, timezone, timedelta

    from app.services.analytics import resolve_analysis_dates

    ist = timezone(timedelta(hours=5, minutes=30))
    requested = date(2026, 3, 1)
    morning = datetime(2026, 3, 3, 10, 0, tzinfo=ist)
    ctx = resolve_analysis_dates(requested, morning)
    assert ctx["exclude_requested_day"] is False
    assert ctx["stats_through_date"] == "2026-03-01"


def test_journey_progress_scales_with_user_timeline():
    from app.services.analytics import compute_journey_progress_percent, compute_time_progress_percent

    days_elapsed = 3
    total_program_days = 75  # example only — production uses each goal's target_date
    execution_adherence = 90.0
    time_progress = compute_time_progress_percent(days_elapsed, total_program_days)
    overall = compute_journey_progress_percent(
        outcome_percent=0.0,
        execution_adherence=execution_adherence,
        time_progress=time_progress,
        days_elapsed=days_elapsed,
    )
    assert overall == round(time_progress * execution_adherence / 100, 1)
    assert overall < (days_elapsed / total_program_days * 100) + 1


@pytest.mark.parametrize("total_program_days", [30, 75, 120, 365])
def test_time_progress_derived_from_goal_timeline(total_program_days):
    from app.services.analytics import compute_time_progress_percent

    days_elapsed = 3
    expected = min(100.0, days_elapsed / total_program_days * 100)
    assert compute_time_progress_percent(days_elapsed, total_program_days) == expected


def test_journey_progress_body_outcome_can_exceed_execution():
    from app.services.analytics import compute_journey_progress_percent

    overall = compute_journey_progress_percent(
        outcome_percent=25.0,
        execution_adherence=90.0,
        time_progress=4.0,
        days_elapsed=3,
    )
    assert overall == 25.0


def test_journey_progress_without_deadline_uses_outcome_only():
    from app.services.analytics import compute_journey_progress_percent

    overall = compute_journey_progress_percent(
        outcome_percent=0.0,
        execution_adherence=100.0,
        time_progress=None,
        days_elapsed=3,
    )
    assert overall == 0.0

    overall_with_body = compute_journey_progress_percent(
        outcome_percent=12.5,
        execution_adherence=100.0,
        time_progress=None,
        days_elapsed=3,
    )
    assert overall_with_body == 12.5
