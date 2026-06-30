from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import engine, Base
from app.services.gemini import setup_gemini_logging
from app.routers import auth, goals, workouts, diet, body, recovery, coach, activities


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_gemini_logging()
    Base.metadata.create_all(bind=engine)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    yield


app = FastAPI(
    title="FitAI Coach API",
    description="AI-powered fitness coaching platform",
    version="1.0.0",
    lifespan=lifespan,
)

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

if os.path.exists(settings.UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


@app.get("/api/health")
def health():
    return {"status": "healthy", "service": "FitAI Coach"}
