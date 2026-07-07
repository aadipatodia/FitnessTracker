from app.services.exercise_display import (
    combo_totals_for_rounds,
    format_combo_totals,
    format_set_display,
    is_combo_exercise,
    movements_per_combo_round,
    parse_combo_segments,
    rep_unit,
)
from app.services.workout_calories import _set_active_seconds


def test_is_combo_exercise():
    assert is_combo_exercise("2 box jump + 5 burpees")
    assert not is_combo_exercise("Clean")
    assert not is_combo_exercise(None)


def test_parse_combo_segments():
    assert parse_combo_segments("2 box jump + 5 burpees") == [
        (2, "box jump"),
        (5, "burpees"),
    ]


def test_combo_totals_for_rounds():
    name = "2 box jump + 5 burpees"
    assert combo_totals_for_rounds(name, 3) == [(6, "box jump"), (15, "burpees")]
    assert format_combo_totals(name, 3) == "6 box jumps + 15 burpees"


def test_movements_per_combo_round():
    assert movements_per_combo_round("2 box jump + 5 burpees") == 7
    assert movements_per_combo_round("Clean") is None


def test_rep_unit():
    assert rep_unit("2 box jump + 5 burpees") == "rounds"
    assert rep_unit("Clean") == "reps"


def test_format_set_display():
    assert format_set_display(None, 5, "2 box jump + 5 burpees") == (
        "5 rounds (10 box jumps + 25 burpees)"
    )
    assert format_set_display(None, 3, "2 box jump + 5 burpees") == (
        "3 rounds (6 box jumps + 15 burpees)"
    )
    assert format_set_display(30, 8, "Clean") == "30 kg × 8 reps"


def test_combo_exercise_active_seconds():
    # 5 rounds × 7 movements × 4 sec = 140 sec (not 20 sec for 5 plain reps)
    assert _set_active_seconds(5, None, "2 box jump + 5 burpees") == 140
