from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_dashboard_stats(db, current_user.id)


@router.get("/charts", response_model=DashboardCharts)
def charts(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_dashboard_charts(db, current_user.id, days)


@router.post("/analyze", response_model=list[CoachingInsightResponse])
async def analyze(
    request: CoachAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    analysis_date = request.analysis_date or date.today()
    user_data = gather_coaching_data(
        db,
        current_user.id,
        days=7 if request.analysis_type == "weekly" else 1,
        target_date=analysis_date,
        analysis_type=request.analysis_type,
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

    return [
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

    return [
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
