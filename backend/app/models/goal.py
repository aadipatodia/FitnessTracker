import enum
from datetime import datetime

from sqlalchemy import String, DateTime, Enum, Float, Integer, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class GoalType(str, enum.Enum):
    REDUCE_BODY_FAT = "reduce_body_fat"
    LOSE_FAT_GAIN_MUSCLE = "lose_fat_gain_muscle"
    INCREASE_STRENGTH = "increase_strength"
    GENERAL_FITNESS = "general_fitness"


class FitnessGoal(Base):
    __tablename__ = "fitness_goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    goal_type: Mapped[GoalType] = mapped_column(Enum(GoalType), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Target metrics
    target_body_fat: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_body_fat: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_exercise: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_weight_lifted: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Nutrition targets
    target_calories: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_protein: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    target_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="goals")

from app.models.user import User  # noqa: E402
