from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.checkpoint import Checkpoint, CheckpointCompletion
from app.schemas import (
    CheckpointCreate,
    CheckpointUpdate,
    CheckpointResponse,
    DailyCheckpointItem,
    DailyCheckpointsResponse,
    CheckpointToggleRequest,
)

router = APIRouter(prefix="/checkpoints", tags=["checkpoints"])


def _daily_item(checkpoint: Checkpoint, completed: bool, completed_at: datetime | None) -> DailyCheckpointItem:
    return DailyCheckpointItem(
        id=checkpoint.id,
        title=checkpoint.title,
        sort_order=checkpoint.sort_order,
        completed=completed,
        completed_at=completed_at,
    )


@router.get("", response_model=list[CheckpointResponse])
def list_checkpoints(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = (
        db.query(Checkpoint)
        .filter(Checkpoint.user_id == current_user.id)
        .order_by(Checkpoint.sort_order, Checkpoint.id)
        .all()
    )
    return items


@router.post("", response_model=CheckpointResponse)
def create_checkpoint(
    data: CheckpointCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    max_order = (
        db.query(Checkpoint.sort_order)
        .filter(Checkpoint.user_id == current_user.id)
        .order_by(Checkpoint.sort_order.desc())
        .first()
    )
    next_order = (max_order[0] + 1) if max_order else 0

    item = Checkpoint(
        user_id=current_user.id,
        title=data.title,
        sort_order=next_order,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{checkpoint_id}", response_model=CheckpointResponse)
def update_checkpoint(
    checkpoint_id: int,
    data: CheckpointUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = (
        db.query(Checkpoint)
        .filter(Checkpoint.id == checkpoint_id, Checkpoint.user_id == current_user.id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    if data.title is not None:
        item.title = data.title
    if data.sort_order is not None:
        item.sort_order = data.sort_order

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{checkpoint_id}", status_code=204)
def delete_checkpoint(
    checkpoint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = (
        db.query(Checkpoint)
        .filter(Checkpoint.id == checkpoint_id, Checkpoint.user_id == current_user.id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    db.delete(item)
    db.commit()


@router.get("/daily", response_model=DailyCheckpointsResponse)
def get_daily_checkpoints(
    log_date: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = (
        db.query(Checkpoint)
        .filter(Checkpoint.user_id == current_user.id)
        .order_by(Checkpoint.sort_order, Checkpoint.id)
        .all()
    )

    completions = (
        db.query(CheckpointCompletion)
        .filter(
            CheckpointCompletion.user_id == current_user.id,
            CheckpointCompletion.log_date == log_date,
        )
        .all()
    )
    completion_map = {c.checkpoint_id: c for c in completions}

    daily_items = [
        _daily_item(
            item,
            completion_map[item.id].completed if item.id in completion_map else False,
            completion_map[item.id].completed_at if item.id in completion_map else None,
        )
        for item in items
    ]

    completed_count = sum(1 for i in daily_items if i.completed)

    return DailyCheckpointsResponse(
        log_date=log_date,
        items=daily_items,
        total=len(daily_items),
        completed_count=completed_count,
    )


@router.put("/daily/toggle", response_model=DailyCheckpointItem)
def toggle_checkpoint(
    data: CheckpointToggleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = (
        db.query(Checkpoint)
        .filter(Checkpoint.id == data.checkpoint_id, Checkpoint.user_id == current_user.id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    now = datetime.utcnow()
    existing = (
        db.query(CheckpointCompletion)
        .filter(
            CheckpointCompletion.checkpoint_id == data.checkpoint_id,
            CheckpointCompletion.log_date == data.log_date,
        )
        .first()
    )

    if existing:
        existing.completed = data.completed
        existing.completed_at = now if data.completed else None
        db.commit()
        completed_at = existing.completed_at
    else:
        completion = CheckpointCompletion(
            user_id=current_user.id,
            checkpoint_id=data.checkpoint_id,
            log_date=data.log_date,
            completed=data.completed,
            completed_at=now if data.completed else None,
        )
        db.add(completion)
        db.commit()
        completed_at = completion.completed_at

    return _daily_item(item, data.completed, completed_at)
