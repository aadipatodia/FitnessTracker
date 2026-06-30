import enum
from datetime import datetime, date

from sqlalchemy import String, DateTime, Float, Integer, ForeignKey, Date, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ActivityCategory(str, enum.Enum):
    CARDIO = "cardio"
    DAILY = "daily"


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    log_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    activity_name: Mapped[str] = mapped_column(String(255), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[ActivityCategory] = mapped_column(Enum(ActivityCategory), nullable=False)
    calories_burned: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="activity_logs")

from app.models.user import User  # noqa: E402
