from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

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


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _format_detail(detail: object) -> str:
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


def log_http_error(request: Request, status_code: int, detail: object) -> None:
    auth = summarize_auth_header(request.headers.get("authorization"))
    message = _format_detail(detail)
    logger.warning(
        "%s %s -> %s | client=%s | auth=%s | reason=%s",
        request.method,
        request.url.path,
        status_code,
        _client_ip(request),
        auth,
        message,
    )


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
