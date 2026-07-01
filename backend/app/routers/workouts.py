from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.activity_log import log_action
from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.workout import Workout, WorkoutExercise, ExerciseSet
from app.schemas import WorkoutCreate, WorkoutResponse, ExerciseResponse, SetResponse
from app.services.analytics import get_user_body_weight_kg
from app.services.workout_calories import estimate_workout_calories

router = APIRouter(prefix="/workouts", tags=["workouts"])


@router.post("", response_model=WorkoutResponse)
def create_workout(
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

    for ex_data in data.exercises:
        exercise = WorkoutExercise(
            workout_id=workout.id,
            exercise_name=ex_data.exercise_name,
            order_index=ex_data.order_index,
            notes=ex_data.notes,
        )
        db.add(exercise)
        db.flush()

        for set_data in ex_data.sets:
            db.add(ExerciseSet(
                exercise_id=exercise.id,
                set_number=set_data.set_number,
                weight_kg=set_data.weight_kg,
                reps=set_data.reps,
                time_seconds=set_data.time_seconds,
                rest_seconds=set_data.rest_seconds,
            ))

    db.commit()
    workout = (
        db.query(Workout)
        .options(joinedload(Workout.exercises).joinedload(WorkoutExercise.sets))
        .filter(Workout.id == workout.id, Workout.user_id == current_user.id)
        .first()
    )
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
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workouts = (
        db.query(Workout)
        .options(joinedload(Workout.exercises).joinedload(WorkoutExercise.sets))
        .filter(Workout.user_id == current_user.id)
        .order_by(Workout.workout_date.desc())
        .limit(limit)
        .all()
    )
    body_weight = get_user_body_weight_kg(db, current_user.id)
    response = [_to_response(w, body_weight) for w in workouts]
    log_action(
        current_user,
        f"viewed workout history (last {limit})",
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
        .options(joinedload(Workout.exercises).joinedload(WorkoutExercise.sets))
        .filter(Workout.id == workout_id, Workout.user_id == current_user.id)
        .first()
    )
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    body_weight = get_user_body_weight_kg(db, current_user.id)
    return _to_response(workout, body_weight)


@router.delete("/{workout_id}", status_code=204)
def delete_workout(
    workout_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workout = (
        db.query(Workout)
        .filter(Workout.id == workout_id, Workout.user_id == current_user.id)
        .first()
    )
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    db.delete(workout)
    db.commit()


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
                    )
                    for s in sorted(ex.sets, key=lambda x: x.set_number)
                ],
            )
            for ex in sorted(workout.exercises, key=lambda x: x.order_index)
        ],
    )
