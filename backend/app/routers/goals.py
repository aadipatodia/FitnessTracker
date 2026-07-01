from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.goal import FitnessGoal, GoalType
from app.schemas import (
    GoalCreate,
    GoalEvaluateRequest,
    GoalFeasibilityResponse,
    GoalGuidanceRequest,
    GoalGuidanceResponse,
    GoalResponse,
)
from app.services.gemini import evaluate_goal_plan, generate_goal_guidance

router = APIRouter(prefix="/goals", tags=["goals"])


def _apply_profile(user: User, gender: str | None, age: int | None) -> None:
    if gender:
        user.gender = gender
    if age is not None:
        user.age = age


def _profile_fields(user: User, data: dict) -> dict:
    return {
        **data,
        "gender": data.get("gender") or user.gender,
        "age": data.get("age") if data.get("age") is not None else user.age,
    }


@router.post("/guidance", response_model=GoalGuidanceResponse)
async def get_goal_guidance(
    data: GoalGuidanceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payload = _profile_fields(current_user, data.model_dump(exclude_none=True))
    result = await generate_goal_guidance(
        payload["goal_type"],
        payload.get("end_goal"),
        gender=payload.get("gender"),
        age=payload.get("age"),
    )
    return GoalGuidanceResponse(title=result["title"], tips=result["tips"])


@router.post("/evaluate", response_model=GoalFeasibilityResponse)
async def evaluate_goal_feasibility(
    data: GoalEvaluateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payload = _profile_fields(current_user, data.model_dump(exclude_none=True))
    result = await evaluate_goal_plan(payload)
    return GoalFeasibilityResponse(**result)


@router.post("", response_model=GoalResponse)
def create_goal(
    data: GoalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _apply_profile(current_user, data.gender, data.age)

    db.query(FitnessGoal).filter(
        FitnessGoal.user_id == current_user.id, FitnessGoal.is_active == True
    ).update({"is_active": False})

    goal = FitnessGoal(
        user_id=current_user.id,
        goal_type=GoalType(data.goal_type),
        title=data.title,
        description=data.description,
        target_body_fat=data.target_body_fat,
        current_body_fat=data.current_body_fat,
        target_weight=data.target_weight,
        current_weight=data.current_weight,
        target_exercise=data.target_exercise,
        target_weight_lifted=data.target_weight_lifted,
        target_calories=data.target_calories or 2200,
        target_protein=data.target_protein or 150,
        target_date=data.target_date,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)

    return _to_response(goal)


@router.get("", response_model=list[GoalResponse])
def list_goals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    goals = db.query(FitnessGoal).filter(FitnessGoal.user_id == current_user.id).all()
    return [_to_response(g) for g in goals]


@router.get("/active", response_model=GoalResponse | None)
def get_active_goal(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    goal = (
        db.query(FitnessGoal)
        .filter(FitnessGoal.user_id == current_user.id, FitnessGoal.is_active == True)
        .first()
    )
    return _to_response(goal) if goal else None


def _to_response(goal: FitnessGoal) -> GoalResponse:
    return GoalResponse(
        id=goal.id,
        goal_type=goal.goal_type.value,
        title=goal.title,
        description=goal.description,
        target_body_fat=goal.target_body_fat,
        current_body_fat=goal.current_body_fat,
        target_weight=goal.target_weight,
        current_weight=goal.current_weight,
        target_exercise=goal.target_exercise,
        target_weight_lifted=goal.target_weight_lifted,
        target_calories=goal.target_calories,
        target_protein=goal.target_protein,
        is_active=goal.is_active,
        created_at=goal.created_at,
        target_date=goal.target_date.date() if goal.target_date else None,
    )
