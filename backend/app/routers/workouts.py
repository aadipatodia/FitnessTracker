from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.activity_log import log_action
from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.workout import Workout, WorkoutExercise, ExerciseSet, DropSetStage
from app.schemas import WorkoutCreate, WorkoutResponse, ExerciseResponse, SetResponse, DropStageResponse
from app.services.analytics import get_user_body_weight_kg
from app.services.exercise_progress_cache import (
    canonicalize_exercise_names_for_user,
    ensure_progress_current,
    resync_exercise_names,
    resync_exercises_from_workout,
)
from app.services.workout_calories import estimate_workout_calories

router = APIRouter(prefix="/workouts", tags=["workouts"])


@router.post("", response_model=WorkoutResponse)
async def create_workout(
    data: WorkoutCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workout = Workout(
        user_id=current_user.id,
        workout_date=data.workout_date,
        name=data.name,
        notes=data.notes,
        duration_minutes=data.duration_minutes,
    )
    db.add(workout)
    db.flush()

    incoming_names = [ex.exercise_name.strip() for ex in data.exercises if ex.exercise_name.strip()]
    canonical_names = canonicalize_exercise_names_for_user(
        db,
        current_user.id,
        incoming_names,
        refresh_semantic=True,
    )

    for ex_data in data.exercises:
        raw_name = ex_data.exercise_name.strip()
        exercise = WorkoutExercise(
            workout_id=workout.id,
            exercise_name=canonical_names.get(raw_name, ex_data.exercise_name),
            order_index=ex_data.order_index,
            notes=ex_data.notes,
        )
        db.add(exercise)
        db.flush()

        for set_data in ex_data.sets:
            exercise_set = ExerciseSet(
                exercise_id=exercise.id,
                set_number=set_data.set_number,
                weight_kg=set_data.weight_kg,
                reps=set_data.reps,
                time_seconds=set_data.time_seconds,
                rest_seconds=set_data.rest_seconds,
            )
            db.add(exercise_set)
            db.flush()

            for stage_data in set_data.drop_stages:
                db.add(DropSetStage(
                    set_id=exercise_set.id,
                    stage_number=stage_data.stage_number,
                    weight_kg=stage_data.weight_kg,
                    reps=stage_data.reps,
                ))

    db.commit()
    workout = (
        db.query(Workout)
        .options(
            joinedload(Workout.exercises)
            .joinedload(WorkoutExercise.sets)
            .joinedload(ExerciseSet.drop_stages)
        )
        .filter(Workout.id == workout.id, Workout.user_id == current_user.id)
        .first()
    )
    exercise_keys = resync_exercises_from_workout(db, current_user.id, workout)
    db.commit()
    await ensure_progress_current(db, current_user.id, exercise_keys)

    body_weight = get_user_body_weight_kg(db, current_user.id)
    response = _to_response(workout, body_weight)
    exercise_names = ", ".join(e.exercise_name for e in workout.exercises[:3])
    extra = f" (+{len(workout.exercises) - 3} more)" if len(workout.exercises) > 3 else ""
    log_action(
        current_user,
        f"logged workout \"{data.name}\" for {data.workout_date}",
        f"{len(workout.exercises)} exercises ({exercise_names}{extra}), "
        f"{response.calories_burned:.0f} kcal burned",
    )
    return response


@router.get("", response_model=list[WorkoutResponse])
def list_workouts(
    workout_date: date | None = Query(None),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        db.query(Workout)
        .options(
            joinedload(Workout.exercises)
            .joinedload(WorkoutExercise.sets)
            .joinedload(ExerciseSet.drop_stages)
        )
        .filter(Workout.user_id == current_user.id)
    )
    if workout_date:
        query = query.filter(Workout.workout_date == workout_date)
    workouts = query.order_by(Workout.workout_date.desc()).limit(limit).all()
    body_weight = get_user_body_weight_kg(db, current_user.id)
    response = [_to_response(w, body_weight) for w in workouts]
    log_action(
        current_user,
        f"viewed workout history ({workout_date or f'last {limit}'})",
        f"{len(response)} workouts returned",
    )
    return response


@router.get("/{workout_id}", response_model=WorkoutResponse)
def get_workout(
    workout_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workout = (
        db.query(Workout)
        .options(
            joinedload(Workout.exercises)
            .joinedload(WorkoutExercise.sets)
            .joinedload(ExerciseSet.drop_stages)
        )
        .filter(Workout.id == workout_id, Workout.user_id == current_user.id)
        .first()
    )
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    body_weight = get_user_body_weight_kg(db, current_user.id)
    return _to_response(workout, body_weight)


@router.delete("/{workout_id}", status_code=204)
async def delete_workout(
    workout_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workout = (
        db.query(Workout)
        .options(joinedload(Workout.exercises))
        .filter(Workout.id == workout_id, Workout.user_id == current_user.id)
        .first()
    )
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    exercise_names = [ex.exercise_name for ex in workout.exercises if ex.exercise_name]
    db.delete(workout)
    db.commit()

    exercise_keys = resync_exercise_names(db, current_user.id, exercise_names)
    db.commit()
    await ensure_progress_current(db, current_user.id, exercise_keys)


def _to_response(workout: Workout, body_weight_kg: float | None = None) -> WorkoutResponse:
    return WorkoutResponse(
        id=workout.id,
        workout_date=workout.workout_date,
        name=workout.name,
        notes=workout.notes,
        duration_minutes=workout.duration_minutes,
        calories_burned=estimate_workout_calories(workout, body_weight_kg),
        created_at=workout.created_at,
        exercises=[
            ExerciseResponse(
                id=ex.id,
                exercise_name=ex.exercise_name,
                order_index=ex.order_index,
                notes=ex.notes,
                sets=[
                    SetResponse(
                        id=s.id,
                        set_number=s.set_number,
                        weight_kg=s.weight_kg,
                        reps=s.reps,
                        time_seconds=s.time_seconds,
                        rest_seconds=s.rest_seconds,
                        drop_stages=[
                            DropStageResponse(
                                id=stage.id,
                                stage_number=stage.stage_number,
                                weight_kg=stage.weight_kg,
                                reps=stage.reps,
                            )
                            for stage in sorted(s.drop_stages, key=lambda d: d.stage_number)
                        ],
                    )
                    for s in sorted(ex.sets, key=lambda x: x.set_number)
                ],
            )
            for ex in sorted(workout.exercises, key=lambda x: x.order_index)
        ],
    )
