from datetime import date
from types import SimpleNamespace

import pytest

from app.services.analytics import (
    build_exercise_progress_comparisons,
    build_exercise_assessments,
    build_exercise_history_summaries,
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


def _workout(exercises, workout_date=None):
    return SimpleNamespace(
        exercises=exercises,
        workout_date=workout_date or date(2026, 3, 1),
    )


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


def test_body_fat_progress_for_recomposition_goal():
    goal = _goal(
        goal_type=SimpleNamespace(value="lose_fat_gain_muscle"),
        target_body_fat=12.0,
        current_body_fat=20.0,
    )
    assert calculate_goal_progress(goal, _metric(body_fat_percent=16.0)) == 50.0


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


def test_exercise_progress_comparisons():
    workouts = [
        _workout([_exercise("Deadlift", [(80, 3)])], date(2026, 3, 1)),
        _workout([_exercise("Deadlift", [(80, 4)])], date(2026, 3, 8)),
    ]
    comparisons = build_exercise_progress_comparisons(workouts)
    assert len(comparisons) == 1
    deadlift = comparisons[0]
    assert deadlift["exercise"] == "Deadlift"
    assert deadlift["previous_session"] == {"date": "2026-03-01", "weight_kg": 80, "reps": 3}
    assert deadlift["latest_session"] == {"date": "2026-03-08", "weight_kg": 80, "reps": 4}
    assert deadlift["sessions_count"] == 2
    assert "first_session" not in deadlift


def test_exercise_progress_includes_first_session_when_more_than_two():
    workouts = [
        _workout([_exercise("Squat", [(60, 5)])], date(2026, 2, 1)),
        _workout([_exercise("Squat", [(70, 5)])], date(2026, 2, 15)),
        _workout([_exercise("Squat", [(80, 5)])], date(2026, 3, 1)),
    ]
    comparisons = build_exercise_progress_comparisons(workouts)
    squat = comparisons[0]
    assert squat["first_session"] == {"date": "2026-02-01", "weight_kg": 60, "reps": 5}
    assert squat["previous_session"]["weight_kg"] == 70
    assert squat["latest_session"]["weight_kg"] == 80


def test_exercise_progress_skips_single_session_exercises():
    workouts = [
        _workout([_exercise("Bench Press", [(40, 10)])], date(2026, 3, 1)),
    ]
    assert build_exercise_progress_comparisons(workouts) == []


def test_exercise_assessments_includes_single_session():
    workouts = [
        _workout([_exercise("Bench Press", [(40, 10)])], date(2026, 3, 1)),
    ]
    assessments = build_exercise_assessments(workouts, None)
    assert len(assessments) == 1
    bench = assessments[0]
    assert bench.exercise == "Bench Press"
    assert bench.trend == "new"
    assert bench.current_weight_kg == 40
    assert bench.current_reps == 10
    assert bench.next_reps == 11


def test_exercise_assessments_rep_progression_target():
    goal = _goal(goal_type=SimpleNamespace(value="increase_strength"))
    workouts = [
        _workout([_exercise("Deadlift", [(80, 3)])], date(2026, 3, 1)),
        _workout([_exercise("Deadlift", [(80, 4)])], date(2026, 3, 8)),
    ]
    assessments = build_exercise_assessments(workouts, goal)
    deadlift = assessments[0]
    assert deadlift.trend == "improving"
    assert deadlift.next_weight_kg == 80
    assert deadlift.next_reps == 5


def test_exercise_assessments_weight_jump_at_rep_ceiling():
    workouts = [
        _workout([_exercise("Squat", [(60, 11)])], date(2026, 3, 1)),
        _workout([_exercise("Squat", [(60, 12)])], date(2026, 3, 8)),
    ]
    assessments = build_exercise_assessments(workouts, None)
    squat = assessments[0]
    assert squat.next_weight_kg == 62.5
    assert squat.next_reps == 8


def test_exercise_assessments_goal_exercise_note():
    goal = _goal(
        goal_type=SimpleNamespace(value="increase_strength"),
        target_exercise="Bench Press",
        target_weight_lifted=100.0,
    )
    workouts = [_workout([_exercise("Bench Press", [(85, 5)])])]
    assessments = build_exercise_assessments(workouts, goal)
    bench = assessments[0]
    assert bench.is_goal_exercise is True
    assert bench.goal_lift_progress_percent == 50.0
    assert bench.goal_note is not None
    assert "100 kg" in bench.goal_note


def test_exercise_history_includes_all_sets():
    workouts = [
        _workout([_exercise("Chest Press", [(40, 12), (40, 10), (40, 8)])], date(2026, 3, 1)),
        _workout([_exercise("Chest Press", [(42.5, 10), (42.5, 8)])], date(2026, 3, 8)),
    ]
    histories = build_exercise_history_summaries(workouts)
    chest = histories["Chest Press"]
    assert len(chest) == 2
    assert len(chest[0]["sets"]) == 3
    assert chest[0]["best_set"] == {"weight_kg": 40, "reps": 12}
    assert chest[1]["set_count"] == 2


def test_exercise_assessments_use_gemini_next_session():
    workouts = [
        _workout([_exercise("Chest Press", [(40, 12), (40, 10)])], date(2026, 3, 1)),
    ]
    gemini_targets = {
        "Chest Press": {
            "next_weight_kg": 42.5,
            "next_reps": 10,
            "next_session_summary": (
                "Next session: 42.5 kg × 10 reps — your last three sets at 40 kg showed "
                "rep drop-off; a small load increase with a solid 10-rep top set fits your trend."
            ),
        }
    }
    assessments = build_exercise_assessments(workouts, None, gemini_targets)
    chest = assessments[0]
    assert chest.next_weight_kg == 42.5
    assert chest.next_reps == 10
    assert "rep drop-off" in chest.next_session_summary


def test_deadline_pace_buffer_is_reasonable():
    assert DEADLINE_PACE_BUFFER == 5


def test_exclude_today_before_7pm():
    from datetime import datetime, timezone, timedelta

    from app.services.analytics import resolve_analysis_dates, ANALYSIS_CUTOFF_HOUR

    ist = timezone(timedelta(hours=5, minutes=30))
    requested = date(2026, 3, 3)
    morning = datetime(2026, 3, 3, 10, 0, tzinfo=ist)
    ctx = resolve_analysis_dates(requested, morning, analysis_type="weekly")
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
    ctx = resolve_analysis_dates(requested, evening, analysis_type="weekly")
    assert ctx["exclude_requested_day"] is False
    assert ctx["stats_through_date"] == "2026-03-03"


def test_past_date_always_included():
    from datetime import datetime, timezone, timedelta

    from app.services.analytics import resolve_analysis_dates

    ist = timezone(timedelta(hours=5, minutes=30))
    requested = date(2026, 3, 1)
    morning = datetime(2026, 3, 3, 10, 0, tzinfo=ist)
    ctx = resolve_analysis_dates(requested, morning, analysis_type="weekly")
    assert ctx["exclude_requested_day"] is False
    assert ctx["stats_through_date"] == "2026-03-01"


def test_daily_includes_today_before_7pm():
    from datetime import datetime, timezone, timedelta

    from app.services.analytics import resolve_analysis_dates

    ist = timezone(timedelta(hours=5, minutes=30))
    requested = date(2026, 3, 3)
    morning = datetime(2026, 3, 3, 10, 0, tzinfo=ist)
    ctx = resolve_analysis_dates(requested, morning, analysis_type="daily")
    assert ctx["exclude_requested_day"] is False
    assert ctx["is_partial_day"] is True
    assert ctx["stats_through_date"] == "2026-03-03"
    assert "partial day" in ctx["stats_basis_note"]


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


def test_composite_progress_without_body_fat_tracking():
    from app.services.analytics import compute_composite_progress_percent

    overall = compute_composite_progress_percent(
        body_percent=None,
        routine_percent=91.7,
        nutrition_percent=100.0,
        workout_percent=100.0,
        recovery_percent=89.3,
    )
    # Weighted average of execution areas only (no body_metrics weight)
    assert overall == round((91.7 * 0.25 + 100 * 0.20 + 100 * 0.20 + 89.3 * 0.10) / 0.75, 1)


def test_goal_tracks_body_fat():
    from app.services.analytics import goal_tracks_body_fat

    assert goal_tracks_body_fat(_goal(current_body_fat=20.0, target_body_fat=12.0)) is True
    assert goal_tracks_body_fat(_goal(current_body_fat=20.0, target_body_fat=None)) is False
    assert goal_tracks_body_fat(_goal(current_body_fat=None, target_body_fat=12.0)) is False
