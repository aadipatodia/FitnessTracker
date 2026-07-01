from datetime import datetime

from sqlalchemy import String, DateTime, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    goals: Mapped[list["FitnessGoal"]] = relationship("FitnessGoal", back_populates="user")
    workouts: Mapped[list["Workout"]] = relationship("Workout", back_populates="user")
    diet_logs: Mapped[list["DietLog"]] = relationship("DietLog", back_populates="user")
    body_metrics: Mapped[list["BodyMetric"]] = relationship("BodyMetric", back_populates="user")
    recovery_logs: Mapped[list["RecoveryLog"]] = relationship("RecoveryLog", back_populates="user")
    activity_logs: Mapped[list["ActivityLog"]] = relationship("ActivityLog", back_populates="user")
    coaching_insights: Mapped[list["CoachingInsight"]] = relationship("CoachingInsight", back_populates="user")
    checkpoints: Mapped[list["Checkpoint"]] = relationship("Checkpoint", back_populates="user")
    checkpoint_completions: Mapped[list["CheckpointCompletion"]] = relationship(
        "CheckpointCompletion", back_populates="user"
    )
