import asyncio
import json
import logging
import re
import time
from datetime import date, datetime, timedelta

import google.generativeai as genai
from dateutil import parser as date_parser

from app.config import settings
from app.logging_setup import configure_logger
from app.services.goal_nutrition import apply_stated_nutrition_targets, parse_stated_nutrition_targets

logger = logging.getLogger("gemini")

INDIA_CONTEXT = (
    "CONTEXT (important): All users are Indian. Food products and logged meals are Indian "
    "cuisine and locally available brands/portions. Estimate calories, protein, carbs, fat, "
    "and all nutrition breakdowns using Indian food reference values — not US/Western databases."
)


def setup_gemini_logging() -> None:
    configure_logger("gemini", "gemini.log")


def _configure_gemini():
    if settings.GEMINI_API_KEY:
        genai.configure(api_key=settings.GEMINI_API_KEY)


def _parse_json_response(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    return json.loads(text)


def _format_user_input(user_input) -> str:
    if isinstance(user_input, str):
        return user_input
    return json.dumps(user_input, indent=2, default=str)


def _log_gemini_exchange(
    operation: str,
    user_input,
    *,
    status: str,
    duration_ms: float | None = None,
    raw_response: str | None = None,
    parsed: dict | None = None,
    error: str | None = None,
    note: str | None = None,
) -> None:
    header_parts = [f"operation={operation}", f"status={status}", f"model={settings.GEMINI_MODEL}"]
    if duration_ms is not None:
        header_parts.append(f"duration={duration_ms:.0f}ms")
    if note:
        header_parts.append(f"note={note}")
    if error:
        header_parts.append(f"error={error}")

    lines = ["── Gemini call ──", " | ".join(header_parts), f"User input:\n{_format_user_input(user_input)}"]
    if raw_response:
        lines.append(f"Gemini response:\n{raw_response.strip()}")
    if parsed is not None:
        lines.append(f"Parsed result:\n{json.dumps(parsed, indent=2, default=str)}")
    logger.info("\n".join(lines))


def _generate_json(operation: str, user_input, prompt: str, fallback: dict) -> dict:
    _configure_gemini()

    if not settings.GEMINI_API_KEY:
        _log_gemini_exchange(
            operation,
            user_input,
            status="skipped",
            note="no GEMINI_API_KEY",
            parsed=fallback,
        )
        return fallback

    model = genai.GenerativeModel(settings.GEMINI_MODEL)
    started = time.perf_counter()
    try:
        response = model.generate_content(prompt)
        elapsed_ms = (time.perf_counter() - started) * 1000
        raw = response.text
        parsed = _parse_json_response(raw)
        _log_gemini_exchange(
            operation,
            user_input,
            status="ok",
            duration_ms=elapsed_ms,
            raw_response=raw,
            parsed=parsed,
        )
        return parsed
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000
        _log_gemini_exchange(
            operation,
            user_input,
            status="fallback",
            duration_ms=elapsed_ms,
            parsed=fallback,
            error=f"{exc.__class__.__name__}: {exc}",
        )
        return fallback


async def _generate_json_async(operation: str, user_input, prompt: str, fallback: dict) -> dict:
    """Run blocking Gemini HTTP calls off the event loop so other requests stay responsive."""
    return await asyncio.to_thread(_generate_json, operation, user_input, prompt, fallback)


async def estimate_meal_nutrition(food_input: str) -> dict:
    """Use Gemini to parse a meal description and estimate nutrition for each item."""
    fallback = {
        "items": [
            {
                "food_name": food_input,
                "quantity": 1,
                "unit": "serving",
                "calories": 0,
                "protein_g": 0,
                "carbs_g": 0,
                "fat_g": 0,
                "fibre_g": 0,
            }
        ]
    }

    prompt = f"""You are a nutrition expert. Parse the user's meal description into distinct food items and estimate macros for each.

{INDIA_CONTEXT}

User input: {food_input}

Rules:
- Break the input into separate items only when the user clearly listed multiple foods (e.g. "2 rotis + dal + curd", "milk and whey protein").
- Do NOT split ingredient lists inside one dish (e.g. "parathas with onions, paneer and potato" is ONE item).
- Respect stated quantities and units (1 glass milk ≈ 250ml, 1 scoop whey ≈ 30g powder).
- Use typical Indian portions when relevant (roti, dal bowl, glass of doodh, paratha, etc.).
- Return totals for each item as listed, not per 100g.
- Use realistic values (e.g. 1 glass whole milk ≈ 150-170 kcal, ~8-10g protein).
- Estimate dietary fibre (fibre_g) for each item — whole grains, roti, dal, vegetables, fruit, etc.

Return ONLY valid JSON with no markdown:
{{
  "items": [
    {{
      "food_name": "short display name",
      "quantity": number,
      "unit": "glass|bowl|piece|scoop|g|serving|etc",
      "calories": number,
      "protein_g": number,
      "carbs_g": number,
      "fat_g": number,
      "fibre_g": number
    }}
  ]
}}"""

    return await _generate_json_async("meal_nutrition", {"food_input": food_input}, prompt, fallback)


async def estimate_cardio_calories(
    activity_name: str,
    duration_minutes: int,
    body_weight_kg: float | None = None,
) -> dict:
    """Use Gemini to estimate kcal burned for a logged cardio session."""
    weight = body_weight_kg or 75.0
    fallback = {
        "calories_burned": round(5.0 * weight * (duration_minutes / 60.0), 1),
        "notes": "Fallback estimate — Gemini unavailable.",
    }

    prompt = f"""You are an exercise physiology expert. Estimate calories burned for this cardio session.

Activity: {activity_name}
Duration: {duration_minutes} minutes
Body weight: {weight} kg

Use standard MET values for the described activity and intensity implied by the name.
Formula: calories = MET × body_weight_kg × (duration_minutes / 60).
Be realistic for the activity type and typical effort (e.g. easy walk vs sprint intervals).

Return ONLY valid JSON (no markdown):
{{
  "calories_burned": number,
  "met_used": number,
  "notes": "brief one-line reasoning"
}}"""

    return await _generate_json_async(
        "cardio_calories",
        {
            "activity_name": activity_name,
            "duration_minutes": duration_minutes,
            "body_weight_kg": weight,
        },
        prompt,
        fallback,
    )


async def generate_coaching_analysis(user_data: dict, analysis_type: str = "daily") -> dict:
    """Generate AI coaching insights from user fitness data."""
    fallback = _fallback_coaching(user_data, analysis_type)
    analysis_date = user_data.get("analysis_date", "today")
    stats_through = user_data.get("stats_through_date", analysis_date)
    data_date = user_data.get("data_date", stats_through)
    stats_basis_note = user_data.get(
        "stats_basis_note",
        f"Analysis based on stats through {stats_through}.",
    )
    stats_scope_rule = (
        f"STATS SCOPE (mandatory — mention this in your first insight):\n"
        f"- {stats_basis_note}\n"
        f"- Use ONLY data through {stats_through}. Do not infer or assume stats for later dates."
    )
    recovery_rules = (
        "RECOVERY SCORE RULES (from recovery_score_info in user data):\n"
        "- recovery_score uses ONLY sleep_hours and water_liters.\n"
        "- Do NOT mention steps or activity tracking in recovery advice.\n"
        "- If recovery_score is low, cite missing sleep and/or water only."
    )
    calorie_rules = (
        "CALORIE RULES:\n"
        "- calories_consumed comes from logged diet entries.\n"
        "- calories_burned_everyday_movement is AUTO-ESTIMATED from body weight only (NEAT): "
        "walking at home, kitchen trips, light chores (~2.3 MET × 2h). NOT resting metabolism.\n"
        "- Do NOT ask the user to log everyday movement — it is estimated automatically.\n"
        "- Resting metabolism (BMR) is NOT included in burn numbers; the intake target already accounts for base body needs.\n"
        "- Logged exercise burn = strength workouts + cardio sessions (cardio kcal estimated by AI at log time).\n"
        "- calories_burned_active_total = everyday_movement + exercise.\n"
        "- target_calorie_burn adjusts to intake: if over target, it equals intake_surplus_after_exercise "
        "(extra exercise burn still needed after crediting logged workouts/cardio); "
        "if on track, it is the minimum per workout (~45 min strength, scaled to body weight).\n"
        "- calories_over_target = max(0, consumed - target).\n"
        "- intake_surplus_after_exercise = max(0, calories_over_target - exercise_burn).\n"
        "- Explain intake vs target and how movement (everyday + exercise) affects their plan."
    )

    if analysis_type == "goal":
        prompt = f"""You are an expert fitness coach. Analyze the user's cumulative progress toward their active goal and give actionable advice to reach it by the deadline.

{INDIA_CONTEXT}

{stats_scope_rule}

Data is a compact summary from goal start through {stats_through} (user selected {analysis_date}). Use goal_progress for metrics — do not invent data.

{recovery_rules}

{calorie_rules}

User Data:
{json.dumps(user_data, indent=2, default=str)}

If has_goal is false, return one insight encouraging them to set a goal.

DEADLINE RULES:
- If goal_progress.weeks_until_deadline / days_until_deadline is null, the user has no target date. Recommend the best realistic completion timeline based on their age, gender, current body metrics, progress so far, and goal type. Set goal_completion_weeks to your recommended estimate.
- For women: account for perimenopause/menopause and related recovery/metabolic factors when age-appropriate (~45+).
- For men: account for age-related recovery and muscle-loss considerations when age-appropriate (40+).
- If a deadline exists, assess on-track status vs that date and set goal_completion_weeks only if you have a revised estimate.

Return ONLY valid JSON (no markdown):
{{
  "title": "Goal Progress",
  "insights": [
    {{"type": "goal_estimate", "title": "string", "content": "string"}},
    {{"type": "nutrition", "title": "string", "content": "string"}},
    {{"type": "progression", "title": "string", "content": "string"}}
  ],
  "calorie_recommendation": number or null,
  "protein_recommendation": number or null,
  "goal_completion_weeks": number or null
}}

Insight type MUST be one of: daily, weekly, progression, nutrition, goal_estimate.

WORKOUT PROGRESS RULES:
- Use goal_progress.training.exercise_progress to compare the same exercise across sessions (previous_session vs latest_session; first_session when present).
- In the progression insight, cite concrete before/after numbers, e.g. "Last deadlift: 80 kg × 3 reps → now 80 kg × 4 reps".
- Note weight increases, rep increases at the same weight, plateaus, or regressions. Prioritize the user's target exercise when set on the goal.
- If exercise_progress is empty, say no repeat exercises logged yet to compare.

Cover: current progress vs targets; if no deadline, a recommended timeline with goal_completion_weeks; if a deadline exists, whether they are on track, weekly rate needed to hit it; calorie/protein adherence including workout burn totals; workout/strength progression from exercise_progress; and 2-3 specific adjustments (training, nutrition, recovery). Be concrete with numbers."""
    elif analysis_type == "weekly":
        prompt = f"""You are an expert fitness coach. Analyze the user's week using the pre-computed weekly_summary (compact daily rollups — do NOT ask for more data).

{INDIA_CONTEXT}

{stats_scope_rule}

The week ends on {stats_through} ({user_data.get("period_start")} to {user_data.get("period_end")}). User selected {analysis_date}.

Sleep in daily_rollups is the night before that date through the morning of that date. Water/recovery_score are for the calendar day.

{recovery_rules}

{calorie_rules}

Also use goal_progress for deadline-aware advice.

User Data:
{json.dumps(user_data, indent=2, default=str)}

Return ONLY valid JSON (no markdown):
{{
  "title": "Weekly Summary",
  "insights": [
    {{"type": "weekly", "title": "string", "content": "string"}},
    {{"type": "progression", "title": "string", "content": "string"}},
    {{"type": "nutrition", "title": "string", "content": "string"}},
    {{"type": "goal_estimate", "title": "string", "content": "string"}}
  ],
  "calorie_recommendation": number,
  "protein_recommendation": number,
  "goal_completion_weeks": number or null
}}

Insight type MUST be one of: daily, weekly, progression, nutrition, goal_estimate.

Reference strength_changes and daily_rollups (include calories_burned per day). Include one goal_estimate insight on deadline progress."""
    else:
        prompt = f"""You are an expert fitness coach. Analyze ONLY the single day {data_date}.

{INDIA_CONTEXT}

{stats_scope_rule}

CRITICAL RULES:
- Every insight MUST be about {data_date} only.
- Do NOT mention workouts, nutrition, or recovery from any other date.
- If there was no workout that day, say so — do not analyze other days' lifts.
- Use workouts array (only this day's sessions), nutrition_for_date, calories_burned_for_date, calorie_balance, recovery_for_analysis_date, and recovery_score.

{recovery_rules}

{calorie_rules}

Sleep for {data_date} is the night before through the morning of that date.

User Data:
{json.dumps(user_data, indent=2, default=str)}

Return ONLY valid JSON (no markdown):
{{
  "title": "Daily Coaching",
  "insights": [
    {{"type": "daily", "title": "Today's Action Plan", "content": "string — kcal eaten vs intake target, auto everyday movement (NEAT) + logged exercise, intake surplus after exercise, protein gap, one concrete next step"}},
    {{"type": "nutrition", "title": "string", "content": "string"}},
    {{"type": "progression", "title": "string", "content": "string"}}
  ],
  "calorie_recommendation": number or null,
  "protein_recommendation": number or null
}}

Insight type MUST be one of: daily, weekly, progression, nutrition, goal_estimate.

The first insight MUST be a concrete action plan with numbers from calorie_balance. Be specific: mention exact protein numbers, calories consumed/burned/net, weight/rep details from that day's workout only, recovery quality for that day."""

    return await _generate_json_async(
        f"coaching_{analysis_type}",
        {"analysis_type": analysis_type, "user_data": user_data},
        prompt,
        fallback,
    )


async def generate_goal_guidance(
    goal_type: str,
    end_goal: str | None = None,
    *,
    gender: str | None = None,
    age: int | None = None,
) -> dict:
    """Personalized coaching tips for goal onboarding."""
    fallback = {
        "title": "Your coaching plan",
        "tips": ["We'll personalize guidance once your goal is saved."],
    }

    profile = []
    if gender:
        profile.append(f"Gender: {gender}")
    if age is not None:
        profile.append(f"Age: {age}")

    prompt = f"""You are an expert fitness coach helping a user set up their goal.

{INDIA_CONTEXT}

Goal categories: {goal_type}
User's end goal: {end_goal or "Not specified yet"}
{"User profile: " + ", ".join(profile) if profile else "User profile: not provided yet"}

Return ONLY valid JSON (no markdown):
{{
  "title": "short coaching focus title",
  "tips": ["actionable tip 1", "actionable tip 2", "actionable tip 3"]
}}

Tailor tips to their stated end goal, category, age, and gender when provided. Be specific and practical. Keep each tip under 120 characters."""

    return await _generate_json_async(
        "goal_guidance",
        {"goal_type": goal_type, "end_goal": end_goal, "gender": gender, "age": age},
        prompt,
        fallback,
    )


def _parse_date_from_text(text: str) -> date | None:
    if not text:
        return None

    iso_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if iso_match:
        try:
            return date.fromisoformat(iso_match.group(1))
        except ValueError:
            pass

    dmy_match = re.search(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b", text)
    if dmy_match:
        day, month, year = (int(dmy_match.group(i)) for i in range(1, 4))
        try:
            return date(year, month, day)
        except ValueError:
            pass

    for pattern in (
        r"\d{1,2}\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
        r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{4}",
        r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
        r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
        r"\s+\d{1,2},?\s+\d{4}",
    ):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return date_parser.parse(match.group(0), dayfirst=True).date()
            except (ValueError, OverflowError):
                pass

    return None


def _parse_target_date(goal_data: dict) -> date | None:
    raw = goal_data.get("target_date")
    if raw is not None:
        if isinstance(raw, date):
            return raw
        if isinstance(raw, datetime):
            return raw.date()
        if isinstance(raw, str) and raw.strip():
            return date.fromisoformat(raw)

    return _parse_date_from_text(goal_data.get("end_goal") or "")


def _weeks_until(target: date, today: date | None = None) -> int:
    today = today or date.today()
    days = max(0, (target - today).days)
    if days == 0:
        return 0
    return max(1, (days + 6) // 7)


def estimate_recommended_weeks(goal_data: dict) -> int:
    """Evidence-based timeline when FitAI is unavailable (matches coaching prompt rates)."""
    goal_type = (goal_data.get("goal_type") or "").lower()
    age = goal_data.get("age")
    age_factor = 1.15 if age and age >= 45 else 1.0

    current_bf = goal_data.get("current_body_fat")
    target_bf = goal_data.get("target_body_fat")
    if current_bf and target_bf and current_bf > target_bf:
        if "recomp" in goal_type or "muscle" in goal_type:
            weeks = (current_bf - target_bf) / 0.2
        else:
            weeks = (current_bf - target_bf) / 0.35
        return max(4, int(weeks * age_factor))

    current_w = goal_data.get("current_weight")
    target_w = goal_data.get("target_weight")
    if current_w and target_w and abs(current_w - target_w) >= 0.5:
        delta = abs(current_w - target_w)
        weeks = delta / 0.5 if current_w > target_w else delta / 0.35
        return max(4, int(weeks * age_factor))

    current_lift = goal_data.get("current_weight_lifted")
    target_lift = goal_data.get("target_weight_lifted")
    if target_lift and "strength" in goal_type:
        baseline = current_lift or (target_lift * 0.7)
        gap = max(0, target_lift - baseline)
        weeks = gap / 2.0  # ~2 kg/month on main lift
        return max(8, int(weeks * age_factor))

    return max(8, int(12 * age_factor))


def apply_recommended_timeline(result: dict, goal_data: dict, user_target_date: date | None) -> dict:
    """Attach FitAI-recommended deadline when the user did not set one."""
    if user_target_date:
        result["recommended_weeks"] = None
        result["recommended_target_date"] = None
        result["weeks_available"] = _weeks_until(user_target_date)
        return result

    raw_weeks = result.get("recommended_weeks")
    if raw_weeks is None:
        weeks = estimate_recommended_weeks(goal_data)
    else:
        try:
            weeks = max(1, int(raw_weeks))
        except (TypeError, ValueError):
            weeks = estimate_recommended_weeks(goal_data)

    result["recommended_weeks"] = weeks
    result["recommended_target_date"] = (date.today() + timedelta(weeks=weeks)).isoformat()
    result["weeks_available"] = weeks
    return result


async def evaluate_goal_plan(goal_data: dict) -> dict:
    """Assess deadline feasibility, expected outcomes, and nutrition targets."""
    target_date = _parse_target_date(goal_data)
    weeks = _weeks_until(target_date) if target_date else None

    enriched = {
        **goal_data,
        "today": date.today().isoformat(),
        "weeks_until_deadline": weeks,
    }
    if target_date:
        enriched["target_date"] = target_date.isoformat()

    deadline_context = (
        f"Today is {date.today().isoformat()}. "
        f"The deadline is {target_date.isoformat()} with {weeks} weeks remaining. "
        "weeks_until_deadline is pre-calculated — use that exact number; do not compute weeks yourself."
        if target_date
        else (
            f"Today is {date.today().isoformat()}. No deadline was provided "
            "(weeks_until_deadline is null). You MUST recommend the best realistic timeline "
            "to reach their full goal."
        )
    )

    result = await _generate_json_async(
        "goal_evaluate",
        enriched,
        f"""You are an expert fitness coach assessing a user's goal plan.

{INDIA_CONTEXT}

Goal data:
{json.dumps(enriched, indent=2, default=str)}

{deadline_context}

Analyze feasibility if a target_date is provided. Use evidence-based rates:
- Fat loss: sustainable ~0.25-0.5% body fat/week or 0.5-0.75 kg/week; extreme max ~1 kg/week
- Recomposition: slower — ~0.15-0.25% body fat/week
- Strength: beginner/intermediate gains ~1-2.5 kg/month on a main lift; advanced slower

If the deadline is unrealistic, set realistic=false and intensity="extreme". Explain what they CAN achieve by the deadline with an aggressive plan. Do not falsely promise the full target.

If no target_date (NO DEADLINE PROVIDED):
- Calculate the best realistic timeline to achieve the FULL goal using age, gender, current weight, body fat/condition, and goal type from the data.
- For women: factor in life-stage physiology — perimenopause/menopause (~45–55) can slow fat loss, reduce muscle gain rate, and affect recovery/sleep; adjust timelines conservatively. Consider menstrual-cycle effects on energy and water retention where relevant.
- For men: factor in age-related recovery capacity and muscle-loss risk (especially 40+).
- Use sustainable evidence-based rates (see above); do NOT promise unrealistically fast results.
- Set realistic=true and intensity to "sustainable" or "aggressive" as appropriate for the recommended plan.
- Set recommended_weeks to the number of weeks for your recommended timeline (integer, minimum 4).
- Populate headline, expected_by_deadline, and aggressive_plan with the recommended timeline (weeks/months) and what they can expect by then. Fill projected_body_fat, projected_weight, and/or projected_lift with realistic end-state values for that timeline.
- If the user DID provide a target_date, set recommended_weeks to null.

NUTRITION TARGET RULES (critical):
- Use gender and age (when provided) to estimate TDEE and realistic calorie/protein targets.
- If end_goal states explicit daily calorie or protein targets, use those values — do NOT recalculate from TDEE or apply an extra deficit.
- If they give a range (e.g. 2000-2200 calories), use the midpoint.
- If they say calories are "after deficit" or "don't cut calories", their stated intake IS the final daily target — never reduce it further.
- Only estimate target_calories/target_protein from body weight when the user did NOT specify their own numbers.

Return ONLY valid JSON (no markdown):
{{
  "realistic": boolean,
  "intensity": "none" | "sustainable" | "aggressive" | "extreme",
  "headline": "string",
  "expected_by_deadline": "string",
  "aggressive_plan": "string",
  "projected_body_fat": number or null,
  "projected_weight": number or null,
  "projected_lift": number or null,
  "target_calories": number or null,
  "target_protein": number or null,
  "recommended_weeks": number or null
}}""",
        _fallback_goal_plan(goal_data),
    )

    return apply_stated_nutrition_targets(
        apply_recommended_timeline(result, goal_data, target_date),
        goal_data,
    )


def _fallback_goal_plan(goal_data: dict) -> dict:
    weight = goal_data.get("current_weight") or 75
    target_date = _parse_target_date(goal_data)
    weeks = _weeks_until(target_date) if target_date else estimate_recommended_weeks(goal_data)
    stated = parse_stated_nutrition_targets(goal_data.get("end_goal"))
    result = {
        "realistic": True,
        "intensity": "sustainable" if not target_date else "none",
        "weeks_available": weeks if weeks is not None else 0,
        "headline": "",
        "expected_by_deadline": "",
        "aggressive_plan": "",
        "projected_body_fat": None,
        "projected_weight": None,
        "projected_lift": None,
        "target_calories": stated.get("target_calories") or int(weight * 30),
        "target_protein": stated.get("target_protein") or int(weight * 1.8),
        "recommended_weeks": None if target_date else weeks,
    }
    return apply_recommended_timeline(result, goal_data, target_date)


def _fallback_coaching(user_data: dict, analysis_type: str) -> dict:
    if analysis_type == "goal":
        goal_progress = user_data.get("goal_progress", {})
        if not goal_progress.get("has_goal"):
            return {
                "title": "Goal Progress",
                "insights": [{
                    "type": "goal_estimate",
                    "title": "Set a Goal",
                    "content": "Set an active fitness goal with a target date to get personalized progress coaching.",
                }],
                "calorie_recommendation": None,
                "protein_recommendation": None,
                "goal_completion_weeks": None,
            }
        progress = goal_progress.get("progress_percent", 0)
        weeks = goal_progress.get("weeks_until_deadline")
        return {
            "title": "Goal Progress",
            "insights": [{
                "type": "goal_estimate",
                "title": "Progress Update",
                "content": f"You are {progress:.0f}% toward your goal."
                + (f" {weeks} weeks until your deadline." if weeks is not None else ""),
            }],
            "calorie_recommendation": goal_progress.get("nutrition", {}).get("target_calories"),
            "protein_recommendation": goal_progress.get("nutrition", {}).get("target_protein"),
            "goal_completion_weeks": weeks,
        }

    nutrition = user_data.get("nutrition_for_date") or user_data.get("nutrition_today", {})
    calorie_balance = user_data.get("calorie_balance") or {}
    if analysis_type == "weekly":
        weekly = user_data.get("weekly_summary", {}).get("nutrition", {})
        protein_today = weekly.get("avg_protein_g") or 0
        target_protein = weekly.get("target_protein") or int((user_data.get("current_weight") or 75) * 1.8)
    else:
        protein_today = nutrition.get("protein") or 0
        active_goal = user_data.get("active_goal") or {}
        target_protein = active_goal.get("target_protein") or int((user_data.get("current_weight") or 75) * 1.8)
    protein_gap = target_protein - protein_today

    insights = []
    if analysis_type == "daily" and calorie_balance.get("target_calories"):
        consumed = calorie_balance.get("calories_consumed", 0)
        everyday = calorie_balance.get("calories_burned_everyday_movement", 0)
        exercise_burn = calorie_balance.get("calories_burned_exercise", 0)
        active_total = calorie_balance.get("calories_burned_active_total", everyday + exercise_burn)
        target = calorie_balance["target_calories"]
        remaining = calorie_balance.get("calories_remaining_to_eat", 0)
        over_target = calorie_balance.get("calories_over_target", 0)
        surplus_after_exercise = calorie_balance.get("intake_surplus_after_exercise", 0)
        if over_target > 0:
            burn_needed = calorie_balance.get("target_calorie_burn", surplus_after_exercise)
            if surplus_after_exercise > 0:
                burn_note = f"Burn about {burn_needed:.0f} more kcal through exercise to offset the rest, or cut intake."
            else:
                burn_note = "Your logged exercise covered today's intake surplus — focus on staying at target tomorrow."
            action = (
                f"You ate {consumed:.0f} kcal ({over_target:.0f} over your {target} intake target). "
                f"Movement today: ~{everyday:.0f} kcal everyday (auto) + {exercise_burn:.0f} kcal exercise "
                f"= {active_total:.0f} kcal active burn. {burn_note}"
            )
        else:
            action = (
                f"You ate {consumed:.0f} kcal with {remaining:.0f} kcal left vs your {target} target. "
                f"Movement: ~{everyday:.0f} kcal everyday (auto) + {exercise_burn:.0f} kcal exercise."
            )
        insights.append({
            "type": "daily",
            "title": "Today's Action Plan",
            "content": action,
        })

    if protein_gap > 0:
        insights.append({
            "type": "nutrition",
            "title": "Protein Gap",
            "content": f"Protein intake is {protein_gap:.0f}g below target of {target_protein}g.",
        })
    else:
        insights.append({
            "type": "nutrition",
            "title": "Protein On Track",
            "content": f"Great job hitting {protein_today:.0f}g protein!",
        })

    streak = user_data.get("workout_streak") or user_data.get("weekly_summary", {}).get("workout_streak", 0)
    insights.append({
        "type": "daily" if analysis_type == "daily" else "weekly",
        "title": "Workout Consistency",
        "content": f"Current workout streak: {streak} days. Keep it up!",
    })

    body_fat = user_data.get("current_body_fat")
    active_goal = user_data.get("active_goal") or {}
    target_bf = active_goal.get("target_body_fat")
    weeks = None
    if body_fat and target_bf:
        weeks = max(1, int((body_fat - target_bf) * 4))
        insights.append({
            "type": "goal_estimate",
            "title": "Goal Timeline",
            "content": f"Estimated time to reach {target_bf}% body fat: {weeks} weeks.",
        })

    title = "Weekly Summary" if analysis_type == "weekly" else "Daily Coaching"
    return {
        "title": title,
        "insights": insights,
        "calorie_recommendation": active_goal.get("target_calories"),
        "protein_recommendation": target_protein,
        "goal_completion_weeks": weeks,
    }


async def generate_exercise_next_session_targets(
    exercise_payloads: dict[str, list[dict] | dict],
    goal_snapshot: dict,
    fallbacks: dict[str, dict],
    *,
    incremental: bool = False,
) -> dict[str, dict]:
    """
    Set next-session targets per exercise.

    When incremental=True, exercise_payloads values are compact dicts
    (progress_summary + recent_sessions + previous_coaching_summary).
    Otherwise values are full session lists (legacy).
    """
    if not exercise_payloads:
        return {"targets": [], "history_summaries": {}}

    user_input = {
        "goal": goal_snapshot,
        "exercises": exercise_payloads,
        "mode": "incremental" if incremental else "full_history",
    }

    if incremental:
        history_block = f"""Exercise data (compact — do NOT ask for more history):
{json.dumps(exercise_payloads, indent=2, default=str)}

Each exercise includes:
- progress_summary: all-time totals, peaks, and volume trend across ALL past sessions
- recent_sessions: only the last few sessions with full set detail
- previous_coaching_summary: your last recommendation (update it, do not repeat verbatim)
- current_best: latest peak set

Use progress_summary for long-term context. Use recent_sessions for set-level detail."""
    else:
        history_block = f"""Full exercise histories (chronological sessions, all sets logged):
{json.dumps(exercise_payloads, indent=2, default=str)}"""

    prompt = f"""You are an expert strength coach. For each exercise below, recommend the next session target.

User goal context:
{json.dumps(goal_snapshot, indent=2, default=str)}

{history_block}

Rules:
- Apply progressive overload suited to the user's goal type (strength / recomp / fat loss / general fitness).
- Consider within-session fatigue (e.g. set 1 vs set 3), not only the best single set.
- If the user repeated the same loads across sessions, prescribe a specific breakthrough (reps, weight, or set quality).
- If they regressed, recommend consolidation before loading again.
- Weight jumps should be realistic (typically 2.5 kg for barbell/dumbbell compounds, smaller for isolation).
- Each exercise MUST get a unique, specific next-session prescription — never reuse the same sentence across exercises.
- next_session_summary: 1–2 sentences starting with "Next session:" — concrete weight × reps (and sets if helpful), plus brief coaching rationale tied to THEIR history.
- history_summary: one compact sentence capturing their long-term trajectory on this lift (for your future reference — peaks, plateaus, trend). Only needed in incremental mode.

Return ONLY valid JSON (no markdown):
{{
  "targets": [
    {{
      "exercise": "exact exercise name from input",
      "next_weight_kg": number or null,
      "next_reps": number or null,
      "next_session_summary": "string",
      "history_summary": "string or null"
    }}
  ]
}}

Include one entry for every exercise in the input."""

    parsed = await _generate_json_async(
        "exercise_next_session_targets",
        user_input,
        prompt,
        {"targets": [
            {
                "exercise": name,
                "next_weight_kg": fb.get("next_weight_kg"),
                "next_reps": fb.get("next_reps"),
                "next_session_summary": fb.get("next_session_summary", ""),
            }
            for name, fb in fallbacks.items()
        ]},
    )

    targets: dict[str, dict] = {}
    history_summaries: dict[str, str] = {}
    for entry in parsed.get("targets") or []:
        name = entry.get("exercise")
        if not name:
            continue
        targets[name] = {
            "next_weight_kg": entry.get("next_weight_kg"),
            "next_reps": entry.get("next_reps"),
            "next_session_summary": entry.get("next_session_summary")
            or fallbacks.get(name, {}).get("next_session_summary", ""),
        }
        if entry.get("history_summary"):
            history_summaries[name] = entry["history_summary"]

    for name, fb in fallbacks.items():
        if name not in targets:
            targets[name] = fb

    return {"targets": targets, "history_summaries": history_summaries}


def resolve_exercise_name_clusters(names: list[str]) -> dict[str, str]:
    """
    Use Gemini to group exercise names that refer to the same movement despite
    inconsistent labels (e.g. "Cable Chest Press" vs "Cable cross fly").
    """
    unique = list(dict.fromkeys(n.strip() for n in names if n and n.strip()))
    identity = {name: name for name in unique}
    if len(unique) < 2:
        return identity

    user_input = {"exercise_names": unique}
    prompt = f"""You analyze exercise names from a user's workout log. The same lift is often logged under different labels — typos, capitalization, abbreviations, equipment notes, or rep-counting notes in parentheses.

Exercise names to analyze:
{json.dumps(unique, indent=2)}

Your job: group names that refer to the SAME single exercise/movement the user performed.

ALWAYS merge these as the same exercise:
- Capitalization or spelling variants: "Barbell Skull Crushers" and "Barbell Skull crushers"; "Lat pulldown" and "Lat pull down"
- Parenthetical logging notes that do NOT change the movement: equipment ("with dumbbells in each hand"), rep style ("reps are for each leg"), machine notes ("machine weight extra")
- "Walking Lunges with dumbbells in each hand" and "Lunges (reps are for each leg)" — same lunge pattern; equipment and per-leg rep notes are logging detail
- "Leg press" and "Leg press (machine)" or "Leg press machine"

Merge when names describe the same movement the user clearly repeats across sessions, even if muscle labels differ slightly, for example:
- "Cable chest press" and "Cable cross fly" when both appear to be the same cable chest exercise on different days

Do NOT merge genuinely different exercises:
- Unilateral vs bilateral: "Single leg Leg Extension" vs "Leg Extension"
- Different angles/variants: "Bench press" vs "Incline bench press"
- Different movements: "Hammer curl" vs "Preacher curl"; "Cable fly" vs "Cable row"

When unsure, keep exercises separate — but never split the same name over capitalization or parenthetical notes alone.

Return ONLY valid JSON (no markdown):
{{
  "clusters": [
    {{
      "canonical": "preferred display name for the group",
      "aliases": ["every name in this group, including the canonical"]
    }}
  ]
}}

Rules:
- Every input name must appear in exactly one cluster.
- Single-name clusters are allowed when no merge is warranted.
- canonical: shortest clear standard name WITHOUT parenthetical notes when possible (e.g. "Lunges" not "Lunges (reps are for each leg)").
- Use Title Case for canonical names when reasonable.
- aliases must use the exact strings from the input list."""

    parsed = _generate_json(
        "exercise_name_clusters",
        user_input,
        prompt,
        {"clusters": [{"canonical": name, "aliases": [name]} for name in unique]},
    )

    mapping: dict[str, str] = {}
    seen: set[str] = set()
    for cluster in parsed.get("clusters") or []:
        canonical = (cluster.get("canonical") or "").strip()
        aliases = cluster.get("aliases") or []
        if not canonical and aliases:
            canonical = str(aliases[0]).strip()
        if not canonical:
            continue
        for alias in aliases:
            alias_text = str(alias).strip()
            if not alias_text or alias_text not in unique or alias_text in seen:
                continue
            mapping[alias_text] = canonical
            seen.add(alias_text)

    for name in unique:
        if name not in mapping:
            mapping[name] = name
    return mapping
