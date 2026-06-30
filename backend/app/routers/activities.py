from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.activity import ActivityLog, ActivityCategory
from app.schemas import ActivityLogCreate, ActivityLogResponse
from app.services.analytics import get_user_body_weight_kg
from app.services.activity_calories import cardio_calories_for_log, fallback_cardio_calories
from app.services.gemini import estimate_cardio_calories

router = APIRouter(prefix="/activities", tags=["activities"])


@router.post("", response_model=ActivityLogResponse)
async def create_activity(
    data: ActivityLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.category != "cardio":
        raise HTTPException(status_code=400, detail="Only cardio activities can be logged")

    body_weight = get_user_body_weight_kg(db, current_user.id)
    estimate = await estimate_cardio_calories(
        data.activity_name.strip(),
        data.duration_minutes,
        body_weight,
    )
    calories = estimate.get("calories_burned")
    if calories is None:
        calories = fallback_cardio_calories(data.duration_minutes, body_weight)

    log = ActivityLog(
        user_id=current_user.id,
        log_date=data.log_date,
        activity_name=data.activity_name.strip(),
        duration_minutes=data.duration_minutes,
        category=ActivityCategory(data.category),
        calories_burned=round(float(calories), 1),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return _to_response(log, body_weight)


@router.get("", response_model=list[ActivityLogResponse])
def list_activities(
    category: str | None = Query(None),
    log_date: date | None = Query(None),
    limit: int = Query(30, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ActivityLog).filter(ActivityLog.user_id == current_user.id)
    if category:
        query = query.filter(ActivityLog.category == ActivityCategory(category))
    if log_date:
        query = query.filter(ActivityLog.log_date == log_date)
    logs = query.order_by(ActivityLog.log_date.desc(), ActivityLog.created_at.desc()).limit(limit).all()
    body_weight = get_user_body_weight_kg(db, current_user.id)
    return [_to_response(log, body_weight) for log in logs]


@router.delete("/{activity_id}", status_code=204)
def delete_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    log = (
        db.query(ActivityLog)
        .filter(ActivityLog.id == activity_id, ActivityLog.user_id == current_user.id)
        .first()
    )
    if not log:
        raise HTTPException(status_code=404, detail="Activity not found")
    db.delete(log)
    db.commit()


def _to_response(log: ActivityLog, body_weight_kg: float | None) -> ActivityLogResponse:
    return ActivityLogResponse(
        id=log.id,
        log_date=log.log_date,
        activity_name=log.activity_name,
        duration_minutes=log.duration_minutes,
        category=log.category.value,
        calories_burned=cardio_calories_for_log(log, body_weight_kg),
        created_at=log.created_at,
    )
