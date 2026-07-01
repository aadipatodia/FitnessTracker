from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import engine, Base, ensure_schema
from app.http_logging import http_exception_handler, validation_exception_handler
from app.logging_setup import logger, setup_app_logging
from app.services.gemini import setup_gemini_logging
from app.routers import auth, goals, workouts, diet, body, recovery, coach, activities, checkpoints


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_app_logging()
    setup_gemini_logging()
    ensure_schema()
    Base.metadata.create_all(bind=engine)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    logger.info(
        "FitAI Coach API started | model=%s | gemini=%s | cors=%s",
        settings.GEMINI_MODEL,
        "configured" if settings.GEMINI_API_KEY else "missing API key",
        settings.CORS_ORIGINS,
    )
    yield
    logger.info("FitAI Coach API shutting down")


app = FastAPI(
    title="FitAI Coach API",
    description="AI-powered fitness coaching platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

origins = [o.strip() for o in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(goals.router, prefix="/api")
app.include_router(workouts.router, prefix="/api")
app.include_router(diet.router, prefix="/api")
app.include_router(body.router, prefix="/api")
app.include_router(recovery.router, prefix="/api")
app.include_router(activities.router, prefix="/api")
app.include_router(coach.router, prefix="/api")
app.include_router(checkpoints.router, prefix="/api")

if os.path.exists(settings.UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


@app.get("/api/health")
def health():
    return {"status": "healthy", "service": "FitAI Coach"}
