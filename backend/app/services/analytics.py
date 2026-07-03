from datetime import date, timedelta

from sqlalchemy import func, desc
from sqlalchemy.orm import Session, joinedload

from app.models.goal import FitnessGoal
from app.models.workout import Workout, WorkoutExercise, ExerciseSet
from app.models.diet import DietLog, DietEntry
from app.models.body import BodyMetric
from app.models.recovery import RecoveryLog
from app.models.activity import ActivityLog, ActivityCategory
from app.models.checkpoint import Checkpoint, CheckpointCompletion
from app.schemas import DashboardStats, DashboardCharts, ChartDataPoint, StrengthProgressPoint, GoalResponse, ProgressBreakdown
from app.services.workout_calories import estimate_minimum_workout_calories, estimate_workout_calories
from app.services.activity_calories import (
    estimate_everyday_movement_burn,
    everyday_movement_info,
    cardio_calories_for_log,
)

RECOVERY_SCORE_INFO = {
    "inputs": ["sleep_hours", "water_liters"],
    "formula": "Up to 57% from sleep (8h = full) plus up to 43% from water (3L = full). Maximum 100%.",
    "not_tracked": "Everyday movement burn is auto-estimated from body weight only (NEAT, not resting metabolism).",
}

# Default weights for composite progress (normalized when components are missing)
PROGRESS_WEIGHTS = {
    "body_metrics": 0.25,
    "daily_routine": 0.25,
    "nutrition": 0.20,
    "workouts": 0.20,
    "recovery": 0.10,
}

EXPECTED_WORKOUTS_PER_WEEK = 4
DEADLINE_PACE_BUFFER = 5  # percentage points ahead/behind threshold


def get_active_goal(db: Session, user_id: int) -> FitnessGoal | None:
    return (
        db.query(FitnessGoal)
        .filter(FitnessGoal.user_id == user_id, FitnessGoal.is_active == True)
        .order_by(desc(FitnessGoal.created_at))
        .first()
    )


def calculate_workout_streak(db: Session, user_id: int) -> int:
    workouts = (
        db.query(Workout.workout_date)
        .filter(Workout.user_id == user_id)
        .order_by(desc(Workout.workout_date))
        .all()
    )
    if not workouts:
        return 0

    dates = sorted(set(w.workout_date for w in workouts), reverse=True)
    streak = 0
    expected = date.today()

    for d in dates:
        if d == expected or d == expected - timedelta(days=1):
            streak += 1
            expected = d - timedelta(days=1)
        elif d < expected - timedelta(days=1):
            break

    return streak


def get_nutrition_for_date(db: Session, user_id: int, log_date: date) -> dict:
    entries = (
        db.query(DietEntry)
        .join(DietLog)
        .filter(DietLog.user_id == user_id, DietLog.log_date == log_date)
        .all()
    )
    return {
        "calories": sum(e.calories for e in entries),
        "protein": sum(e.protein_g for e in entries),
        "carbs": sum(e.carbs_g for e in entries),
        "fat": sum(e.fat_g for e in entries),
        "fibre": sum(e.fibre_g for e in entries),
    }


def get_today_nutrition(db: Session, user_id: int) -> dict:
    return get_nutrition_for_date(db, user_id, date.today())


def get_user_body_weight_kg(db: Session, user_id: int) -> float | None:
    goal = get_active_goal(db, user_id)
    latest_metric = (
        db.query(BodyMetric)
        .filter(BodyMetric.user_id == user_id)
        .order_by(desc(BodyMetric.recorded_date))
        .first()
    )
    if latest_metric and latest_metric.weight_kg:
        return latest_metric.weight_kg
    if goal and goal.current_weight:
        return goal.current_weight
    return None


def get_workouts_for_date(db: Session, user_id: int, workout_date: date) -> list[Workout]:
    return (
        db.query(Workout)
        .options(joinedload(Workout.exercises).joinedload(WorkoutExercise.sets))
        .filter(Workout.user_id == user_id, Workout.workout_date == workout_date)
        .all()
    )


def get_activities_for_date(
    db: Session, user_id: int, log_date: date, category: ActivityCategory | None = None,
) -> list[ActivityLog]:
    query = db.query(ActivityLog).filter(
        ActivityLog.user_id == user_id,
        ActivityLog.log_date == log_date,
    )
    if category:
        query = query.filter(ActivityLog.category == category)
    return query.all()


