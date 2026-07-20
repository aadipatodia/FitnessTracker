import io
from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from PIL import Image
from sqlalchemy.orm import Session, joinedload

from app.activity_log import log_action
from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.diet import DietLog, DietEntry
from app.schemas import (
    DietEntryResponse,
    DietLogCreate,
    DietLogEntriesCreate,
    DietLogResponse,
    MealPhotoAnalysisResponse,
)
from app.services import gemini as gemini_service
from app.services.nutrition import NutritionService

router = APIRouter(prefix="/diet", tags=["diet"])

MAX_PHOTO_BYTES = 10 * 1024 * 1024  # 10MB


@router.post("/log-photo", response_model=MealPhotoAnalysisResponse)
async def analyze_meal_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Analyze a meal photo with Gemini vision and return an estimate. Nothing is saved here —
    the frontend must show the user a review screen and call /log-entries to persist it."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="No photo was uploaded.")
    if len(content) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=400, detail="Photo is too large (max 10MB). Try a smaller image.")

    try:
        image = Image.open(io.BytesIO(content))
        image.load()
        img_format = (image.format or "JPEG").upper()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="This doesn't look like a valid image. Please try a different photo.",
        )

    mime_type = "image/jpeg" if img_format == "JPEG" else f"image/{img_format.lower()}"

    try:
        result = await gemini_service.analyze_meal_photo(content, mime_type)
    except gemini_service.GeminiVisionError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    normalized = _normalize_photo_result(result)
    log_action(
        current_user,
        "analyzed a meal photo",
        f"{len(normalized['items'])} item(s) detected, confidence={normalized['confidence']}",
    )
    return normalized


@router.post("/log-entries", response_model=DietLogResponse)
def log_diet_entries(
    data: DietLogEntriesCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save pre-computed entries (from a reviewed/edited photo estimate, or added manually)
    directly — no Gemini call, so the user's confirmed numbers are saved exactly as shown."""
    diet_log = DietLog(
        user_id=current_user.id,
        log_date=data.log_date,
        meal_type=data.meal_type,
    )
    db.add(diet_log)
    db.flush()

    for entry in data.entries:
        db.add(DietEntry(
            diet_log_id=diet_log.id,
            raw_input=entry.food_name,
            food_name=entry.food_name,
            quantity=entry.quantity,
            unit=entry.unit,
            calories=entry.calories,
            protein_g=entry.protein_g,
            carbs_g=entry.carbs_g,
            fat_g=entry.fat_g,
            fibre_g=entry.fibre_g,
            source=entry.source,
        ))

    db.commit()
    db.refresh(diet_log)
    response = _to_response(diet_log)
    log_action(
        current_user,
        f"logged {data.meal_type or 'meal'} for {data.log_date} from a meal photo",
        f"{response.total_calories:.0f} kcal "
        f"({response.total_protein:.0f}P/{response.total_carbs:.0f}C/{response.total_fat:.0f}F), "
        f"{len(response.entries)} item(s)",
    )
    return response


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


def _normalize_photo_result(parsed: dict) -> dict:
    """Coerce Gemini's raw parsed JSON into a well-formed MealPhotoAnalysisResponse shape,
    tolerating missing/malformed fields instead of letting FastAPI's response validation 500."""
    raw_items = parsed.get("items")
    items = []
    if isinstance(raw_items, list):
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            try:
                items.append({
                    "name": str(item.get("name") or "Unknown item"),
                    "estimated_quantity": str(item.get("estimated_quantity") or "1 serving"),
                    "calories": float(item.get("calories") or 0),
                    "protein_g": float(item.get("protein_g") or 0),
                    "carbs_g": float(item.get("carbs_g") or 0),
                    "fat_g": float(item.get("fat_g") or 0),
                })
            except (TypeError, ValueError):
                continue

    if not items:
        raise HTTPException(
            status_code=502,
            detail="Gemini couldn't identify any food items in this photo. Try a clearer photo.",
        )

    raw_total = parsed.get("total") if isinstance(parsed.get("total"), dict) else {}
    try:
        total = {
            "calories": float(raw_total.get("calories", 0)) or sum(i["calories"] for i in items),
            "protein_g": float(raw_total.get("protein_g", 0)) or sum(i["protein_g"] for i in items),
            "carbs_g": float(raw_total.get("carbs_g", 0)) or sum(i["carbs_g"] for i in items),
            "fat_g": float(raw_total.get("fat_g", 0)) or sum(i["fat_g"] for i in items),
        }
    except (TypeError, ValueError):
        total = {
            "calories": sum(i["calories"] for i in items),
            "protein_g": sum(i["protein_g"] for i in items),
            "carbs_g": sum(i["carbs_g"] for i in items),
            "fat_g": sum(i["fat_g"] for i in items),
        }

    confidence = str(parsed.get("confidence") or "medium").lower()
    if confidence not in ("low", "medium", "high"):
        confidence = "medium"

    return {"items": items, "total": total, "confidence": confidence}


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
