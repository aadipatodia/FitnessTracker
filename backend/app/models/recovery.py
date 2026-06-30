from datetime import datetime, date

from sqlalchemy import DateTime, Float, Integer, ForeignKey, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RecoveryLog(Base):
    __tablename__ = "recovery_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    log_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    water_liters: Mapped[float | None] = mapped_column(Float, nullable=True)
    steps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="recovery_logs")

from app.models.user import User  # noqa: E402
