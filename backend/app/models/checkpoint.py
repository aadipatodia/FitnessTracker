from datetime import datetime, date

from sqlalchemy import DateTime, Integer, ForeignKey, Date, String, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Checkpoint(Base):
    __tablename__ = "checkpoint_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="checkpoints")
    completions: Mapped[list["CheckpointCompletion"]] = relationship(
        "CheckpointCompletion", back_populates="checkpoint", cascade="all, delete-orphan"
    )


class CheckpointCompletion(Base):
    __tablename__ = "checkpoint_completions"
    __table_args__ = (
        UniqueConstraint("checkpoint_id", "log_date", name="uq_checkpoint_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    checkpoint_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("checkpoint_items.id", ondelete="CASCADE"), nullable=False
    )
    log_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="checkpoint_completions")
    checkpoint: Mapped["Checkpoint"] = relationship("Checkpoint", back_populates="completions")


from app.models.user import User  # noqa: E402
