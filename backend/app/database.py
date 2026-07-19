from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from sqlalchemy import text

from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def ensure_schema() -> None:
    """Add columns introduced after initial deploy (safe to run repeatedly)."""
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS gender VARCHAR(20)"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS age INTEGER"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS exercise_name_clusters JSON"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token VARCHAR(255)"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token_expires_at TIMESTAMP"))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_users_reset_token ON users (reset_token)"
        ))
        conn.execute(text("ALTER TABLE diet_entries ADD COLUMN IF NOT EXISTS fibre_g FLOAT DEFAULT 0"))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS exercise_progress_summaries (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                exercise_name VARCHAR(255) NOT NULL,
                exercise_key VARCHAR(255) NOT NULL,
                sessions_count INTEGER DEFAULT 0,
                last_session_date DATE,
                last_workout_id INTEGER,
                current_weight_kg FLOAT,
                current_reps INTEGER,
                previous_weight_kg FLOAT,
                previous_reps INTEGER,
                trend VARCHAR(32) DEFAULT 'new',
                next_weight_kg FLOAT,
                next_reps INTEGER,
                next_session_summary TEXT,
                recent_sessions_json JSON,
                progress_summary_json JSON,
                ai_context_summary TEXT,
                history_updated_at TIMESTAMP DEFAULT NOW(),
                ai_refreshed_at TIMESTAMP,
                CONSTRAINT uq_user_exercise_progress UNIQUE (user_id, exercise_key)
            )
        """))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_exercise_progress_user "
            "ON exercise_progress_summaries (user_id)"
        ))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS drop_set_stages (
                id SERIAL PRIMARY KEY,
                set_id INTEGER NOT NULL REFERENCES exercise_sets(id) ON DELETE CASCADE,
                stage_number INTEGER NOT NULL,
                weight_kg FLOAT,
                reps INTEGER
            )
        """))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_drop_set_stages_set_id "
            "ON drop_set_stages (set_id)"
        ))


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
