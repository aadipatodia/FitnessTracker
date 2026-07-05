from datetime import date, datetime, timedelta
from types import SimpleNamespace

from app.services.exercise_progress_cache import (
    _apply_sessions_to_row,
    _build_progress_summary,
    _normalize_exercise_key,
    _row_needs_ai_refresh,
    compact_payload_for_ai,
)


def _row(**kwargs):
    defaults = {
        "exercise_name": "Bench Press",
        "exercise_key": "bench press",
        "sessions_count": 0,
        "recent_sessions_json": None,
        "progress_summary_json": None,
        "ai_context_summary": None,
        "current_weight_kg": None,
        "current_reps": None,
        "last_session_date": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_build_progress_summary_tracks_peaks_and_trend():
    sessions = [
        {
            "date": "2026-01-01",
            "best_set": {"weight_kg": 60, "reps": 8},
            "total_volume_kg": 480,
        },
        {
            "date": "2026-01-08",
            "best_set": {"weight_kg": 62.5, "reps": 8},
            "total_volume_kg": 500,
        },
        {
            "date": "2026-01-15",
            "best_set": {"weight_kg": 65, "reps": 6},
            "total_volume_kg": 520,
        },
    ]
    summary = _build_progress_summary(sessions)
    assert summary["total_sessions"] == 3
    assert summary["all_time_peak"]["weight_kg"] == 65
    assert summary["volume_trend"] == "up"


def test_apply_sessions_sets_trend_improving():
    row = _row()
    sessions = [
        {"date": "2026-01-01", "best_set": {"weight_kg": 60, "reps": 8}, "workout_id": 1},
        {"date": "2026-01-08", "best_set": {"weight_kg": 62.5, "reps": 8}, "workout_id": 2},
    ]
    _apply_sessions_to_row(row, "Bench Press", sessions)
    assert row.trend == "improving"
    assert row.current_weight_kg == 62.5
    assert row.previous_weight_kg == 60
    assert row.sessions_count == 2


def test_compact_payload_limits_recent_sessions():
    recent = [
        {"date": f"2026-01-{i:02d}", "best_set": {"weight_kg": 50 + i, "reps": 8}, "sets": []}
        for i in range(1, 9)
    ]
    row = _row(
        recent_sessions_json=recent,
        progress_summary_json={"total_sessions": 8},
        ai_context_summary="Prior: consolidate 60 kg × 8.",
        current_weight_kg=57,
        current_reps=8,
        last_session_date=date(2026, 1, 8),
    )
    payload = compact_payload_for_ai(row)
    assert len(payload["recent_sessions"]) <= 4
    assert payload["previous_coaching_summary"] == "Prior: consolidate 60 kg × 8."
    assert payload["progress_summary"]["total_sessions"] == 8


def test_normalize_exercise_key():
    assert _normalize_exercise_key("  Deadlift ") == "deadlift"
    assert _normalize_exercise_key("Hammer-Curl") == "hammer curl"


def test_unique_exercise_keys_dedupes_case_variants():
    from types import SimpleNamespace
    from app.services.exercise_progress_cache import _unique_exercise_keys

    workout = SimpleNamespace(
        exercises=[
            SimpleNamespace(exercise_name="Bench Press"),
            SimpleNamespace(exercise_name="bench press"),
            SimpleNamespace(exercise_name="Squat"),
        ],
    )
    keys = _unique_exercise_keys([workout])
    assert keys == ["bench press", "squat"]


def test_row_needs_ai_refresh_when_never_refreshed():
    row = _row(ai_refreshed_at=None, history_updated_at=datetime.utcnow())
    assert _row_needs_ai_refresh(row) is True


def test_row_needs_ai_refresh_when_history_newer():
    row = _row(
        ai_refreshed_at=datetime.utcnow() - timedelta(hours=1),
        history_updated_at=datetime.utcnow(),
    )
    assert _row_needs_ai_refresh(row) is True


def test_row_needs_ai_refresh_when_current():
    now = datetime.utcnow()
    row = _row(ai_refreshed_at=now, history_updated_at=now)
    assert _row_needs_ai_refresh(row) is False
