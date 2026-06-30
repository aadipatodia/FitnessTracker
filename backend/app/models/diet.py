from datetime import datetime, date

from sqlalchemy import String, DateTime, Float, Integer, ForeignKey, Text, Date, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DietLog(Base):
    __tablename__ = "diet_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    log_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    meal_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # breakfast, lunch, dinner, snack
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="diet_logs")
    entries: Mapped[list["DietEntry"]] = relationship(
        "DietEntry", back_populates="diet_log", cascade="all, delete-orphan"
    )


class DietEntry(Base):
    __tablename__ = "diet_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    diet_log_id: Mapped[int] = mapped_column(Integer, ForeignKey("diet_logs.id"), nullable=False)
    raw_input: Mapped[str] = mapped_column(Text, nullable=False)
    food_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    unit: Mapped[str] = mapped_column(String(50), default="serving")
    calories: Mapped[float] = mapped_column(Float, default=0)
    protein_g: Mapped[float] = mapped_column(Float, default=0)
    carbs_g: Mapped[float] = mapped_column(Float, default=0)
    fat_g: Mapped[float] = mapped_column(Float, default=0)
    source: Mapped[str] = mapped_column(String(50), default="database")  # database | gemini
    food_item_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("food_items.id"), nullable=True)

    diet_log: Mapped["DietLog"] = relationship("DietLog", back_populates="entries")
    food_item: Mapped["FoodItem | None"] = relationship("FoodItem")

from app.models.user import User  # noqa: E402
from app.models.food import FoodItem  # noqa: E402
