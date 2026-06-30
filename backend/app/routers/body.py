import os
import uuid

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.body import BodyMetric
from app.schemas import BodyMetricCreate, BodyMetricResponse

router = APIRouter(prefix="/body", tags=["body"])


@router.post("/metrics", response_model=BodyMetricResponse)
def create_body_metric(
    data: BodyMetricCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    metric = BodyMetric(
        user_id=current_user.id,
        recorded_date=data.recorded_date,
        weight_kg=data.weight_kg,
        body_fat_percent=data.body_fat_percent,
        waist_cm=data.waist_cm,
        notes=data.notes,
    )
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return metric


@router.get("/metrics", response_model=list[BodyMetricResponse])
def list_body_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    metrics = (
        db.query(BodyMetric)
        .filter(BodyMetric.user_id == current_user.id)
        .order_by(BodyMetric.recorded_date.desc())
        .all()
    )
    return metrics


@router.delete("/metrics/{metric_id}", status_code=204)
def delete_body_metric(
    metric_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    metric = (
        db.query(BodyMetric)
        .filter(BodyMetric.id == metric_id, BodyMetric.user_id == current_user.id)
        .first()
    )
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")

    if metric.photo_url:
        filename = os.path.basename(metric.photo_url)
        filepath = os.path.join(settings.UPLOAD_DIR, filename)
        if os.path.isfile(filepath):
            os.remove(filepath)

    db.delete(metric)
    db.commit()


@router.post("/metrics/{metric_id}/photo", response_model=BodyMetricResponse)
async def upload_progress_photo(
    metric_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    metric = (
        db.query(BodyMetric)
        .filter(BodyMetric.id == metric_id, BodyMetric.user_id == current_user.id)
        .first()
    )
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or "photo.jpg")[1] or ".jpg"
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(settings.UPLOAD_DIR, filename)

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    metric.photo_url = f"/uploads/{filename}"
    db.commit()
    db.refresh(metric)
    return metric
