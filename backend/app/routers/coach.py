import asyncio
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.activity_log import log_action, summarize_titles
from app.auth import get_current_user
from app.database import SessionLocal, get_db
from app.models.user import User
from app.models.coaching import CoachingInsight, InsightType
from app.schemas import CoachingInsightResponse, CoachAnalysisRequest, DashboardStats, DashboardCharts
from app.services.analytics import get_dashboard_stats, get_dashboard_charts, gather_coaching_data
from app.services.gemini import generate_coaching_analysis

router = APIRouter(prefix="/coach", tags=["coach"])

INSIGHT_TYPE_ALIASES: dict[str, InsightType] = {
    "nutrition_focus": InsightType.NUTRITION,
    "training_strategy": InsightType.PROGRESSION,
    "training": InsightType.PROGRESSION,
    "recovery": InsightType.DAILY,
    "action": InsightType.DAILY,
    "today_action": InsightType.DAILY,
}


def _normalize_insight_type(raw: str | None) -> InsightType:
    if not raw:
        return InsightType.DAILY
    if raw in INSIGHT_TYPE_ALIASES:
        return INSIGHT_TYPE_ALIASES[raw]
    try:
        return InsightType(raw)
    except ValueError:
        return InsightType.DAILY


def _insight_matches(
    insight: CoachingInsight,
    analysis_date: Optional[date],
    analysis_type: Optional[str],
) -> bool:
    meta = insight.metadata_json or {}
    if analysis_date and meta.get("analysis_date") != str(analysis_date):
        return False
    if analysis_type and meta.get("analysis_type") != analysis_type:
        return False
    return True


async def _gather_coaching_data_async(
    user_id: int,
    *,
    days: int,
    target_date: date,
    analysis_type: str,
    client_datetime: datetime | None,
) -> dict:
    """Run heavy analytics off the event loop with a dedicated DB session."""

    def _run() -> dict:
        db = SessionLocal()
        try:
            return gather_coaching_data(
                db,
                user_id,
                days=days,
                target_date=target_date,
                analysis_type=analysis_type,
                client_datetime=client_datetime,
            )
        finally:
            db.close()

    return await asyncio.to_thread(_run)


def _delete_existing_insights(
    db: Session,
    user_id: int,
    analysis_date: date,
    analysis_type: str,
) -> None:
    existing = (
        db.query(CoachingInsight)
        .filter(CoachingInsight.user_id == user_id)
        .all()
    )
    for insight in existing:
        if _insight_matches(insight, analysis_date, analysis_type):
            db.delete(insight)


@router.get("/dashboard", response_model=DashboardStats)
def dashboard(
    client_datetime: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stats = get_dashboard_stats(db, current_user.id, client_datetime=client_datetime)
    log_action(
        current_user,
        "viewed dashboard",
        f"{stats.calories_today:.0f} kcal eaten today, "
        f"{stats.workout_streak}-day workout streak, "
        f"recovery score {stats.recovery_score:.0f}%",
    )
    return stats


@router.get("/charts", response_model=DashboardCharts)
async def charts(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await get_dashboard_charts(db, current_user.id, days)
    log_action(current_user, f"viewed progress charts ({days} days)", "charts loaded")
    return data


@router.post("/analyze", response_model=list[CoachingInsightResponse])
async def analyze(
    request: CoachAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    analysis_date = request.analysis_date or date.today()
    user_data = await _gather_coaching_data_async(
        current_user.id,
        days=7 if request.analysis_type == "weekly" else 1,
        target_date=analysis_date,
        analysis_type=request.analysis_type,
        client_datetime=request.client_datetime,
    )
    analysis = await generate_coaching_analysis(user_data, request.analysis_type)

    _delete_existing_insights(db, current_user.id, analysis_date, request.analysis_type)

    saved: list[CoachingInsight] = []
    calorie_balance = user_data.get("calorie_balance")
    for insight in analysis.get("insights", []):
        record = CoachingInsight(
            user_id=current_user.id,
            insight_type=_normalize_insight_type(insight.get("type")),
            title=insight.get("title", "Insight"),
            content=insight.get("content", ""),
            metadata_json={
                "analysis_date": str(analysis_date),
                "analysis_type": request.analysis_type,
                "stats_through_date": user_data.get("stats_through_date"),
                "exclude_requested_day": user_data.get("exclude_requested_day"),
                "stats_basis_note": user_data.get("stats_basis_note"),
                "data_date": user_data.get("data_date"),
                "calorie_recommendation": analysis.get("calorie_recommendation"),
                "protein_recommendation": analysis.get("protein_recommendation"),
                "goal_completion_weeks": analysis.get("goal_completion_weeks"),
                "calorie_balance": calorie_balance,
            },
        )
        db.add(record)
        saved.append(record)

    db.commit()
    for s in saved:
        db.refresh(s)

    response = [
        CoachingInsightResponse(
            id=s.id,
            insight_type=s.insight_type.value,
            title=s.title,
            content=s.content,
            metadata_json=s.metadata_json,
            created_at=s.created_at,
        )
        for s in saved
    ]

    type_label = {"daily": "daily", "weekly": "weekly", "goal": "goal"}.get(
        request.analysis_type, request.analysis_type
    )
    extras = []
    if analysis.get("calorie_recommendation"):
        extras.append(f"{analysis['calorie_recommendation']} kcal recommended")
    if analysis.get("protein_recommendation"):
        extras.append(f"{analysis['protein_recommendation']}g protein recommended")
    extra_text = f", {', '.join(extras)}" if extras else ""
    log_action(
        current_user,
        f"ran {type_label} AI coach analysis for {analysis_date}",
        f"generated {summarize_titles(response)}{extra_text}",
    )
    return response


@router.get("/insights", response_model=list[CoachingInsightResponse])
def list_insights(
    analysis_date: Optional[date] = Query(None),
    analysis_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    insights = (
        db.query(CoachingInsight)
        .filter(CoachingInsight.user_id == current_user.id)
        .order_by(CoachingInsight.created_at.desc())
        .limit(50)
        .all()
    )

    if analysis_date or analysis_type:
        insights = [i for i in insights if _insight_matches(i, analysis_date, analysis_type)]

    response = [
        CoachingInsightResponse(
            id=i.id,
            insight_type=i.insight_type.value,
            title=i.title,
            content=i.content,
            metadata_json=i.metadata_json,
            created_at=i.created_at,
        )
        for i in insights
    ]

    if analysis_type and analysis_date:
        type_label = {"daily": "daily", "weekly": "weekly", "goal": "goal"}.get(
            analysis_type, analysis_type
        )
        action = f"viewed {type_label} coach insights for {analysis_date}"
    elif analysis_type:
        type_label = {"daily": "daily", "weekly": "weekly", "goal": "goal"}.get(
            analysis_type, analysis_type
        )
        action = f"viewed {type_label} coach insights"
    else:
        action = "viewed coach insights"

    log_action(current_user, action, summarize_titles(response))
    return response
