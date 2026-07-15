from datetime import datetime, date

from sqlalchemy import String, DateTime, Float, Integer, ForeignKey, Text, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Workout(Base):
    __tablename__ = "workouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    workout_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="workouts")
    exercises: Mapped[list["WorkoutExercise"]] = relationship(
        "WorkoutExercise", back_populates="workout", cascade="all, delete-orphan"
    )


class WorkoutExercise(Base):
    __tablename__ = "workout_exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    workout_id: Mapped[int] = mapped_column(Integer, ForeignKey("workouts.id"), nullable=False)
    exercise_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    workout: Mapped["Workout"] = relationship("Workout", back_populates="exercises")
    sets: Mapped[list["ExerciseSet"]] = relationship(
        "ExerciseSet", back_populates="exercise", cascade="all, delete-orphan"
    )


class ExerciseSet(Base):
    __tablename__ = "exercise_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    exercise_id: Mapped[int] = mapped_column(Integer, ForeignKey("workout_exercises.id"), nullable=False)
    set_number: Mapped[int] = mapped_column(Integer, nullable=False)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    time_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rest_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    exercise: Mapped["WorkoutExercise"] = relationship("WorkoutExercise", back_populates="sets")
    drop_stages: Mapped[list["DropSetStage"]] = relationship(
        "DropSetStage",
        back_populates="set",
        cascade="all, delete-orphan",
        order_by="DropSetStage.stage_number",
    )


class DropSetStage(Base):
    """An additional weight/rep stage within a drop set (stage 1 is the ExerciseSet itself)."""

    __tablename__ = "drop_set_stages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    set_id: Mapped[int] = mapped_column(Integer, ForeignKey("exercise_sets.id"), nullable=False)
    stage_number: Mapped[int] = mapped_column(Integer, nullable=False)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    reps: Mapped[int | None] = mapped_column(Integer, nullable=True)

    set: Mapped["ExerciseSet"] = relationship("ExerciseSet", back_populates="drop_stages")

from app.models.user import User  # noqa: E402
