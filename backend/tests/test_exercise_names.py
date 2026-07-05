from app.services.exercise_names import (
    cluster_exercise_names,
    exercise_names_equivalent,
    exercise_similarity,
    find_best_exercise_match,
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


def test_exercise_similarity_is_perfect_for_identical_normalized_names():
    assert exercise_similarity("Dead-Lift", "dead lift") == 1.0
