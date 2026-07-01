from app.logging_setup import logger
from app.models.user import User


def user_label(user: User) -> str:
    if user.full_name:
        return f"{user.full_name} ({user.email})"
    return user.email


def log_action(user: User, action: str, result: str) -> None:
    logger.info("%s — %s → %s", user_label(user), action, result)


def log_failure(subject: str, action: str, reason: str) -> None:
    logger.warning("%s — %s failed: %s", subject, action, reason)


def summarize_titles(items: list, title_key: str = "title", max_items: int = 3) -> str:
    if not items:
        return "nothing found"
    titles = []
    for item in items[:max_items]:
        title = item[title_key] if isinstance(item, dict) else getattr(item, title_key, str(item))
        titles.append(f'"{title}"')
    extra = len(items) - max_items
    joined = ", ".join(titles)
    if extra > 0:
        return f"{len(items)} items ({joined}, +{extra} more)"
    if len(items) == 1:
        return joined
    return f"{len(items)} items ({joined})"
