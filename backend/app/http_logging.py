from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.logging_setup import logger


def format_detail(detail: object) -> str:
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        parts = []
        for item in detail:
            if isinstance(item, dict):
                loc = ".".join(str(part) for part in item.get("loc", ()))
                msg = item.get("msg", "")
                parts.append(f"{loc}: {msg}" if loc else str(msg))
            else:
                parts.append(str(item))
        return "; ".join(parts) or "validation error"
    return str(detail)


def _friendly_endpoint(path: str) -> str:
    labels = {
        "/api/auth/login": "sign in",
        "/api/auth/register": "create account",
        "/api/coach/insights": "view coach insights",
        "/api/coach/analyze": "run AI coach analysis",
        "/api/coach/dashboard": "view dashboard",
        "/api/coach/charts": "view progress charts",
        "/api/diet/logs": "view diet history",
        "/api/diet/log": "log a meal",
        "/api/workouts": "view workouts",
    }
    for prefix, label in labels.items():
        if path == prefix or path.startswith(prefix + "/"):
            return label
    return path.removeprefix("/api/")


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if exc.status_code >= 400 and request.url.path not in ("/api/auth/login", "/api/auth/register"):
        action = _friendly_endpoint(request.url.path)
        logger.warning(
            "Request failed — %s: %s",
            action,
            format_detail(exc.detail),
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    action = _friendly_endpoint(request.url.path)
    logger.warning(
        "Request failed — %s: invalid input (%s)",
        action,
        format_detail(exc.errors()),
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})