def get_calorie_burn_breakdown(
    db: Session, user_id: int, log_date: date, body_weight: float | None = None,
) -> dict:
    """Active burn: auto everyday movement (NEAT) + logged workouts and cardio. Excludes BMR."""
    weight = body_weight if body_weight is not None else get_user_body_weight_kg(db, user_id)
    everyday = estimate_everyday_movement_burn(weight)

    workouts = get_workouts_for_date(db, user_id, log_date)
    workout_burn = round(
        sum(estimate_workout_calories(w, weight) for w in workouts), 1,
    )

    cardio_logs = get_activities_for_date(db, user_id, log_date, ActivityCategory.CARDIO)
    cardio_burn = round(
        sum(cardio_calories_for_log(a, weight) for a in cardio_logs),
        1,
    )

    exercise_burn = round(workout_burn + cardio_burn, 1)
    total = round(everyday + exercise_burn, 1)
    return {
        "everyday_movement": everyday,
        "workouts": workout_burn,
        "cardio": cardio_burn,
        "exercise_total": exercise_burn,
        "total": total,
        "everyday_movement_info": everyday_movement_info(weight),
    }


def get_calories_burned_for_date(db: Session, user_id: int, workout_date: date) -> float:
    return get_calorie_burn_breakdown(db, user_id, workout_date)["total"]


def get_recovery_log_for_date(db: Session, user_id: int, log_date: date) -> RecoveryLog | None:
    return (
        db.query(RecoveryLog)
        .filter(RecoveryLog.user_id == user_id, RecoveryLog.log_date == log_date)
        .first()
    )


def sleep_hours_for_date(db: Session, user_id: int, analysis_date: date) -> tuple[float | None, date | None]:
    """
    Sleep for the night before analysis_date through the morning of analysis_date.
    Checks the wake-up date first, then the previous calendar day (bed-night date).
    """
    log = get_recovery_log_for_date(db, user_id, analysis_date)
    if log and log.sleep_hours is not None:
        return log.sleep_hours, analysis_date

    prev_date = analysis_date - timedelta(days=1)
    prev_log = get_recovery_log_for_date(db, user_id, prev_date)
    if prev_log and prev_log.sleep_hours is not None:
        return prev_log.sleep_hours, prev_date

    return None, None


def recovery_summary_for_date(db: Session, user_id: int, day: date) -> dict:
    log = get_recovery_log_for_date(db, user_id, day)
    sleep_hours, sleep_logged_on = sleep_hours_for_date(db, user_id, day)
    prev_night = day - timedelta(days=1)
    return {
        "date": str(day),
        "sleep_hours": sleep_hours,
        "sleep_period": f"{prev_night} night to {day} morning",
        "sleep_logged_on": str(sleep_logged_on) if sleep_logged_on else None,
        "water": log.water_liters if log else None,
    }


def calculate_recovery_score_for_date(db: Session, user_id: int, log_date: date) -> float:
    log = get_recovery_log_for_date(db, user_id, log_date)
    sleep_hours, _ = sleep_hours_for_date(db, user_id, log_date)

    score = 0.0
    if sleep_hours:
        score += min(sleep_hours / 8 * 57, 57)
    if log and log.water_liters:
        score += min(log.water_liters / 3 * 43, 43)

    return round(min(score, 100), 1)


def calculate_recovery_score(db: Session, user_id: int) -> float:
    return calculate_recovery_score_for_date(db, user_id, date.today())


def calculate_goal_progress(goal: FitnessGoal | None, latest_metric: BodyMetric | None) -> float:
    """Body-metric progress only (weight, body fat, or strength lift)."""
    if not goal:
        return 0.0

    if goal.goal_type.value == "reduce_body_fat" and goal.target_body_fat and goal.current_body_fat:
        current = latest_metric.body_fat_percent if latest_metric and latest_metric.body_fat_percent else goal.current_body_fat
        total = goal.current_body_fat - goal.target_body_fat
        if total <= 0:
            return 100.0
        progress = (goal.current_body_fat - current) / total * 100
        return round(max(0, min(100, progress)), 1)

    if goal.target_weight and goal.current_weight:
        current = latest_metric.weight_kg if latest_metric and latest_metric.weight_kg else goal.current_weight
        total = abs(goal.current_weight - goal.target_weight)
        if total <= 0:
            return 100.0
        progress = abs(goal.current_weight - current) / total * 100
        return round(max(0, min(100, progress)), 1)

    return 0.0


def calculate_strength_progress(
    goal: FitnessGoal,
    workouts: list[Workout],
) -> float | None:
    if not goal.target_exercise or not goal.target_weight_lifted:
        return None

    peaks = _max_weight_by_exercise(workouts)
    current_peak = None
    for name, weight in peaks.items():
        if goal.target_exercise.lower() in name.lower():
            current_peak = weight
            break

    if current_peak is None:
        return 0.0

    # Assume starting lift is ~70% of target if not tracked separately
    start_lift = goal.target_weight_lifted * 0.7
    total = goal.target_weight_lifted - start_lift
    if total <= 0:
        return 100.0
    progress = (current_peak - start_lift) / total * 100
    return round(max(0, min(100, progress)), 1)


