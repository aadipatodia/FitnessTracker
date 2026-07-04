import logging
from pathlib import Path
from typing import Optional

import firebase_admin
from firebase_admin import auth, credentials

from app.config import settings

logger = logging.getLogger(__name__)

_initialized = False


def _has_admin_credentials() -> bool:
    return bool(
        settings.FIREBASE_CREDENTIALS_PATH
        and Path(settings.FIREBASE_CREDENTIALS_PATH).is_file()
    )


def init_firebase() -> bool:
    global _initialized
    if _initialized or firebase_admin._apps:
        _initialized = True
        return True

    if not settings.FIREBASE_PROJECT_ID:
        logger.warning("FIREBASE_PROJECT_ID not set — Firebase token verification disabled")
        return False

    try:
        options = {"projectId": settings.FIREBASE_PROJECT_ID}
        if _has_admin_credentials():
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred, options)
            logger.info("Firebase Admin initialized with service account")
        else:
            firebase_admin.initialize_app(options=options)
            logger.info(
                "Firebase initialized for token verification only "
                "(set FIREBASE_CREDENTIALS_PATH for account linking)"
            )
        _initialized = True
        return True
    except Exception:
        logger.exception("Firebase initialization failed")
        return False


def is_firebase_admin_configured() -> bool:
    return _has_admin_credentials()


def verify_firebase_id_token(token: str) -> Optional[dict]:
    if not init_firebase():
        return None
    try:
        return auth.verify_id_token(token)
    except Exception:
        return None


def link_firebase_user(user, password: str, db) -> Optional[str]:
    """Create or link a Firebase account for an existing PostgreSQL user."""
    if user.firebase_uid:
        return user.firebase_uid
    if not is_firebase_admin_configured() or not init_firebase():
        return None

    try:
        fb_user = auth.create_user(
            email=user.email,
            password=password,
            display_name=user.full_name,
        )
        user.firebase_uid = fb_user.uid
        db.commit()
        return fb_user.uid
    except auth.EmailAlreadyExistsError:
        fb_user = auth.get_user_by_email(user.email)
        user.firebase_uid = fb_user.uid
        db.commit()
        return fb_user.uid
    except Exception:
        logger.exception("Failed to link Firebase user for %s", user.email)
        return None


def ensure_firebase_user_for_reset(user, db) -> bool:
    """Ensure a Firebase user exists so password reset email can be sent."""
    if user.firebase_uid:
        return True
    if not is_firebase_admin_configured() or not init_firebase():
        return False

    try:
        fb_user = auth.create_user(email=user.email, display_name=user.full_name)
        user.firebase_uid = fb_user.uid
        db.commit()
        return True
    except auth.EmailAlreadyExistsError:
        fb_user = auth.get_user_by_email(user.email)
        user.firebase_uid = fb_user.uid
        db.commit()
        return True
    except Exception:
        logger.exception("Failed to ensure Firebase user for reset: %s", user.email)
        return False
