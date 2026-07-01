import time

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.logging_setup import logger


def summarize_auth_header(value: str | None) -> str:
    if not value:
        return "missing"
    if not value.lower().startswith("bearer "):
        return "malformed (expected Bearer scheme)"
    token = value[7:].strip()
    if not token:
        return "empty bearer token"
    return f"present (length={len(token)})"


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def request_path(request: Request) -> str:
    path = request.url.path
    if request.url.query:
        path = f"{path}?{request.url.query}"
    return path


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


def request_context(request: Request) -> str:
    auth = summarize_auth_header(request.headers.get("authorization"))
    ua = request.headers.get("user-agent", "unknown")
    return (
        f"client={client_ip(request)} | auth={auth} | "
        f"ua={ua[:120]}{'…' if len(ua) > 120 else ''}"
    )


def duration_ms(request: Request) -> float | None:
    started = getattr(request.state, "started_at", None)
    if started is None:
        return None
    return (time.perf_counter() - started) * 1000


def format_duration(request: Request) -> str:
    ms = duration_ms(request)
    return f"{ms:.0f}ms" if ms is not None else "—"


def log_http_error(request: Request, status_code: int, detail: object) -> None:
    reason = format_detail(detail)
    logger.warning(
        "%s %s -> %s (%s) | %s | reason=%s",
        request.method,
        request_path(request),
        status_code,
        format_duration(request),
        request_context(request),
        reason,
    )


def log_http_success(request: Request, status_code: int) -> None:
    logger.info(
        "%s %s -> %s (%s) | %s",
        request.method,
        request_path(request),
        status_code,
        format_duration(request),
        request_context(request),
    )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every completed request. Errors are logged in the exception handler."""

    async def dispatch(self, request: Request, call_next):
        request.state.started_at = time.perf_counter()
        response = await call_next(request)

        if response.status_code < 400:
            log_http_success(request, response.status_code)

        return response


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if exc.status_code >= 400:
        log_http_error(request, exc.status_code, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    log_http_error(request, 422, exc.errors())
    return JSONResponse(status_code=422, content={"detail": exc.errors()})