def calculate_routine_adherence(
    db: Session, user_id: int, start_date: date, end_date: date,
) -> float | None:
    checkpoints = db.query(Checkpoint).filter(Checkpoint.user_id == user_id).all()
    if not checkpoints:
        return None

    days = _date_range(start_date, end_date)
    if not days:
        return None

    total_possible = len(checkpoints) * len(days)
    completed = (
        db.query(CheckpointCompletion)
        .filter(
            CheckpointCompletion.user_id == user_id,
            CheckpointCompletion.log_date >= start_date,
            CheckpointCompletion.log_date <= end_date,
            CheckpointCompletion.completed == True,
        )
        .count()
    )
    return round(completed / total_possible * 100, 1)


def calculate_nutrition_adherence(
    db: Session, user_id: int, goal: FitnessGoal, start_date: date, end_date: date,
) -> float | None:
    days = _date_range(start_date, end_date)
    if not days:
        return None

    target_protein = goal.target_protein or int((goal.current_weight or 75) * 1.8)
    logged_days = 0
    on_target_days = 0

    for day in days:
        nutrition = get_nutrition_for_date(db, user_id, day)
        if nutrition["protein"] <= 0 and nutrition["calories"] <= 0:
            continue
        logged_days += 1
        if nutrition["protein"] >= target_protein * 0.9:
            on_target_days += 1
        elif goal.target_calories and nutrition["calories"] > 0:
            calorie_ok = abs(nutrition["calories"] - goal.target_calories) <= goal.target_calories * 0.15
            if calorie_ok:
                on_target_days += 1

    if logged_days == 0:
        return None
    return round(on_target_days / logged_days * 100, 1)


def calculate_workout_adherence(
    db: Session, user_id: int, start_date: date, end_date: date,
) -> float | None:
    days = _date_range(start_date, end_date)
    if not days:
        return None

    workout_dates = {
        row.workout_date
        for row in db.query(Workout.workout_date)
        .filter(
            Workout.user_id == user_id,
            Workout.workout_date >= start_date,
            Workout.workout_date <= end_date,
        )
        .distinct()
        .all()
    }
    if not workout_dates:
        return 0.0

    expected_per_day = EXPECTED_WORKOUTS_PER_WEEK / 7
    expected_total = len(days) * expected_per_day
    actual = len(workout_dates)
    return round(min(100, actual / expected_total * 100), 1)


def calculate_recovery_adherence(
    db: Session, user_id: int, start_date: date, end_date: date,
) -> float | None:
    days = _date_range(start_date, end_date)
    scores = [
        calculate_recovery_score_for_date(db, user_id, day)
        for day in days
    ]
    logged = [s for s in scores if s > 0]
    if not logged:
        return None
    return round(sum(logged) / len(logged), 1)


def calculate_overall_progress(
    db: Session,
    user_id: int,
    goal: FitnessGoal | None,
    latest_metric: BodyMetric | None,
    as_of_date: date | None = None,
) -> dict:
    """
    Composite progress from daily routine, nutrition, workouts, recovery, and body metrics.
    Includes deadline pacing when a target date is set.
    """
    if not goal:
        return {
            "overall_percent": 0.0,
            "body_percent": None,
            "breakdown": None,
            "days_elapsed": None,
            "total_program_days": None,
            "expected_progress_percent": None,
            "deadline_status": "no_deadline",
        }

    today = as_of_date or date.today()
    goal_start = goal.created_at.date()
    days_elapsed = max(1, (today - goal_start).days + 1)

    workouts = (
        db.query(Workout)
        .options(joinedload(Workout.exercises).joinedload(WorkoutExercise.sets))
        .filter(
            Workout.user_id == user_id,
            Workout.workout_date >= goal_start,
            Workout.workout_date <= today,
        )
        .all()
    )

    if goal.goal_type.value == "increase_strength":
        body_percent = calculate_strength_progress(goal, workouts)
    else:
        body_percent = calculate_goal_progress(goal, latest_metric)
        if body_percent == 0.0 and not (goal.target_weight or goal.target_body_fat):
            body_percent = None

    routine_percent = calculate_routine_adherence(db, user_id, goal_start, today)
    nutrition_percent = calculate_nutrition_adherence(db, user_id, goal, goal_start, today)
    workout_percent = calculate_workout_adherence(db, user_id, goal_start, today)
    recovery_percent = calculate_recovery_adherence(db, user_id, goal_start, today)

    components: dict[str, tuple[float, float]] = {}
    if body_percent is not None:
        components["body_metrics"] = (body_percent, PROGRESS_WEIGHTS["body_metrics"])
    if routine_percent is not None:
        components["daily_routine"] = (routine_percent, PROGRESS_WEIGHTS["daily_routine"])
    if nutrition_percent is not None:
        components["nutrition"] = (nutrition_percent, PROGRESS_WEIGHTS["nutrition"])
    if workout_percent is not None:
        components["workouts"] = (workout_percent, PROGRESS_WEIGHTS["workouts"])
    if recovery_percent is not None:
        components["recovery"] = (recovery_percent, PROGRESS_WEIGHTS["recovery"])

    if components:
        total_weight = sum(w for _, w in components.values())
        overall = sum(v * w / total_weight for v, w in components.values())
        overall_percent = round(max(0, min(100, overall)), 1)
    else:
        overall_percent = body_percent if body_percent is not None else 0.0

    breakdown = ProgressBreakdown(
        body_metrics=body_percent if goal.goal_type.value != "increase_strength" else None,
        daily_routine=routine_percent,
        nutrition=nutrition_percent,
        workouts=workout_percent,
        recovery=recovery_percent,
        strength=body_percent if goal.goal_type.value == "increase_strength" else None,
    )

    target_date = goal.target_date.date() if goal.target_date else None
    total_program_days = None
    expected_progress_percent = None
    deadline_status = "no_deadline"

    if target_date and target_date >= goal_start:
        total_program_days = (target_date - goal_start).days + 1
        expected_progress_percent = round(min(100, days_elapsed / total_program_days * 100), 1)
        gap = overall_percent - expected_progress_percent
        if gap >= DEADLINE_PACE_BUFFER:
            deadline_status = "ahead"
        elif gap <= -DEADLINE_PACE_BUFFER:
            deadline_status = "behind"
        else:
            deadline_status = "on_track"

    return {
        "overall_percent": overall_percent,
        "body_percent": body_percent,
        "breakdown": breakdown,
        "days_elapsed": days_elapsed,
        "total_program_days": total_program_days,
        "expected_progress_percent": expected_progress_percent,
        "deadline_status": deadline_status,
    }


