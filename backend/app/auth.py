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
from app.logging_setup import logger
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
        logger.warning("Auth rejected: missing bearer token")
        raise _unauthorized("Missing authentication token")

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except ExpiredSignatureError:
        logger.warning("Auth rejected: token expired")
        raise _unauthorized("Token expired")
    except JWTError as exc:
        logger.warning("Auth rejected: invalid token (%s)", exc.__class__.__name__)
        raise _unauthorized("Invalid authentication token")

    user_id = payload.get("sub")
    if user_id is None:
        logger.warning("Auth rejected: token missing subject claim")
        raise _unauthorized("Invalid token payload: missing user id")

    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        logger.warning("Auth rejected: invalid subject claim value=%r", user_id)
        raise _unauthorized("Invalid token payload: bad user id")

    user = db.query(User).filter(User.id == user_id_int).first()
    if user is None:
        logger.warning("Auth rejected: user not found for id=%s", user_id_int)
        raise _unauthorized(f"User not found for token (id={user_id_int})")
    return user


def create_password_reset_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=15)
    return jwt.encode(
        {"sub": str(user_id), "type": "password_reset", "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def verify_password_reset_token(token: str) -> Optional[int]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "password_reset":
            return None
        user_id = payload.get("sub")
        return int(user_id) if user_id is not None else None
    except (JWTError, ValueError, TypeError):
        return None
