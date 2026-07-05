from app.services.exercise_names import (
    cluster_exercise_names,
    exercise_names_equivalent,
    exercise_similarity,
    find_best_exercise_match,
    merge_strength_progression_points,
    normalize_exercise_key,
)


def test_normalize_exercise_key_strips_punctuation_and_case():
    assert normalize_exercise_key("  Hammer-Curl ") == "hammer curl"
    assert normalize_exercise_key("Bench Press!!!") == "bench press"


def test_exercise_names_equivalent_handles_typos():
    assert exercise_names_equivalent("Hammer curl", "Hammer curll")
    assert exercise_names_equivalent("Front Raises", "front raises")
    assert not exercise_names_equivalent("Hammer curl", "Bench Press")


def test_find_best_exercise_match_prefers_closest_spelling():
    candidates = ["Front Raises", "Bench Press", "Hammer curl"]
    assert find_best_exercise_match("Hammer curll", candidates) == "Hammer curl"


def test_cluster_exercise_names_merges_variants():
    names = ["Hammer curl", "Hammer curll", "Front Raises", "front raises"]
    clusters = cluster_exercise_names(names)
    assert clusters["Hammer curll"] == clusters["Hammer curl"]
    assert clusters["front raises"] == clusters["Front Raises"]


def test_merge_strength_progression_points_combines_name_variants():
    points = [
        {"date": "2026-07-02", "exercise": "Bench Press", "max_weight": 30},
        {"date": "2026-07-05", "exercise": "Bench press", "max_weight": 35},
    ]
    merged = merge_strength_progression_points(points, ["Bench Press", "Bench press"])
    assert len(merged) == 2
    assert all(row["exercise"] == merged[0]["exercise"] for row in merged)
    by_date = {row["date"]: row["max_weight"] for row in merged}
    assert by_date["2026-07-02"] == 30
    assert by_date["2026-07-05"] == 35


def test_merge_strength_progression_points_keeps_same_day_heaviest():
    points = [
        {"date": "2026-07-05", "exercise": "Bench Press", "max_weight": 30},
        {"date": "2026-07-05", "exercise": "Bench press", "max_weight": 35},
    ]
    merged = merge_strength_progression_points(points)
    assert len(merged) == 1
    assert merged[0]["max_weight"] == 35
