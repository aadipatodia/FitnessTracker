from pydantic_settings import BaseSettings, SettingsConfigDict

# Fixed JWT signing key — not loaded from env so tokens stay valid across deploys/restarts.
SECRET_KEY = "fitai-coach-dev-secret-change-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql://fitai:fitai@localhost:5432/fitai_coach"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_VISION_MODEL: str = "gemini-3.5-flash"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    UPLOAD_DIR: str = "uploads"
    FRONTEND_URL: str = "http://localhost:5173"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "FitAI"

    @property
    def SECRET_KEY(self) -> str:
        return SECRET_KEY


settings = Settings()
