from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, ForeignKey, String, Text, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ExerciseProgressSummary(Base):
    """Cached per-exercise progress + AI targets — avoids resending full workout history to Gemini."""

    __tablename__ = "exercise_progress_summaries"
    __table_args__ = (UniqueConstraint("user_id", "exercise_key", name="uq_user_exercise_progress"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    exercise_name: Mapped[str] = mapped_column(String(255), nullable=False)
    exercise_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    sessions_count: Mapped[int] = mapped_column(Integer, default=0)
    last_session_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_workout_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    current_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    previous_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    previous_reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trend: Mapped[str] = mapped_column(String(32), default="new")

    next_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    next_reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_session_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    recent_sessions_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    progress_summary_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ai_context_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    history_updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ai_refreshed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="exercise_progress_summaries")


from app.models.user import User  # noqa: E402
