"""Helpers for combo/complex exercises (e.g. '2 box jump + 5 burpees')."""

import re

_COMBO_LEADING_COUNT = re.compile(r"^\s*(\d+)")


def is_combo_exercise(exercise_name: str | None) -> bool:
    """True when the exercise name describes a multi-movement combo (contains '+')."""
    return bool(exercise_name and "+" in exercise_name)


def parse_combo_segments(exercise_name: str | None) -> list[tuple[int, str]]:
    """
    Split a combo name into per-round movement counts and labels.

    Example: '2 box jump + 5 burpees' -> [(2, 'box jump'), (5, 'burpees')].
    """
    if not is_combo_exercise(exercise_name):
        return []

    segments: list[tuple[int, str]] = []
    for part in exercise_name.split("+"):
        part = part.strip()
        if not part:
            continue
        match = _COMBO_LEADING_COUNT.match(part)
        if match:
            count = int(match.group(1))
            label = part[match.end() :].strip()
        else:
            count = 1
            label = part
        if label:
            segments.append((count, label))
    return segments


def combo_totals_for_rounds(exercise_name: str | None, rounds: int) -> list[tuple[int, str]]:
    """Scale each combo segment by logged rounds (e.g. 3 rounds -> 6 box jumps, 15 burpees)."""
    if rounds <= 0:
        return []
    return [(count * rounds, label) for count, label in parse_combo_segments(exercise_name)]


def _pluralize_movement(total: int, label: str) -> str:
    if total == 1 or label.endswith("s"):
        return label
    return f"{label}s"


def format_combo_totals(exercise_name: str | None, rounds: int) -> str | None:
    """Human-readable total volume for a combo set, e.g. '6 box jumps + 15 burpees'."""
    totals = combo_totals_for_rounds(exercise_name, rounds)
    if not totals:
        return None
    return " + ".join(
        f"{total} {_pluralize_movement(total, label)}" for total, label in totals
    )


def movements_per_combo_round(exercise_name: str | None) -> int | None:
    """
    Parse how many individual movements one logged rep/round includes.

    Example: '2 box jump + 5 burpees' -> 7 (2 jumps + 5 burpees per round).
    """
    segments = parse_combo_segments(exercise_name)
    if not segments:
        return None
    total = sum(count for count, _ in segments)
    return total if total > 0 else None


def rep_unit(exercise_name: str | None) -> str:
    """Label for logged rep count: 'rounds' for combos, 'reps' otherwise."""
    return "rounds" if is_combo_exercise(exercise_name) else "reps"


def format_set_display(
    weight_kg: float | None,
    reps: int | None,
    exercise_name: str | None = None,
    drop_stages: list[tuple[float | None, int | None]] | None = None,
) -> str:
    unit = rep_unit(exercise_name)
    if weight_kg and reps:
        base = f"{weight_kg:g} kg × {reps} {unit}"
    elif weight_kg:
        base = f"{weight_kg:g} kg"
    elif reps:
        base = f"{reps} {unit}"
    else:
        return "—"

    if reps and is_combo_exercise(exercise_name):
        totals = format_combo_totals(exercise_name, reps)
        if totals:
            base = f"{base} ({totals})"

    if drop_stages:
        chain = []
        for stage_weight, stage_reps in drop_stages:
            if stage_weight and stage_reps:
                chain.append(f"{stage_weight:g} kg × {stage_reps}")
            elif stage_weight:
                chain.append(f"{stage_weight:g} kg")
            elif stage_reps:
                chain.append(f"{stage_reps}")
        if chain:
            return " → ".join([base, *chain])
    return base
