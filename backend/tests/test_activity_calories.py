"""Tests for activity calorie estimation."""

from app.services.activity_calories import (
    estimate_everyday_movement_burn,
    everyday_movement_info,
    fallback_cardio_calories,
)


def test_everyday_movement_scales_with_weight():
    lighter = estimate_everyday_movement_burn(60)
    heavier = estimate_everyday_movement_burn(80)
    assert heavier > lighter


def test_everyday_movement_is_neat_not_bmr():
    neat = estimate_everyday_movement_burn(70)
    assert 250 < neat < 450


def test_everyday_movement_uses_weight_only():
    info = everyday_movement_info(68)
    assert info["body_weight_kg"] == 68
    assert "Resting metabolism is NOT included" in info["description"]


def test_fallback_cardio_scales_with_duration():
    short = fallback_cardio_calories(20, body_weight_kg=70)
    long = fallback_cardio_calories(40, body_weight_kg=70)
    assert abs(long - short * 2) < 0.2
