from app.services.nutrition import _meal_items_from_response, NutritionService


def test_meal_items_from_response_list():
    data = {
        "items": [
            {
                "food_name": "mixed parathas",
                "quantity": 2,
                "unit": "piece",
                "calories": 400,
                "protein_g": 12,
                "carbs_g": 50,
                "fat_g": 18,
            },
            {
                "food_name": "curd",
                "quantity": 1,
                "unit": "serving",
                "calories": 60,
                "protein_g": 4,
                "carbs_g": 5,
                "fat_g": 3,
            },
        ]
    }
    items = _meal_items_from_response(data, "fallback")
    assert len(items) == 2
    assert items[0]["food_name"] == "mixed parathas"
    assert items[1]["food_name"] == "curd"


def test_meal_items_from_legacy_single_item():
    data = {
        "food_name": "paneer",
        "quantity": 150,
        "unit": "g",
        "calories": 300,
        "protein_g": 25,
        "carbs_g": 10,
        "fat_g": 20,
    }
    items = _meal_items_from_response(data, "150g paneer")
    assert len(items) == 1
    assert items[0]["food_name"] == "paneer"
    assert items[0]["quantity"] == 150


def test_nutrition_service_maps_gemini_items():
    class FakeGemini:
        async def estimate_meal_nutrition(self, text):
            return {
                "items": [
                    {
                        "food_name": "milk",
                        "quantity": 1,
                        "unit": "glass",
                        "calories": 160,
                        "protein_g": 8,
                        "carbs_g": 12,
                        "fat_g": 8,
                    },
                    {
                        "food_name": "whey protein",
                        "quantity": 1,
                        "unit": "scoop",
                        "calories": 120,
                        "protein_g": 24,
                        "carbs_g": 3,
                        "fat_g": 2,
                    },
                ]
            }

    import app.services.gemini as gemini_mod

    original = gemini_mod.estimate_meal_nutrition
    gemini_mod.estimate_meal_nutrition = FakeGemini().estimate_meal_nutrition

    import asyncio

    service = NutritionService()
    results = asyncio.run(service.process_food_input("1 glass milk and 1 scoop whey protein"))
    gemini_mod.estimate_meal_nutrition = original

    assert len(results) == 2
    assert results[0].food_name == "milk"
    assert results[0].unit == "glass"
    assert results[1].food_name == "whey protein"
    assert all(r.raw_input == "1 glass milk and 1 scoop whey protein" for r in results)
