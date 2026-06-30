"""Estimate calories burned from logged strength workouts."""

from app.models.workout import Workout

DEFAULT_BODY_WEIGHT_KG = 75.0
STRENGTH_TRAINING_MET = 5.0  # vigorous resistance training (Compendium of Physical Activities)
KCAL_PER_KG_REP = 0.05
SECONDS_PER_REP = 4
DEFAULT_SET_ACTIVE_SECONDS = 45
DEFAULT_REST_SECONDS = 60
SETUP_SECONDS_PER_EXERCISE = 30
MIN_WORKOUT_MINUTES = 15
TARGET_WORKOUT_MINUTES = 45  # baseline session length for minimum burn target


def _set_active_seconds(reps: int | None, time_seconds: int | None) -> int:
    if time_seconds:
        return time_seconds
    if reps:
        return max(30, reps * SECONDS_PER_REP)
    return DEFAULT_SET_ACTIVE_SECONDS


def estimate_workout_duration_minutes(workout: Workout) -> int:
    if workout.duration_minutes:
        return workout.duration_minutes

    total_seconds = 0
    for exercise in workout.exercises:
        for exercise_set in exercise.sets:
            total_seconds += _set_active_seconds(exercise_set.reps, exercise_set.time_seconds)
            total_seconds += exercise_set.rest_seconds or DEFAULT_REST_SECONDS
        total_seconds += SETUP_SECONDS_PER_EXERCISE

    return max(MIN_WORKOUT_MINUTES, round(total_seconds / 60))


def estimate_lift_volume_kg(workout: Workout) -> float:
    return sum(
        (exercise_set.weight_kg or 0) * (exercise_set.reps or 0)
        for exercise in workout.exercises
        for exercise_set in exercise.sets
    )


def estimate_minimum_workout_calories(body_weight_kg: float | None = None) -> float:
    """Minimum active calories to aim for in a strength workout session."""
    weight = body_weight_kg or DEFAULT_BODY_WEIGHT_KG
    return round(STRENGTH_TRAINING_MET * weight * (TARGET_WORKOUT_MINUTES / 60.0), 1)


def estimate_workout_calories(workout: Workout, body_weight_kg: float | None = None) -> float:
    """Estimate kcal burned from a workout using MET + lifting volume."""
    weight = body_weight_kg or DEFAULT_BODY_WEIGHT_KG
    duration_minutes = estimate_workout_duration_minutes(workout)

    met_calories = STRENGTH_TRAINING_MET * weight * (duration_minutes / 60.0)
    volume_calories = estimate_lift_volume_kg(workout) * KCAL_PER_KG_REP

    return round(met_calories + volume_calories, 1)
