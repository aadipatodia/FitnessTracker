"""Everyday movement (NEAT) estimates and cardio calorie fallbacks."""

DEFAULT_BODY_WEIGHT_KG = 75.0
FALLBACK_CARDIO_MET = 5.0  # used only when Gemini is unavailable

# Light physical movement at home: walking between rooms, kitchen trips, light chores.
EVERYDAY_MOVEMENT_MET = 2.3
EVERYDAY_MOVEMENT_HOURS = 2.0


def estimate_everyday_movement_burn(body_weight_kg: float | None = None) -> float:
    """
    NEAT only: physical movement during daily life (walking at home, light chores).
    Does NOT include resting metabolism (BMR). Uses only body weight (kg).
    """
    weight = body_weight_kg or DEFAULT_BODY_WEIGHT_KG
    return round(EVERYDAY_MOVEMENT_MET * weight * EVERYDAY_MOVEMENT_HOURS, 1)


def everyday_movement_info(body_weight_kg: float | None = None) -> dict:
    weight = body_weight_kg or DEFAULT_BODY_WEIGHT_KG
    kcal = estimate_everyday_movement_burn(weight)
    return {
        "body_weight_kg": weight,
        "met": EVERYDAY_MOVEMENT_MET,
        "equivalent_hours": EVERYDAY_MOVEMENT_HOURS,
        "everyday_movement_kcal": kcal,
        "description": (
            f"~{kcal:.0f} kcal from everyday physical movement for {weight:.0f} kg "
            f"({EVERYDAY_MOVEMENT_MET} MET × {EVERYDAY_MOVEMENT_HOURS}h — walking at home, "
            "kitchen trips, light chores). Resting metabolism is NOT included; "
            "your intake target already covers base body needs."
        ),
    }


def fallback_cardio_calories(
    duration_minutes: int,
    body_weight_kg: float | None = None,
) -> float:
    """Generic fallback when Gemini cannot estimate logged cardio."""
    weight = body_weight_kg or DEFAULT_BODY_WEIGHT_KG
    return round(FALLBACK_CARDIO_MET * weight * (duration_minutes / 60.0), 1)


def cardio_calories_for_log(
    log,
    body_weight_kg: float | None = None,
) -> float:
    """Use persisted Gemini estimate, or generic fallback for older rows."""
    if log.calories_burned is not None:
        return log.calories_burned
    return fallback_cardio_calories(log.duration_minutes, body_weight_kg)
