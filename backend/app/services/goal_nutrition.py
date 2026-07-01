"""Extract user-stated calorie and protein targets from free-text goals."""

from __future__ import annotations

import re


def parse_stated_nutrition_targets(text: str | None) -> dict[str, int | bool]:
    """Parse explicit daily calorie/protein targets from goal description text."""
    if not text:
        return {}

    lowered = text.lower()
    result: dict[str, int | bool] = {}

    if re.search(
        r"after\s+(?:the\s+)?defic|don'?t\s+cut\s+calor|do\s+not\s+cut\s+calor|already\s+(?:in\s+)?defic",
        lowered,
    ):
        result["calories_post_deficit"] = True

    calorie_range = re.search(
        r"(?:consume|eat|intake|have\s+to\s+consume)?\s*"
        r"(\d{3,4})\s*(?:-|–|to)\s*(\d{3,4})\s*(?:cal(?:ories)?|kcal)\b",
        lowered,
    )
    if not calorie_range:
        calorie_range = re.search(
            r"(\d{3,4})\s*(?:-|–|to)\s*(\d{3,4})\s*(?:cal(?:ories)?|kcal)\b",
            lowered,
        )
    if calorie_range:
        low, high = int(calorie_range.group(1)), int(calorie_range.group(2))
        if 800 <= low <= high <= 6000:
            result["target_calories"] = round((low + high) / 2)

    if "target_calories" not in result:
        single_calorie = re.search(r"\b(\d{3,4})\s*(?:cal(?:ories)?|kcal)\b", lowered)
        if single_calorie:
            value = int(single_calorie.group(1))
            if 800 <= value <= 6000:
                result["target_calories"] = value

    protein_range = re.search(
        r"(\d{2,3})\s*(?:-|–|to)\s*(\d{2,3})\s*g?\s*protein",
        lowered,
    )
    if protein_range:
        low, high = int(protein_range.group(1)), int(protein_range.group(2))
        if 50 <= low <= high <= 400:
            result["target_protein"] = round((low + high) / 2)

    if "target_protein" not in result:
        single_protein = re.search(r"\b(\d{2,3})\s*g\s+protein", lowered)
        if single_protein:
            value = int(single_protein.group(1))
            if 50 <= value <= 400:
                result["target_protein"] = value

    return result


def apply_stated_nutrition_targets(result: dict, goal_data: dict) -> dict:
    """Override AI nutrition targets when the user stated their own."""
    parsed = parse_stated_nutrition_targets(goal_data.get("end_goal"))
    if parsed.get("target_calories"):
        result["target_calories"] = parsed["target_calories"]
    if parsed.get("target_protein"):
        result["target_protein"] = parsed["target_protein"]
    return result