def get_dashboard_stats(db: Session, user_id: int) -> DashboardStats:
    goal = get_active_goal(db, user_id)
    latest_metric = (
        db.query(BodyMetric)
        .filter(BodyMetric.user_id == user_id)
        .order_by(desc(BodyMetric.recorded_date))
        .first()
    )
    nutrition = get_today_nutrition(db, user_id)
    burn = get_calorie_burn_breakdown(db, user_id, date.today())
    progress_data = calculate_overall_progress(db, user_id, goal, latest_metric)

    goal_response = None
    if goal:
        goal_response = GoalResponse(
            id=goal.id,
            goal_type=goal.goal_type.value,
            title=goal.title,
            description=goal.description,
            target_body_fat=goal.target_body_fat,
            current_body_fat=goal.current_body_fat,
            target_weight=goal.target_weight,
            current_weight=goal.current_weight,
            target_exercise=goal.target_exercise,
            target_weight_lifted=goal.target_weight_lifted,
            target_calories=goal.target_calories,
            target_protein=goal.target_protein,
            is_active=goal.is_active,
            created_at=goal.created_at,
            target_date=goal.target_date.date() if goal.target_date else None,
        )

    return DashboardStats(
        current_weight=latest_metric.weight_kg if latest_metric else (goal.current_weight if goal else None),
        current_body_fat=latest_metric.body_fat_percent if latest_metric else (goal.current_body_fat if goal else None),
        goal_progress_percent=progress_data["overall_percent"],
        body_progress_percent=progress_data["body_percent"],
        progress_breakdown=progress_data["breakdown"],
        days_elapsed=progress_data["days_elapsed"],
        total_program_days=progress_data["total_program_days"],
        expected_progress_percent=progress_data["expected_progress_percent"],
        deadline_status=progress_data["deadline_status"],
        calories_today=nutrition["calories"],
        calories_burned_today=burn["total"],
        calories_burned_workouts=burn["workouts"],
        calories_burned_cardio=burn["cardio"],
        calories_burned_everyday=burn["everyday_movement"],
        protein_today=nutrition["protein"],
        recovery_score=calculate_recovery_score(db, user_id),
        workout_streak=calculate_workout_streak(db, user_id),
        target_calories=goal.target_calories if goal else None,
        target_protein=goal.target_protein if goal else None,
        active_goal=goal_response,
    )


