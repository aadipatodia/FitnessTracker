from datetime import date

from app.models.workout import Workout, WorkoutExercise, ExerciseSet
from app.services.workout_calories import (
    estimate_lift_volume_kg,
    estimate_minimum_workout_calories,
    estimate_workout_calories,
    estimate_workout_duration_minutes,
)


def _workout(exercises: list[list[tuple[float, int, int | None]]]) -> Workout:
    workout = Workout(user_id=1, workout_date=date.today())
    for index, sets in enumerate(exercises):
        exercise = WorkoutExercise(
            workout=workout,
            exercise_name=f"Exercise {index + 1}",
            order_index=index,
        )
        for set_number, (weight, reps, rest) in enumerate(sets, start=1):
            ExerciseSet(
                exercise=exercise,
                set_number=set_number,
                weight_kg=weight,
                reps=reps,
                rest_seconds=rest,
            )
    return workout


def test_estimate_duration_from_sets_when_not_logged():
    workout = _workout([[(60, 8, 90), (60, 8, 90), (60, 8, 90)]])
    duration = estimate_workout_duration_minutes(workout)
    assert duration >= 15


def test_uses_logged_duration_when_present():
    workout = _workout([[(60, 8, 60)]])
    workout.duration_minutes = 55
    assert estimate_workout_duration_minutes(workout) == 55


def test_lift_volume_sums_weight_times_reps():
    workout = _workout([[(100, 5, 60), (80, 10, 60)]])
    assert estimate_lift_volume_kg(workout) == 1300


def test_calories_scale_with_body_weight_and_volume():
    workout = _workout([[(100, 10, 60), (100, 10, 60), (100, 10, 60)]])
    lighter = estimate_workout_calories(workout, body_weight_kg=70)
    heavier = estimate_workout_calories(workout, body_weight_kg=90)
    assert heavier > lighter
    assert estimate_workout_calories(workout, body_weight_kg=80) > 0


def test_minimum_workout_calories_scales_with_body_weight():
    lighter = estimate_minimum_workout_calories(60)
    heavier = estimate_minimum_workout_calories(80)
    assert heavier > lighter
    assert estimate_minimum_workout_calories(75) == 281.2
