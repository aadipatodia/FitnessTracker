from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.recovery import RecoveryLog
from app.schemas import RecoveryLogCreate, RecoveryLogResponse

router = APIRouter(prefix="/recovery", tags=["recovery"])


@router.post("/log", response_model=RecoveryLogResponse)
def log_recovery(
    data: RecoveryLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = (
        db.query(RecoveryLog)
        .filter(RecoveryLog.user_id == current_user.id, RecoveryLog.log_date == data.log_date)
        .first()
    )
    if existing:
        existing.sleep_hours = data.sleep_hours
        existing.water_liters = data.water_liters
        existing.steps = data.steps
        db.commit()
        db.refresh(existing)
        return existing

    log = RecoveryLog(
        user_id=current_user.id,
        log_date=data.log_date,
        sleep_hours=data.sleep_hours,
        water_liters=data.water_liters,
        steps=data.steps,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("/logs", response_model=list[RecoveryLogResponse])
def list_recovery_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logs = (
        db.query(RecoveryLog)
        .filter(RecoveryLog.user_id == current_user.id)
        .order_by(RecoveryLog.log_date.desc())
        .limit(30)
        .all()
    )
    return logs


@router.delete("/logs/{log_id}", status_code=204)
def delete_recovery_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    log = (
        db.query(RecoveryLog)
        .filter(RecoveryLog.id == log_id, RecoveryLog.user_id == current_user.id)
        .first()
    )
    if not log:
        raise HTTPException(status_code=404, detail="Recovery log not found")
    db.delete(log)
    db.commit()
