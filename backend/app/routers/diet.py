from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.activity_log import log_action
from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.diet import DietLog, DietEntry
from app.schemas import DietLogCreate, DietLogResponse, DietEntryResponse
from app.services.nutrition import NutritionService

router = APIRouter(prefix="/diet", tags=["diet"])


@router.post("/log", response_model=DietLogResponse)
async def log_diet(
    data: DietLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    nutrition_service = NutritionService()
    results = await nutrition_service.process_food_input(data.food_input)

    diet_log = DietLog(
        user_id=current_user.id,
        log_date=data.log_date,
        meal_type=data.meal_type,
    )
    db.add(diet_log)
    db.flush()

    for result in results:
        db.add(DietEntry(
            diet_log_id=diet_log.id,
            raw_input=result.raw_input or data.food_input,
            food_name=result.food_name,
            quantity=result.quantity,
            unit=result.unit,
            calories=result.calories,
            protein_g=result.protein_g,
            carbs_g=result.carbs_g,
            fat_g=result.fat_g,
            fibre_g=result.fibre_g,
            source=result.source,
            food_item_id=result.food_item_id,
        ))

    db.commit()
    db.refresh(diet_log)
    response = _to_response(diet_log)
    log_action(
        current_user,
        f"logged {data.meal_type} for {data.log_date}: \"{data.food_input}\"",
        f"{response.total_calories:.0f} kcal "
        f"({response.total_protein:.0f}P/{response.total_carbs:.0f}C/{response.total_fat:.0f}F/{response.total_fibre:.0f}Fi), "
        f"{len(response.entries)} item(s)",
    )
    return response


@router.get("/logs", response_model=list[DietLogResponse])
def list_diet_logs(
    log_date: date | None = Query(None),
    limit: int = Query(30, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        db.query(DietLog)
        .options(joinedload(DietLog.entries))
        .filter(DietLog.user_id == current_user.id)
    )
    if log_date:
        query = query.filter(DietLog.log_date == log_date)
    logs = query.order_by(DietLog.log_date.desc()).limit(limit).all()
    response = [_to_response(log) for log in logs]
    total_kcal = sum(r.total_calories for r in response)
    log_action(
        current_user,
        f"viewed diet history ({log_date or f'last {limit}'})",
        f"{len(response)} meals, {total_kcal:.0f} kcal total",
    )
    return response


@router.delete("/logs/{log_id}", status_code=204)
def delete_diet_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    log = (
        db.query(DietLog)
        .filter(DietLog.id == log_id, DietLog.user_id == current_user.id)
        .first()
    )
    if not log:
        raise HTTPException(status_code=404, detail="Diet log not found")
    log_action(
        current_user,
        f"deleted meal from {log.log_date} ({log.meal_type})",
        "meal removed",
    )
    db.delete(log)
    db.commit()


def _to_response(log: DietLog) -> DietLogResponse:
    entries = [
        DietEntryResponse(
            id=e.id,
            raw_input=e.raw_input,
            food_name=e.food_name,
            quantity=e.quantity,
            unit=e.unit,
            calories=e.calories,
            protein_g=e.protein_g,
            carbs_g=e.carbs_g,
            fat_g=e.fat_g,
            fibre_g=e.fibre_g,
            source=e.source,
        )
        for e in log.entries
    ]
    return DietLogResponse(
        id=log.id,
        log_date=log.log_date,
        meal_type=log.meal_type,
        created_at=log.created_at,
        entries=entries,
        total_calories=sum(e.calories for e in entries),
        total_protein=sum(e.protein_g for e in entries),
        total_carbs=sum(e.carbs_g for e in entries),
        total_fat=sum(e.fat_g for e in entries),
        total_fibre=sum(e.fibre_g for e in entries),
    )
