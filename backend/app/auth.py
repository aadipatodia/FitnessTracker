from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise _unauthorized("Missing authentication token")

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except ExpiredSignatureError:
        raise _unauthorized("Token expired")
    except JWTError:
        raise _unauthorized("Invalid authentication token")

    user_id = payload.get("sub")
    if user_id is None:
        raise _unauthorized("Invalid token payload: missing user id")

    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise _unauthorized("Invalid token payload: bad user id")

    user = db.query(User).filter(User.id == user_id_int).first()
    if user is None:
        raise _unauthorized(f"User not found for token (id={user_id_int})")
    return user