def get_dashboard_charts(db: Session, user_id: int, days: int = 30) -> DashboardCharts:
    start_date = date.today() - timedelta(days=days) if days > 0 else None

    metrics_q = db.query(BodyMetric).filter(BodyMetric.user_id == user_id)
    if start_date:
        metrics_q = metrics_q.filter(BodyMetric.recorded_date >= start_date)
    metrics = metrics_q.order_by(BodyMetric.recorded_date).all()
    weight_trend = [
        ChartDataPoint(date=m.recorded_date.isoformat(), value=m.weight_kg)
        for m in metrics if m.weight_kg
    ]
    body_fat_trend = [
        ChartDataPoint(date=m.recorded_date.isoformat(), value=m.body_fat_percent)
        for m in metrics if m.body_fat_percent
    ]

    strength_q = (
        db.query(
            Workout.workout_date,
            WorkoutExercise.exercise_name,
            func.max(ExerciseSet.weight_kg).label("max_weight"),
        )
        .join(WorkoutExercise, WorkoutExercise.workout_id == Workout.id)
        .join(ExerciseSet, ExerciseSet.exercise_id == WorkoutExercise.id)
        .filter(Workout.user_id == user_id)
    )
    if start_date:
        strength_q = strength_q.filter(Workout.workout_date >= start_date)
    strength_data = (
        strength_q
        .group_by(Workout.workout_date, WorkoutExercise.exercise_name)
        .order_by(Workout.workout_date)
        .all()
    )
    strength_progression = [
        StrengthProgressPoint(
            date=str(row.workout_date),
            exercise=row.exercise_name,
            max_weight=row.max_weight or 0,
        )
        for row in strength_data
    ]

    # Nutrition trends
    diet_q = db.query(DietLog).filter(DietLog.user_id == user_id)
    if start_date:
        diet_q = diet_q.filter(DietLog.log_date >= start_date)
    diet_logs = diet_q.all()
    protein_by_date: dict[str, float] = {}
    calories_by_date: dict[str, float] = {}

    for log in diet_logs:
        d = log.log_date.isoformat()
        for entry in log.entries:
            protein_by_date[d] = protein_by_date.get(d, 0) + entry.protein_g
            calories_by_date[d] = calories_by_date.get(d, 0) + entry.calories

    protein_intake = [ChartDataPoint(date=d, value=v) for d, v in sorted(protein_by_date.items())]
    calories_intake = [ChartDataPoint(date=d, value=v) for d, v in sorted(calories_by_date.items())]

    return DashboardCharts(
        weight_trend=weight_trend,
        body_fat_trend=body_fat_trend,
        strength_progression=strength_progression,
        protein_intake=protein_intake,
        calories_intake=calories_intake,
    )


def _goal_snapshot(goal: FitnessGoal | None) -> dict:
    if not goal:
        return {"has_goal": False}
    return {
        "has_goal": True,
        "title": goal.title,
        "type": goal.goal_type.value,
        "target_body_fat": goal.target_body_fat,
        "target_weight": goal.target_weight,
        "target_calories": goal.target_calories,
        "target_protein": goal.target_protein,
        "target_exercise": goal.target_exercise,
        "target_weight_lifted": goal.target_weight_lifted,
        "target_date": goal.target_date.date().isoformat() if goal.target_date else None,
        "starting_body_fat": goal.current_body_fat,
        "starting_weight": goal.current_weight,
        "started_on": goal.created_at.date().isoformat(),
    }


def build_calorie_balance(
    consumed: float,
    target: int | None,
    burn_breakdown: dict | None = None,
    body_weight_kg: float | None = None,
) -> dict:
    """Active calorie position: everyday movement + logged exercise vs intake target."""
    exercise = burn_breakdown.get("exercise_total", 0) if burn_breakdown else 0
    everyday = burn_breakdown.get("everyday_movement", 0) if burn_breakdown else 0
    active_total = round(everyday + exercise, 1)
    min_workout_burn = estimate_minimum_workout_calories(body_weight_kg)
    balance: dict = {
        "calories_consumed": round(consumed, 1),
        "calories_burned_active_total": active_total,
        "calories_burned_everyday_movement": everyday,
        "calories_burned_workouts": burn_breakdown.get("workouts", 0) if burn_breakdown else 0,
        "calories_burned_cardio": burn_breakdown.get("cardio", 0) if burn_breakdown else 0,
        "calories_burned_exercise": exercise,
        "target_calories": target,
        "minimum_workout_calorie_burn": min_workout_burn,
    }
    if burn_breakdown and burn_breakdown.get("everyday_movement_info"):
        balance["everyday_movement_info"] = burn_breakdown["everyday_movement_info"]
    if target:
        over_target = round(max(0, consumed - target), 1)
        balance["calories_remaining_to_eat"] = round(max(0, target - consumed), 1)
        balance["calories_over_target"] = over_target
        # Exercise burn offsets intake above target; everyday movement is already counted in NEAT estimate
        surplus_after_exercise = round(max(0, over_target - exercise), 1)
        balance["intake_surplus_after_exercise"] = surplus_after_exercise
        if over_target > 0:
            balance["target_calorie_burn"] = surplus_after_exercise
            balance["target_calorie_burn_mode"] = "surplus_offset"
        else:
            balance["target_calorie_burn"] = min_workout_burn
            balance["target_calorie_burn_mode"] = "workout_minimum"
    else:
        balance["target_calorie_burn"] = min_workout_burn
        balance["target_calorie_burn_mode"] = "workout_minimum"
    return balance


