from dataclasses import dataclass


@dataclass
class NutritionResult:
    food_name: str
    quantity: float
    unit: str
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fibre_g: float
    source: str
    food_item_id: int | None = None
    raw_input: str = ""


def _meal_items_from_response(data: dict, food_input: str) -> list[dict]:
    items = data.get("items")
    if isinstance(items, list) and items:
        return items

    if "food_name" in data or "calories" in data:
        return [{
            "food_name": data.get("food_name", food_input),
            "quantity": data.get("quantity", 1),
            "unit": data.get("unit", "serving"),
            "calories": data.get("calories", 0),
            "protein_g": data.get("protein_g", 0),
            "carbs_g": data.get("carbs_g", 0),
            "fat_g": data.get("fat_g", 0),
            "fibre_g": data.get("fibre_g", 0),
        }]

    return [{
        "food_name": food_input,
        "quantity": 1,
        "unit": "serving",
        "calories": 0,
        "protein_g": 0,
        "carbs_g": 0,
        "fat_g": 0,
        "fibre_g": 0,
    }]


class NutritionService:
    async def process_food_input(self, text: str) -> list[NutritionResult]:
        from app.services.gemini import estimate_meal_nutrition

        text = text.strip()
        if not text:
            return []

        data = await estimate_meal_nutrition(text)
        return [
            NutritionResult(
                food_name=str(item.get("food_name", text)),
                quantity=float(item.get("quantity", 1)),
                unit=str(item.get("unit", "serving")),
                calories=float(item.get("calories", 0)),
                protein_g=float(item.get("protein_g", 0)),
                carbs_g=float(item.get("carbs_g", 0)),
                fat_g=float(item.get("fat_g", 0)),
                fibre_g=float(item.get("fibre_g", 0)),
                source="gemini",
                raw_input=text,
            )
            for item in _meal_items_from_response(data, text)
        ]
