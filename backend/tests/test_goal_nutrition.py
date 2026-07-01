from app.services.goal_nutrition import apply_stated_nutrition_targets, parse_stated_nutrition_targets

USER_GOAL = (
    "i am at 68.8kg 20% body fat i want to get to 12% by 15 sept 2026 "
    "I want lear muscle definition in abs, back, chest, legs and arms "
    "After deficeit I have to consume 2000-2200 calories every day and 130-140g protein "
    "note this calorie amount is after the deficiet dont cut calories from it"
)


def test_parse_calorie_and_protein_range_from_goal_text():
    parsed = parse_stated_nutrition_targets(USER_GOAL)
    assert parsed["target_calories"] == 2100
    assert parsed["target_protein"] == 135
    assert parsed["calories_post_deficit"] is True


def test_apply_stated_targets_overrides_ai_recommendation():
    result = apply_stated_nutrition_targets(
        {"target_calories": 1650, "target_protein": 120},
        {"end_goal": USER_GOAL},
    )
    assert result["target_calories"] == 2100
    assert result["target_protein"] == 135


def test_single_calorie_value():
    parsed = parse_stated_nutrition_targets("Eat 2200 calories daily")
    assert parsed["target_calories"] == 2200