def _workout_to_summary(workout: Workout, body_weight_kg: float | None = None) -> dict:
    exercises = []
    for ex in workout.exercises:
        sets = [{"weight": s.weight_kg, "reps": s.reps} for s in ex.sets]
        exercises.append({"name": ex.exercise_name, "sets": sets})
    return {
        "date": str(workout.workout_date),
        "name": workout.name,
        "calories_burned": estimate_workout_calories(workout, body_weight_kg),
        "exercises": exercises,
    }


def _max_weight_by_exercise(workouts: list[Workout]) -> dict[str, float]:
    peaks: dict[str, float] = {}
    for workout in workouts:
        for ex in workout.exercises:
            for s in ex.sets:
                if s.weight_kg:
                    peaks[ex.exercise_name] = max(peaks.get(ex.exercise_name, 0), s.weight_kg)
    return peaks


def build_weekly_coaching_summary(db: Session, user_id: int, end_date: date) -> dict:
    """Compact 7-day rollup for AI — avoids sending raw workout logs."""
    start_date = end_date - timedelta(days=6)
    goal = get_active_goal(db, user_id)

    daily_rollups = []
    protein_days = 0
    calorie_days = 0
    total_protein = 0.0
    total_calories = 0.0
    total_calories_burned = 0.0
    workout_days = 0
    sleep_logged = 0
    total_sleep = 0.0

    body_weight = get_user_body_weight_kg(db, user_id)

    for day in _date_range(start_date, end_date):
        nutrition = get_nutrition_for_date(db, user_id, day)
        recovery = recovery_summary_for_date(db, user_id, day)
        score = calculate_recovery_score_for_date(db, user_id, day)
        day_workouts = get_workouts_for_date(db, user_id, day)
        day_burn = get_calorie_burn_breakdown(db, user_id, day, body_weight)
        day_burned_total = day_burn["total"]

        if nutrition["protein"] > 0:
            protein_days += 1
            total_protein += nutrition["protein"]
        if nutrition["calories"] > 0:
            calorie_days += 1
            total_calories += nutrition["calories"]
        total_calories_burned += day_burned_total
        if recovery["sleep_hours"]:
            sleep_logged += 1
            total_sleep += recovery["sleep_hours"]
        if day_workouts:
            workout_days += 1

        exercise_peaks = []
        for workout in day_workouts:
            for ex in workout.exercises:
                max_weight = max((s.weight_kg or 0 for s in ex.sets), default=0)
                max_reps = max((s.reps or 0 for s in ex.sets), default=0)
                if max_weight or max_reps:
                    exercise_peaks.append({
                        "exercise": ex.exercise_name,
                        "peak_weight": max_weight,
                        "peak_reps": max_reps,
                    })

        daily_rollups.append({
            "date": str(day),
            "workout": bool(day_workouts),
            "session": day_workouts[0].name if day_workouts else None,
            "calories": round(nutrition["calories"], 1) if nutrition["calories"] else None,
            "calories_burned": day_burned_total if day_burned_total else None,
            "calories_burned_breakdown": day_burn if day_burned_total else None,
            "protein_g": round(nutrition["protein"], 1) if nutrition["protein"] else None,
            "sleep_hours": recovery["sleep_hours"],
            "recovery_score": score,
            "exercise_peaks": exercise_peaks or None,
        })

    week_workouts = (
        db.query(Workout)
        .filter(
            Workout.user_id == user_id,
            Workout.workout_date >= start_date,
            Workout.workout_date <= end_date,
        )
        .order_by(Workout.workout_date)
        .all()
    )
    first_half = [w for w in week_workouts if w.workout_date <= start_date + timedelta(days=2)]
    second_half = [w for w in week_workouts if w.workout_date >= end_date - timedelta(days=2)]
    early_peaks = _max_weight_by_exercise(first_half)
    late_peaks = _max_weight_by_exercise(second_half)
    strength_changes = []
    for exercise in sorted(set(early_peaks) | set(late_peaks)):
        early = early_peaks.get(exercise)
        late = late_peaks.get(exercise)
        if early or late:
            strength_changes.append({
                "exercise": exercise,
                "early_week_max_kg": early,
                "late_week_max_kg": late,
            })

    metrics = (
        db.query(BodyMetric)
        .filter(
            BodyMetric.user_id == user_id,
            BodyMetric.recorded_date >= start_date,
            BodyMetric.recorded_date <= end_date,
        )
        .order_by(BodyMetric.recorded_date)
        .all()
    )
    first_metric = metrics[0] if metrics else None
    last_metric = metrics[-1] if metrics else None

    latest_metric = (
        db.query(BodyMetric)
        .filter(BodyMetric.user_id == user_id, BodyMetric.recorded_date <= end_date)
        .order_by(desc(BodyMetric.recorded_date))
        .first()
    )

    return {
        "period_start": str(start_date),
        "period_end": str(end_date),
        "workout_days": workout_days,
        "workout_streak": calculate_workout_streak(db, user_id),
        "nutrition": {
            "days_logged": calorie_days,
            "avg_calories": round(total_calories / calorie_days, 1) if calorie_days else None,
            "avg_protein_g": round(total_protein / protein_days, 1) if protein_days else None,
            "total_calories_burned": round(total_calories_burned, 1),
            "avg_calories_burned_per_day": round(total_calories_burned / 7, 1),
            "target_calories": goal.target_calories if goal else None,
            "target_protein": goal.target_protein if goal else None,
        },
        "recovery": {
            "days_with_sleep": sleep_logged,
            "avg_sleep_hours": round(total_sleep / sleep_logged, 1) if sleep_logged else None,
        },
        "body_metrics": {
            "start_weight": first_metric.weight_kg if first_metric else None,
            "end_weight": last_metric.weight_kg if last_metric else None,
            "start_body_fat": first_metric.body_fat_percent if first_metric else None,
            "end_body_fat": last_metric.body_fat_percent if last_metric else None,
            "current_weight": latest_metric.weight_kg if latest_metric else None,
            "current_body_fat": latest_metric.body_fat_percent if latest_metric else None,
        },
        "strength_changes": strength_changes,
        "daily_rollups": daily_rollups,
        "recovery_score_info": RECOVERY_SCORE_INFO,
    }


