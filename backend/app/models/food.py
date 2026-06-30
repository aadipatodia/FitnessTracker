from datetime import datetime

from sqlalchemy import String, DateTime, Float, Integer, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FoodItem(Base):
    __tablename__ = "food_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    aliases: Mapped[list | None] = mapped_column(JSON, default=list)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    serving_size: Mapped[float] = mapped_column(Float, default=1.0)
    serving_unit: Mapped[str] = mapped_column(String(50), default="serving")
    calories: Mapped[float] = mapped_column(Float, nullable=False)
    protein_g: Mapped[float] = mapped_column(Float, default=0)
    carbs_g: Mapped[float] = mapped_column(Float, default=0)
    fat_g: Mapped[float] = mapped_column(Float, default=0)
    region: Mapped[str | None] = mapped_column(String(50), default="indian")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
