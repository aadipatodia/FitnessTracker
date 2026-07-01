import json
import logging
import re
import time
from datetime import date, datetime

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
      "fat_g": number
    }}
  ]
}}"""

    return _generate_json("meal_nutrition", {"food_input": food_input}, prompt, fallback)


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

    return _generate_json(
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

Data is a compact summary from goal start through {analysis_date}. Use goal_progress for metrics — do not invent data.

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

Cover: current progress vs targets; if no deadline, a recommended timeline with goal_completion_weeks; if a deadline exists, whether they are on track, weekly rate needed to hit it; calorie/protein adherence including workout burn totals; and 2-3 specific adjustments (training, nutrition, recovery). Be concrete with numbers."""
    elif analysis_type == "weekly":
        prompt = f"""You are an expert fitness coach. Analyze the user's week using the pre-computed weekly_summary (compact daily rollups — do NOT ask for more data).

{INDIA_CONTEXT}

The week ends on {analysis_date} ({user_data.get("period_start")} to {user_data.get("period_end")}).

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
        prompt = f"""You are an expert fitness coach. Analyze ONLY the single day {analysis_date}.

{INDIA_CONTEXT}

CRITICAL RULES:
- Every insight MUST be about {analysis_date} only.
- Do NOT mention workouts, nutrition, or recovery from any other date.
- If there was no workout that day, say so — do not analyze other days' lifts.
- Use workouts array (only this day's sessions), nutrition_for_date, calories_burned_for_date, calorie_balance, recovery_for_analysis_date, and recovery_score.

{recovery_rules}

{calorie_rules}

Sleep for {analysis_date} is the night before through the morning of that date.

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

    return _generate_json(
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

    return _generate_json(
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

    result = _generate_json(
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
- Populate headline, expected_by_deadline, and aggressive_plan with the recommended timeline (weeks/months) and what they can expect by then. Fill projected_body_fat, projected_weight, and/or projected_lift with realistic end-state values for that timeline.

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
  "target_protein": number or null
}}""",
        _fallback_goal_plan(goal_data),
    )

    result["weeks_available"] = weeks if weeks is not None else 0
    return apply_stated_nutrition_targets(result, goal_data)


def _fallback_goal_plan(goal_data: dict) -> dict:
    weight = goal_data.get("current_weight") or 75
    target_date = _parse_target_date(goal_data)
    weeks = _weeks_until(target_date) if target_date else None
    stated = parse_stated_nutrition_targets(goal_data.get("end_goal"))
    return {
        "realistic": True,
        "intensity": "none",
        "weeks_available": weeks if weeks is not None else 0,
        "headline": "",
        "expected_by_deadline": "",
        "aggressive_plan": "",
        "projected_body_fat": None,
        "projected_weight": None,
        "projected_lift": None,
        "target_calories": stated.get("target_calories") or int(weight * 30),
        "target_protein": stated.get("target_protein") or int(weight * 1.8),
    }


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