def build_goal_progress_summary(db: Session, user_id: int, as_of_date: date) -> dict:
    """Cumulative progress since goal was set — compact for AI goal coaching."""
    goal = get_active_goal(db, user_id)
    if not goal:
        return {"has_goal": False}

    goal_start = goal.created_at.date()
    latest_metric = (
        db.query(BodyMetric)
        .filter(BodyMetric.user_id == user_id, BodyMetric.recorded_date <= as_of_date)
        .order_by(desc(BodyMetric.recorded_date))
        .first()
    )
    first_metric = (
        db.query(BodyMetric)
        .filter(
            BodyMetric.user_id == user_id,
            BodyMetric.recorded_date >= goal_start,
            BodyMetric.recorded_date <= as_of_date,
        )
        .order_by(BodyMetric.recorded_date)
        .first()
    )

    workouts = (
        db.query(Workout)
        .filter(
            Workout.user_id == user_id,
            Workout.workout_date >= goal_start,
            Workout.workout_date <= as_of_date,
        )
        .all()
    )
    weeks_elapsed = max(1, ((as_of_date - goal_start).days + 1) / 7)

    body_weight = get_user_body_weight_kg(db, user_id)
    protein_days = 0
    total_protein = 0.0
    protein_on_target = 0
    total_calories_consumed = 0.0
    calorie_days = 0
    total_calories_burned = 0.0
    for day in _date_range(goal_start, as_of_date):
        nutrition = get_nutrition_for_date(db, user_id, day)
        day_burn = get_calorie_burn_breakdown(db, user_id, day, body_weight)
        total_calories_burned += day_burn["total"]
        if nutrition["protein"] > 0:
            protein_days += 1
            total_protein += nutrition["protein"]
            target = goal.target_protein or int((goal.current_weight or 75) * 1.8)
            if nutrition["protein"] >= target * 0.9:
                protein_on_target += 1
        if nutrition["calories"] > 0:
            calorie_days += 1
            total_calories_consumed += nutrition["calories"]

    target_lift_peak = None
    if goal.target_exercise:
        peaks = _max_weight_by_exercise(workouts)
        for name, weight in peaks.items():
            if goal.target_exercise.lower() in name.lower():
                target_lift_peak = weight
                break

    target_date = goal.target_date.date() if goal.target_date else None
    days_until = (target_date - as_of_date).days if target_date else None
    current_weight = (
        latest_metric.weight_kg if latest_metric and latest_metric.weight_kg
        else goal.current_weight
    )
    current_body_fat = (
        latest_metric.body_fat_percent if latest_metric and latest_metric.body_fat_percent
        else goal.current_body_fat
    )

    progress_data = calculate_overall_progress(db, user_id, goal, latest_metric, as_of_date)

    return {
        "has_goal": True,
        "goal": _goal_snapshot(goal),
        "as_of_date": str(as_of_date),
        "days_since_start": (as_of_date - goal_start).days + 1,
        "days_until_deadline": days_until,
        "weeks_until_deadline": max(0, (days_until + 6) // 7) if days_until is not None else None,
        "progress_percent": progress_data["overall_percent"],
        "progress_breakdown": progress_data,
        "body_metrics": {
            "starting_weight": goal.current_weight,
            "current_weight": current_weight,
            "weight_change_kg": round(current_weight - goal.current_weight, 1)
            if current_weight and goal.current_weight else None,
            "starting_body_fat": goal.current_body_fat,
            "current_body_fat": current_body_fat,
            "body_fat_change": round(goal.current_body_fat - current_body_fat, 1)
            if current_body_fat and goal.current_body_fat else None,
            "first_logged_on": str(first_metric.recorded_date) if first_metric else None,
        },
        "training": {
            "total_workouts": len(workouts),
            "workouts_per_week": round(len(workouts) / weeks_elapsed, 1),
            "workout_streak": calculate_workout_streak(db, user_id),
            "target_lift_peak_kg": target_lift_peak,
            "target_lift_goal_kg": goal.target_weight_lifted,
        },
        "nutrition": {
            "days_logged": protein_days,
            "avg_protein_g": round(total_protein / protein_days, 1) if protein_days else None,
            "days_protein_on_target": protein_on_target,
            "target_protein": goal.target_protein,
            "target_calories": goal.target_calories,
            "calorie_days_logged": calorie_days,
            "avg_calories_consumed": round(total_calories_consumed / calorie_days, 1)
            if calorie_days else None,
            "total_calories_burned": round(total_calories_burned, 1),
            "avg_calories_burned_per_day": round(total_calories_burned / max(1, (as_of_date - goal_start).days + 1), 1),
        },
    }


def gather_coaching_data(
    db: Session,
    user_id: int,
    days: int = 7,
    target_date: date | None = None,
    analysis_type: str = "daily",
) -> dict:
    """Aggregate user data for AI coaching analysis."""
    end_date = target_date or date.today()
    goal = get_active_goal(db, user_id)
    metric = (
        db.query(BodyMetric)
        .filter(BodyMetric.user_id == user_id, BodyMetric.recorded_date <= end_date)
        .order_by(desc(BodyMetric.recorded_date))
        .first()
    )

    if analysis_type == "goal":
        return {
            "analysis_type": "goal",
            "analysis_date": str(end_date),
            "goal_progress": build_goal_progress_summary(db, user_id, end_date),
            "active_goal": _goal_snapshot(goal),
            "current_weight": metric.weight_kg if metric else (goal.current_weight if goal else None),
            "current_body_fat": metric.body_fat_percent if metric else (goal.current_body_fat if goal else None),
            "recovery_score_info": RECOVERY_SCORE_INFO,
        }

    if analysis_type == "weekly":
        return {
            "analysis_type": "weekly",
            "analysis_date": str(end_date),
            "period_start": str(end_date - timedelta(days=6)),
            "period_end": str(end_date),
            "active_goal": _goal_snapshot(goal),
            "weekly_summary": build_weekly_coaching_summary(db, user_id, end_date),
            "goal_progress": build_goal_progress_summary(db, user_id, end_date),
            "recovery_score_info": RECOVERY_SCORE_INFO,
        }

    # Daily — single day only
    body_weight = get_user_body_weight_kg(db, user_id)
    day_workouts = get_workouts_for_date(db, user_id, end_date)
    nutrition = get_nutrition_for_date(db, user_id, end_date)
    burn = get_calorie_burn_breakdown(db, user_id, end_date, body_weight)
    target_calories = goal.target_calories if goal else None
    day_activities = get_activities_for_date(db, user_id, end_date, ActivityCategory.CARDIO)
    return {
        "analysis_type": "daily",
        "analysis_date": str(end_date),
        "period_start": str(end_date),
        "period_end": str(end_date),
        "active_goal": _goal_snapshot(goal),
        "current_weight": metric.weight_kg if metric else (goal.current_weight if goal else None),
        "current_body_fat": metric.body_fat_percent if metric else (goal.current_body_fat if goal else None),
        "workout_streak": calculate_workout_streak(db, user_id),
        "nutrition_for_date": nutrition,
        "calories_burned_for_date": burn["total"],
        "calories_burned_breakdown": burn,
        "calorie_balance": build_calorie_balance(
            nutrition["calories"], target_calories, burn, body_weight,
        ),
        "activities": [
            {
                "name": a.activity_name,
                "duration_minutes": a.duration_minutes,
                "calories_burned": cardio_calories_for_log(a, body_weight),
            }
            for a in day_activities
        ],
        "recovery_score": calculate_recovery_score_for_date(db, user_id, end_date),
        "recovery_for_analysis_date": recovery_summary_for_date(db, user_id, end_date),
        "recovery_score_info": RECOVERY_SCORE_INFO,
        "workouts": [_workout_to_summary(w, body_weight) for w in day_workouts],
    }


def _date_range(start: date, end: date) -> list[date]:
    days: list[date] = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days
