import enum
from datetime import datetime

from sqlalchemy import String, DateTime, Enum, Integer, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class InsightType(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    PROGRESSION = "progression"
    NUTRITION = "nutrition"
    GOAL_ESTIMATE = "goal_estimate"


class CoachingInsight(Base):
    __tablename__ = "coaching_insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    insight_type: Mapped[InsightType] = mapped_column(Enum(InsightType), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="coaching_insights")

from app.models.user import User  # noqa: E402
