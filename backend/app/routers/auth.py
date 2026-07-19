import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.activity_log import log_action, log_failure
from app.auth import create_access_token, get_current_user, get_password_hash, verify_password
from app.config import settings
from app.dev_credentials import log_dev_credential
from app.database import get_db
from app.models.user import User
from app.schemas import (
    ForgotPasswordRequest,
    MessageResponse,
    ResetPasswordRequest,
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services.email import send_password_reset_email

router = APIRouter(prefix="/auth", tags=["auth"])

RESET_TOKEN_TTL = timedelta(hours=1)
GENERIC_FORGOT_PASSWORD_MESSAGE = (
    "If an account exists for that email, we've sent a password reset link."
)


@router.post("/register", response_model=Token)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log_dev_credential(user_data.email, user_data.password, user_data.full_name)

    token = create_access_token(data={"sub": str(user.id)})
    log_action(user, "created account", "signed in automatically")
    return Token(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user:
        log_failure(credentials.email, "sign in", "account does not exist")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User does not exist",
        )
    if not verify_password(credentials.password, user.hashed_password):
        log_failure(credentials.email, "sign in", "wrong password")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wrong password",
        )

    log_action(user, "signed in", "session started")
    token = create_access_token(data={"sub": str(user.id)})
    return Token(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


def _frontend_origin(request: Request) -> str:
    """Prefer the browser's actual origin over the configured default, so a stale
    FRONTEND_URL env var can never point the reset link at the wrong deployment."""
    origin = request.headers.get("origin") or request.headers.get("referer")
    if origin:
        return origin.rstrip("/").removesuffix("/reset-password").removesuffix("/forgot-password").removesuffix("/login")
    return settings.FRONTEND_URL


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(data: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        log_failure(data.email, "request password reset", "account does not exist")
        return MessageResponse(message=GENERIC_FORGOT_PASSWORD_MESSAGE)

    user.reset_token = secrets.token_urlsafe(32)
    user.reset_token_expires_at = datetime.utcnow() + RESET_TOKEN_TTL
    db.commit()

    reset_link = f"{_frontend_origin(request)}/reset-password?token={user.reset_token}"
    sent = send_password_reset_email(user.email, reset_link)
    log_action(
        user,
        "requested password reset",
        "reset email sent" if sent else "reset email FAILED to send (SMTP not configured?)",
    )
    return MessageResponse(message=GENERIC_FORGOT_PASSWORD_MESSAGE)


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.reset_token == data.token).first()
    if not user or not user.reset_token_expires_at or user.reset_token_expires_at < datetime.utcnow():
        log_failure("unknown", "reset password", "invalid or expired token")
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")

    user.hashed_password = get_password_hash(data.new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    db.commit()

    log_action(user, "reset password", "password updated via email link")
    return MessageResponse(message="Password updated. You can now sign in.")
