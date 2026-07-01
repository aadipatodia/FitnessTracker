from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# Auth
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    email: EmailStr
    reset_token: str
    new_password: str = Field(min_length=6)


class PasswordResetRequestResponse(BaseModel):
    message: str
    reset_token: Optional[str] = None


class MessageResponse(BaseModel):
    message: str


# Goals
class GoalCreate(BaseModel):
    goal_type: str
    title: str
    description: Optional[str] = None
    target_body_fat: Optional[float] = None
    current_body_fat: Optional[float] = None
    target_weight: Optional[float] = None
    current_weight: Optional[float] = None
    target_exercise: Optional[str] = None
    target_weight_lifted: Optional[float] = None
    target_calories: Optional[int] = None
    target_protein: Optional[int] = None
    target_date: Optional[date] = None


class GoalGuidanceRequest(BaseModel):
    goal_type: str
    end_goal: Optional[str] = None


class GoalGuidanceResponse(BaseModel):
    title: str
    tips: list[str]


class GoalEvaluateRequest(BaseModel):
    goal_type: str
    end_goal: Optional[str] = None
    target_date: Optional[date] = None
    current_body_fat: Optional[float] = None
    target_body_fat: Optional[float] = None
    current_weight: Optional[float] = None
    target_weight: Optional[float] = None
    target_exercise: Optional[str] = None
    current_weight_lifted: Optional[float] = None
    target_weight_lifted: Optional[float] = None


class GoalFeasibilityResponse(BaseModel):
    realistic: bool
    intensity: str
    weeks_available: int
    headline: str
    expected_by_deadline: str
    aggressive_plan: str
    projected_body_fat: Optional[float] = None
    projected_weight: Optional[float] = None
    projected_lift: Optional[float] = None
    target_calories: Optional[int] = None
    target_protein: Optional[int] = None


class GoalResponse(BaseModel):
    id: int
    goal_type: str
    title: str
    description: Optional[str]
    target_body_fat: Optional[float]
    current_body_fat: Optional[float]
    target_weight: Optional[float]
    current_weight: Optional[float]
    target_exercise: Optional[str]
    target_weight_lifted: Optional[float]
    target_calories: Optional[int]
    target_protein: Optional[int]
    is_active: bool
    created_at: datetime
    target_date: Optional[date]

    class Config:
        from_attributes = True


# Workouts
class SetCreate(BaseModel):
    set_number: int
    weight_kg: Optional[float] = None
    reps: Optional[int] = None
    time_seconds: Optional[int] = None
    rest_seconds: Optional[int] = None


class ExerciseCreate(BaseModel):
    exercise_name: str
    order_index: int = 0
    notes: Optional[str] = None
    sets: list[SetCreate]


class WorkoutCreate(BaseModel):
    workout_date: date
    name: Optional[str] = None
    notes: Optional[str] = None
    duration_minutes: Optional[int] = None
    exercises: list[ExerciseCreate]


class SetResponse(BaseModel):
    id: int
    set_number: int
    weight_kg: Optional[float]
    reps: Optional[int]
    time_seconds: Optional[int]
    rest_seconds: Optional[int]

    class Config:
        from_attributes = True


class ExerciseResponse(BaseModel):
    id: int
    exercise_name: str
    order_index: int
    notes: Optional[str]
    sets: list[SetResponse]

    class Config:
        from_attributes = True


class WorkoutResponse(BaseModel):
    id: int
    workout_date: date
    name: Optional[str]
    notes: Optional[str]
    duration_minutes: Optional[int]
    calories_burned: float = 0
    created_at: datetime
    exercises: list[ExerciseResponse]

    class Config:
        from_attributes = True


# Diet
class DietLogCreate(BaseModel):
    log_date: date
    meal_type: Optional[str] = None
    food_input: str  # plain English, e.g. "2 rotis + dal + 150g paneer"


class DietEntryResponse(BaseModel):
    id: int
    raw_input: str
    food_name: str
    quantity: float
    unit: str
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    source: str

    class Config:
        from_attributes = True


class DietLogResponse(BaseModel):
    id: int
    log_date: date
    meal_type: Optional[str]
    created_at: datetime
    entries: list[DietEntryResponse]
    total_calories: float = 0
    total_protein: float = 0
    total_carbs: float = 0
    total_fat: float = 0

    class Config:
        from_attributes = True


# Body metrics
class BodyMetricCreate(BaseModel):
    recorded_date: date
    weight_kg: Optional[float] = None
    body_fat_percent: Optional[float] = None
    waist_cm: Optional[float] = None
    notes: Optional[str] = None


class BodyMetricResponse(BaseModel):
    id: int
    recorded_date: date
    weight_kg: Optional[float]
    body_fat_percent: Optional[float]
    waist_cm: Optional[float]
    photo_url: Optional[str]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Activities (cardio + daily movement)
class ActivityLogCreate(BaseModel):
    log_date: date
    activity_name: str
    duration_minutes: int = Field(ge=1, le=600)
    category: str = "cardio"  # cardio only


class ActivityLogResponse(BaseModel):
    id: int
    log_date: date
    activity_name: str
    duration_minutes: int
    category: str
    calories_burned: float = 0
    created_at: datetime

    class Config:
        from_attributes = True


# Recovery
class RecoveryLogCreate(BaseModel):
    log_date: date
    sleep_hours: Optional[float] = None
    water_liters: Optional[float] = None
    steps: Optional[int] = None


class RecoveryLogResponse(BaseModel):
    id: int
    log_date: date
    sleep_hours: Optional[float]
    water_liters: Optional[float]
    steps: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# Checkpoints
class CheckpointCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class CheckpointUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    sort_order: Optional[int] = None


class CheckpointResponse(BaseModel):
    id: int
    title: str
    sort_order: int
    created_at: datetime

    class Config:
        from_attributes = True


class DailyCheckpointItem(BaseModel):
    id: int
    title: str
    sort_order: int
    completed: bool
    completed_at: Optional[datetime] = None


class DailyCheckpointsResponse(BaseModel):
    log_date: date
    items: list[DailyCheckpointItem]
    total: int
    completed_count: int


class CheckpointToggleRequest(BaseModel):
    checkpoint_id: int
    log_date: date
    completed: bool


# Coaching
class CoachingInsightResponse(BaseModel):
    id: int
    insight_type: str
    title: str
    content: str
    metadata_json: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


class CoachAnalysisRequest(BaseModel):
    analysis_type: str = "daily"  # daily | weekly | goal
    analysis_date: Optional[date] = None


# Dashboard
class DashboardStats(BaseModel):
    current_weight: Optional[float]
    current_body_fat: Optional[float]
    goal_progress_percent: float
    calories_today: float
    calories_burned_today: float = 0
    calories_burned_workouts: float = 0
    calories_burned_cardio: float = 0
    calories_burned_everyday: float = 0
    protein_today: float
    recovery_score: float
    workout_streak: int
    target_calories: Optional[int]
    target_protein: Optional[int]
    active_goal: Optional[GoalResponse]


class ChartDataPoint(BaseModel):
    date: str
    value: float
    label: Optional[str] = None


class StrengthProgressPoint(BaseModel):
    date: str
    exercise: str
    max_weight: float


class DashboardCharts(BaseModel):
    weight_trend: list[ChartDataPoint]
    body_fat_trend: list[ChartDataPoint]
    strength_progression: list[StrengthProgressPoint]
    protein_intake: list[ChartDataPoint]
    calories_intake: list[ChartDataPoint]
