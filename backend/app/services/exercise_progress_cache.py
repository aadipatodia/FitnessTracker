"""Persisted exercise summaries — incremental Gemini refresh instead of full history replay."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.exercise_progress import ExerciseProgressSummary
from app.models.workout import Workout, WorkoutExercise, ExerciseSet
from app.schemas import ExerciseAssessment
from app.services.analytics import (
    _best_set_for_exercise,
    _build_fallback_next_session_targets,
    _build_status_summary,
    _determine_trend,
    _exercise_matches_goal,
    _goal_context_note,
    _goal_snapshot,
    _normalize_exercise_key,
    _resolve_next_session_target,
    _rep_range_for_goal,
    build_exercise_assessments,
    build_exercise_history_summaries,
    get_active_goal,
)

RECENT_SESSIONS_STORED = 8
RECENT_SESSIONS_FOR_AI = 4


def _session_from_exercise(workout: Workout, ex: WorkoutExercise) -> dict | None:
    sets: list[dict] = []
    ordered_sets = sorted(ex.sets, key=lambda row: getattr(row, "set_number", 0))
    for idx, s in enumerate(ordered_sets):
        if not s.weight_kg and not s.reps:
            continue
        sets.append({
            "set_number": getattr(s, "set_number", idx + 1),
            "weight_kg": s.weight_kg,
            "reps": s.reps,
        })
    if not sets:
        return None
    best_weight, best_reps = _best_set_for_exercise(ex.sets)
    volume = sum((row.get("weight_kg") or 0) * (row.get("reps") or 0) for row in sets)
    return {
        "date": str(workout.workout_date),
        "workout_id": workout.id,
        "workout_name": workout.name,
        "sets": sets,
        "best_set": {"weight_kg": best_weight, "reps": best_reps},
        "total_volume_kg": round(volume, 1),
        "set_count": len(sets),
    }


def _build_progress_summary(sessions: list[dict]) -> dict:
    if not sessions:
        return {}
    peaks = [
        {
            "date": s["date"],
            "weight_kg": s["best_set"].get("weight_kg"),
            "reps": s["best_set"].get("reps"),
        }
        for s in sessions
    ]
    all_time_peak = max(
        peaks,
        key=lambda p: (p.get("weight_kg") or 0, p.get("reps") or 0),
    )
    recent = peaks[-4:]
    volume_trend = "flat"
    if len(sessions) >= 3:
        v1 = sessions[-3].get("total_volume_kg") or 0
        v2 = sessions[-1].get("total_volume_kg") or 0
        if v2 > v1 * 1.05:
            volume_trend = "up"
        elif v2 < v1 * 0.95:
            volume_trend = "down"

    return {
        "total_sessions": len(sessions),
        "first_session_date": sessions[0]["date"],
        "last_session_date": sessions[-1]["date"],
        "all_time_peak": all_time_peak,
        "recent_session_peaks": recent,
        "volume_trend": volume_trend,
    }


def _load_workouts_for_exercise(db: Session, user_id: int, exercise_key: str) -> list[Workout]:
    return (
        db.query(Workout)
        .options(joinedload(Workout.exercises).joinedload(WorkoutExercise.sets))
        .join(WorkoutExercise, WorkoutExercise.workout_id == Workout.id)
        .filter(
            Workout.user_id == user_id,
            func.lower(WorkoutExercise.exercise_name) == exercise_key,
        )
        .order_by(Workout.workout_date, Workout.id)
        .all()
    )


def _sessions_for_exercise_key(workouts: list[Workout], exercise_key: str) -> list[dict]:
    sessions: list[dict] = []
    for workout in workouts:
        for ex in workout.exercises:
            if _normalize_exercise_key(ex.exercise_name) != exercise_key:
                continue
            session = _session_from_exercise(workout, ex)
            if session:
                sessions.append(session)
    return sessions


def _apply_sessions_to_row(
    row: ExerciseProgressSummary,
    exercise_name: str,
    sessions: list[dict],
    *,
    last_workout_id: int | None = None,
) -> None:
    row.exercise_name = exercise_name
    row.sessions_count = len(sessions)
    row.recent_sessions_json = sessions[-RECENT_SESSIONS_STORED:]
    row.progress_summary_json = _build_progress_summary(sessions)
    row.history_updated_at = datetime.utcnow()

    if not sessions:
        row.last_session_date = None
        row.last_workout_id = None
        row.current_weight_kg = None
        row.current_reps = None
        row.previous_weight_kg = None
        row.previous_reps = None
        row.trend = "new"
        return

    latest = sessions[-1]
    row.last_session_date = date.fromisoformat(latest["date"])
    row.last_workout_id = last_workout_id or latest.get("workout_id")
    row.current_weight_kg = latest["best_set"].get("weight_kg")
    row.current_reps = latest["best_set"].get("reps")

    if len(sessions) >= 2:
        prev = sessions[-2]
        row.previous_weight_kg = prev["best_set"].get("weight_kg")
        row.previous_reps = prev["best_set"].get("reps")
        current = {"weight_kg": row.current_weight_kg, "reps": row.current_reps}
        previous = {"weight_kg": row.previous_weight_kg, "reps": row.previous_reps}
        row.trend = _determine_trend(current, previous)
    else:
        row.previous_weight_kg = None
        row.previous_reps = None
        row.trend = "new"


def _get_or_create_row(db: Session, user_id: int, exercise_key: str) -> ExerciseProgressSummary:
    row = (
        db.query(ExerciseProgressSummary)
        .filter(
            ExerciseProgressSummary.user_id == user_id,
            ExerciseProgressSummary.exercise_key == exercise_key,
        )
        .first()
    )
    if row:
        return row
    row = ExerciseProgressSummary(user_id=user_id, exercise_key=exercise_key, exercise_name=exercise_key)
    db.add(row)
    return row


def resync_exercise_summary(db: Session, user_id: int, exercise_key: str) -> ExerciseProgressSummary | None:
    """Rebuild cached history for one exercise from the database."""
    workouts = _load_workouts_for_exercise(db, user_id, exercise_key)
    sessions = _sessions_for_exercise_key(workouts, exercise_key)
    if not sessions:
        existing = (
            db.query(ExerciseProgressSummary)
            .filter(
                ExerciseProgressSummary.user_id == user_id,
                ExerciseProgressSummary.exercise_key == exercise_key,
            )
            .first()
        )
        if existing:
            db.delete(existing)
        return None

    display_name = next(
        ex.exercise_name
        for w in workouts
        for ex in w.exercises
        if _normalize_exercise_key(ex.exercise_name) == exercise_key
    )
    row = _get_or_create_row(db, user_id, exercise_key)
    _apply_sessions_to_row(row, display_name, sessions)
    return row


def resync_exercises_from_workout(db: Session, user_id: int, workout: Workout) -> list[str]:
    """Refresh summaries for every exercise in a saved workout."""
    keys: list[str] = []
    for ex in workout.exercises:
        key = _normalize_exercise_key(ex.exercise_name)
        if key in keys:
            continue
        keys.append(key)
        resync_exercise_summary(db, user_id, key)
    return keys


def list_stale_exercise_keys(db: Session, user_id: int) -> list[str]:
    rows = (
        db.query(ExerciseProgressSummary)
        .filter(ExerciseProgressSummary.user_id == user_id)
        .all()
    )
    stale: list[str] = []
    for row in rows:
        if row.ai_refreshed_at is None or row.history_updated_at > row.ai_refreshed_at:
            stale.append(row.exercise_key)
    return stale


def compact_payload_for_ai(row: ExerciseProgressSummary) -> dict:
    recent = (row.recent_sessions_json or [])[-RECENT_SESSIONS_FOR_AI:]
    return {
        "exercise": row.exercise_name,
        "progress_summary": row.progress_summary_json,
        "recent_sessions": recent,
        "previous_coaching_summary": row.ai_context_summary,
        "current_best": {
            "weight_kg": row.current_weight_kg,
            "reps": row.current_reps,
            "date": str(row.last_session_date) if row.last_session_date else None,
        },
    }


def apply_ai_targets(
    db: Session,
    user_id: int,
    targets_by_exercise: dict[str, dict],
    history_summaries: dict[str, str] | None = None,
) -> None:
    history_summaries = history_summaries or {}
    for exercise_name, target in targets_by_exercise.items():
        key = _normalize_exercise_key(exercise_name)
        row = (
            db.query(ExerciseProgressSummary)
            .filter(
                ExerciseProgressSummary.user_id == user_id,
                ExerciseProgressSummary.exercise_key == key,
            )
            .first()
        )
        if not row:
            continue
        row.next_weight_kg = target.get("next_weight_kg")
        row.next_reps = target.get("next_reps")
        summary = target.get("next_session_summary") or ""
        row.next_session_summary = summary
        rolling = history_summaries.get(exercise_name) or history_summaries.get(row.exercise_name)
        if rolling:
            row.ai_context_summary = rolling
        elif summary:
            row.ai_context_summary = summary
        row.ai_refreshed_at = datetime.utcnow()


def fallback_targets_for_rows(rows: list[ExerciseProgressSummary], goal) -> dict[str, dict]:
    histories: dict[str, list[dict]] = {}
    for row in rows:
        histories[row.exercise_name] = row.recent_sessions_json or []
    return _build_fallback_next_session_targets(histories, goal)


def assessment_from_row(row: ExerciseProgressSummary, goal) -> ExerciseAssessment:
    rep_min, rep_max = _rep_range_for_goal(goal)
    current = {
        "date": str(row.last_session_date) if row.last_session_date else "",
        "weight_kg": row.current_weight_kg,
        "reps": row.current_reps,
    }
    previous = None
    if row.previous_weight_kg is not None or row.previous_reps is not None:
        previous = {
            "weight_kg": row.previous_weight_kg,
            "reps": row.previous_reps,
        }

    next_by = {
        row.exercise_name: {
            "next_weight_kg": row.next_weight_kg,
            "next_reps": row.next_reps,
            "next_session_summary": row.next_session_summary,
        }
    }
    next_w, next_r, next_summary = _resolve_next_session_target(
        row.exercise_name,
        next_by,
        row.current_weight_kg,
        row.current_reps,
        row.previous_weight_kg,
        row.previous_reps,
        rep_min,
        rep_max,
    )
    is_goal_ex = _exercise_matches_goal(row.exercise_name, goal)
    goal_lift_pct = None
    if is_goal_ex and goal and goal.target_weight_lifted and row.current_weight_kg:
        start = goal.target_weight_lifted * 0.7
        gap = goal.target_weight_lifted - start
        goal_lift_pct = (
            round(max(0, min(100, (row.current_weight_kg - start) / gap * 100)), 1)
            if gap > 0 else 100.0
        )

    return ExerciseAssessment(
        exercise=row.exercise_name,
        current_date=current["date"],
        current_weight_kg=row.current_weight_kg,
        current_reps=row.current_reps,
        previous_weight_kg=row.previous_weight_kg,
        previous_reps=row.previous_reps,
        trend=row.trend,
        sessions_count=row.sessions_count,
        status_summary=_build_status_summary(current, previous, row.trend, row.sessions_count),
        next_weight_kg=next_w,
        next_reps=next_r,
        next_session_summary=next_summary or "Log a working set to unlock your next-session target.",
        goal_note=_goal_context_note(goal, row.exercise_name, row.current_weight_kg),
        is_goal_exercise=is_goal_ex,
        goal_lift_progress_percent=goal_lift_pct,
    )


def assessments_from_cache(
    db: Session,
    user_id: int,
    start_date: date | None,
) -> list[ExerciseAssessment]:
    goal = get_active_goal(db, user_id)
    query = db.query(ExerciseProgressSummary).filter(ExerciseProgressSummary.user_id == user_id)
    if start_date:
        query = query.filter(ExerciseProgressSummary.last_session_date >= start_date)
    rows = query.order_by(ExerciseProgressSummary.last_session_date.desc()).all()
    return [assessment_from_row(row, goal) for row in rows]


async def refresh_ai_targets_for_exercises(
    db: Session,
    user_id: int,
    exercise_keys: list[str],
) -> None:
    """Call Gemini only for stale exercises using compact cached context."""
    if not exercise_keys:
        return

    goal = get_active_goal(db, user_id)
    rows: list[ExerciseProgressSummary] = []
    for key in exercise_keys:
        row = (
            db.query(ExerciseProgressSummary)
            .filter(
                ExerciseProgressSummary.user_id == user_id,
                ExerciseProgressSummary.exercise_key == key,
            )
            .first()
        )
        if row and row.sessions_count > 0:
            rows.append(row)

    if not rows:
        return

    fallbacks = fallback_targets_for_rows(rows, goal)
    compact = {row.exercise_name: compact_payload_for_ai(row) for row in rows}

    from app.services.gemini import generate_exercise_next_session_targets

    result = await generate_exercise_next_session_targets(
        compact,
        _goal_snapshot(goal),
        fallbacks,
        incremental=True,
    )
    apply_ai_targets(db, user_id, result.get("targets", {}), result.get("history_summaries"))
    db.commit()


async def ensure_progress_current(
    db: Session,
    user_id: int,
    exercise_keys: list[str] | None = None,
) -> None:
    """Refresh AI targets only for exercises whose workout data changed since last Gemini call."""
    if exercise_keys is None:
        keys = list_stale_exercise_keys(db, user_id)
    else:
        keys = exercise_keys
    await refresh_ai_targets_for_exercises(db, user_id, keys)


def bootstrap_user_cache(db: Session, user_id: int) -> list[str]:
    """One-time backfill: build summaries for all exercises from existing workouts."""
    workouts = (
        db.query(Workout)
        .options(joinedload(Workout.exercises).joinedload(WorkoutExercise.sets))
        .filter(Workout.user_id == user_id)
        .order_by(Workout.workout_date)
        .all()
    )
    histories = build_exercise_history_summaries(workouts)
    keys: list[str] = []
    for exercise_name in histories:
        key = _normalize_exercise_key(exercise_name)
        keys.append(key)
        resync_exercise_summary(db, user_id, key)
    db.commit()
    return keys


def build_assessments_from_workouts_fallback(
    db: Session,
    user_id: int,
    workouts: list[Workout],
    next_by_exercise: dict[str, dict] | None,
) -> list[ExerciseAssessment]:
    """Legacy path when cache is empty — local rules only, no Gemini."""
    goal = get_active_goal(db, user_id)
    return build_exercise_assessments(workouts, goal, next_by_exercise)
